# !/usr/bin/env python
__author__ = "Danelle Cline"
__copyright__ = "Copyright 2022, MBARI"
__credits__ = ["MBARI"]
__license__ = "GPL"
__maintainer__ = "Danelle Cline"
__email__ = "dcline at mbari.org"
__doc__ = '''

Runs deepsort tracking algorithm on YOLOv5 models

The speed this runs depends on many factors including: 
1) the size of the detection model. 
2) the GPU and CPU it is run on

@author: __author__
@status: __status__
@license: __license__
'''

import click
import datetime
import boto3
import tempfile
import json
import signal
import yaml
import tarfile
import os
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse
import uuid
from pipeline import queue_processor
from pipeline import __version__

# If running in AWS, we must define the inputs/outputs per the spec
from pipeline.data_models import generate_uuids, parse_events

if 'AWS_CONTAINER_CREDENTIALS_RELATIVE_URI' in os.environ:
    default_input = '/opt/ml/processing/input'
    default_output = '/opt/ml/processing/output'
    job_config_path = Path('/opt/ml/config/')
    sys.path.insert(0, '/app/Yolov5_DeepSort_Pytorch')
else:
    default_input = Path(__file__).parent.parent / 'test' / 'in'
    default_output = Path(__file__).parent.parent / 'test' / 'out'
    sys.path.insert(0, str(Path(__file__).parent.parent))
    job_config_path = None

print(default_output)
print(default_input)
stop_flag = False

# A known pretrained model
default_model_s3 = 's3://902005-public/models/yolov5x_mbay_benthic_model.tar.gz'  # yolov5 model

MAX_TIMEOUT_SECS = 3*60*60 # maximum time a file should take to process is 3 hours

@click.group(context_settings={'help_option_names': ['-h', '--help']})
@click.version_option(
    __version__,
    '-V', '--version',
    message=f'%(prog)s, version %(version)s'
)
def cli():
    """
    DeepSort Detect and Track
    """

@cli.command(name="dettrack")
@click.option('-c', '--config-s3', type=click.STRING, help='Location of deepsort tracking algorithm config yaml file')
@click.option('-i', '--input', type=click.STRING, default=default_input,
              help='Path to the input path with video_path files. These can be either mp4 or mov files that ffmpeg '
                   'understands.')
@click.option('-o', '--output', type=click.STRING, default=default_output,
              help='Path to the output to save the results')
@click.option('--conf-thres', type=float, default=0.01, help='object confidence threshold')
@click.option('--iou-thres', type=float, default=0.5, help='IOU threshold for NMS')
@click.option('--save-vid', is_flag=True, help='save video_path tracking results')
@click.option('--max-det', type=int, default=1000, help='maximum detections per image')
@click.option('-m', '--model-s3', type=str, default=default_model_s3,
              help='S3 path to the trained model tar gz file - must contain a valid YOLOv5 Pytorch model. ')
@click.option('--model-size', type=click.INT, default=640, help='Size of the model, e.g. 640 or 1280')
@click.option('--debug', is_flag=True, help='Debugging flag. Skips processing and downloading of the model.')
def process_command(config_s3, conf_thres, iou_thres, input, output, model_size, model_s3, save_vid, max_det, debug):
    """
    Process a collection of videos either from an input folder, or from a sqs queue
    """
    signal.signal(signal.SIGTERM, sigterm_handler)

    print(f'{__version__}')
    print(f'Processing videos in {input}. ')
    input_path = Path(input)
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    processor = queue_processor.QueueProcessor(input_path, output_path)

    # download and setup the model once in a temp dir
    download_fini = False
    with tempfile.TemporaryDirectory() as model_temp_dir:

        # deepsort track.py requires separate input/output so let's create that here
        with tempfile.TemporaryDirectory() as in_tmp_dir:
            in_tmp_path = Path(in_tmp_dir) / 'in'; in_tmp_path.mkdir()
            out_tmp_path = Path(in_tmp_dir) / 'out'; out_tmp_path.mkdir()

            while processor.has_video() and not stop_flag:

                try:
                    # start fetching new video
                    video = processor.next(out_tmp_path, debug)

                    if video is None:
                        break

                    # only download the model if we have a video to process
                    if not debug and not download_fini:
                        download_fini = True
                        model_path, model_name, config_path = download_config(model_s3, config_s3, Path(model_temp_dir))

                    # output tar to save the results to
                    out_tar_path = Path(output_path) / f'{video.stem}.tracks.tar.gz'
                    out_tar_path.parent.mkdir(parents=True, exist_ok=True)

                    try:
                        start_utc = datetime.datetime.utcnow()

                        if not debug:
                            cmd_track = f'python3 track.py --yolo_model {model_path} ' \
                                        f'--source {video.input_path} ' \
                                        f'--output {in_tmp_path} ' \
                                        f'--imgsz {model_size} ' \
                                        f'--conf-thres {conf_thres} ' \
                                        f'--iou-thres {iou_thres} ' \
                                        f'--max-det {max_det} ' \
                                        f'--save-txt ' \
                                        f'--agnostic-nms '
                            if config_path:
                                cmd_track += f'--config_deepsort {config_path} '
                            if save_vid:
                                cmd_track += '--save-vid '
                        else:
                            cmd_track = [f"echo track {input_path} && sleep 60"]

                        track_proc = subprocess.Popen(cmd_track, shell=True)
                        track_proc.wait(timeout=MAX_TIMEOUT_SECS)
                        if track_proc.returncode == 0 or debug:
                            video.complete()

                    except Exception as ex:
                        print(f'Exception {ex}')
                    finally:

                        # copy any configuration files to further downstream data loading/processing
                        if job_config_path and job_config_path.exists():
                            for c in job_config_path.glob('*.json'):
                                shutil.copy2(c.as_posix(), in_tmp_dir)
                        else:
                            # create a new job file in the temp_dir with job metadata
                            with open(f"{in_tmp_path.as_posix()}/processingjobconfig.json", "w", encoding="utf-8") as j:
                                image_uri = os.environ['IMAGE_URI'] if 'IMAGE_URI' in os.environ else "mbari/deepsort-yolov5:latest"
                                processor_name = os.environ['PROCESSOR'] if 'PROCESSOR' in os.environ else "deepsort-yolov5"
                                json.dump({
                                      "UserName": video.user_name,
                                      "ProcessingJobName": f"{processor_name}-{video.job_name}",
                                      "AppSpecification": {
                                          "ImageUri": image_uri,
                                          "ContainerArguments": sys.argv
                                      }
                                    }, j)
                        # convert the yolo output to a more friendly json output
                        # yolo output is a simple .txt file with the same file prefix as the video_path,
                        # e.g. myvideo.mov output is myvideo.txt
                        yolo_results = in_tmp_path / f'{video.stem}.txt'

                        # handle missing data
                        if yolo_results.exists():
                            events_sans_uuids = parse_events(yolo_results.as_posix())
                            events = generate_uuids(events_sans_uuids)

                            # save events aggregated by frame in the same format as deepsea-track to simplify loading
                            visual_events = []
                            last_frame = -1
                            for e in events:
                                if last_frame == -1:
                                    last_frame = e['frameNum']

                                if e['frameNum'] > last_frame:
                                    with open(f"{in_tmp_dir}/f{last_frame:06}.json", 'w', encoding='utf-8') as f:
                                        json.dump(["visualevents", visual_events], f)
                                        visual_events = []

                                last_frame = e['frameNum']

                                visual_events.append(["visualevent",
                                                          {
                                                              'bounding_box': {
                                                                  'height': e['height'],
                                                                  'width': e['width'],
                                                                  'x': e['x'],
                                                                  'y': e['y']
                                                              },
                                                              'class_name': e['name'],
                                                              'confidence': e['confidence'],
                                                              'frame_num': e['frameNum'],
                                                              'occlusion': e['occlusion'],
                                                              'surprise': e['surprise'],
                                                              'track_uuid': e['track_uuid'],
                                                              'uuid': str(uuid.uuid4()),
                                                          }
                                                          ])

                                if len(visual_events) > 0:
                                    with open(f"{in_tmp_path.as_posix()}/f{last_frame:06}.json", 'w', encoding='utf-8') as f:
                                        json.dump(["visualevents", visual_events], f)

                        processor.save(in_tmp_path, out_tar_path, video)
                        total_time = datetime.datetime.utcnow() - start_utc
                        print(f'Total {video.name} processing time {total_time}. Started at {start_utc}')

                        # clean temp input dir and remove output
                        for i in in_tmp_path.glob('*'):
                            i.unlink()
                        for o in out_tmp_path.glob('*'):
                            o.unlink()
                        processor.clean(video)

                except Exception as ex:
                    print(f'System failure exception {ex}')
                    exit(-1)
    print('Done')


def download_config(model_uri: str, track_uri: str, output_dir: Path):
    """
    Downloads and unpacks the model data and optionally a tracker config yaml

    :param model_uri: full path to model bucket object
    :param track_uri: full path to track bucket object or None if using default
    :param output_dir: full path to directory to save the output
    :return:  a Path object with the path to the model, model name, path to the tracker config
    e.g. /tmp/9sdfggg/best.pt, yolov5x, /tmp/9sdfggg/deepsort_config.yaml
    """
    # download the model and uncompress
    parsed_track_config = None
    if track_uri: parsed_track_config = urlparse(track_uri, allow_fragments=False)
    parsed_url_model = urlparse(model_uri, allow_fragments=False)

    print(f'Downloading model {parsed_url_model.netloc}...')
    s3 = boto3.resource('s3')
    bucket = s3.Bucket(parsed_url_model.netloc)
    found_config = False

    try:
        if parsed_url_model.query:
            prefix = parsed_url_model.path.lstrip('/') + '?' + parsed_url_model.query
            objects = bucket.objects.filter(Prefix=prefix)
            if 'model.tar.gz' not in objects.keys():
                raise Exception(f'Cannot find model.tar.gz in {parsed_url_model}')
            s3.Bucket(parsed_url_model.netloc).download_file(f'{prefix}/model.tar.gz', f'{output_dir}/model.tar.gz')
        else:
            s3.Bucket(parsed_url_model.netloc).download_file(f'{parsed_url_model.path[1:]}', f'{output_dir}/model.tar.gz')

        print(f'Unpacking model {parsed_url_model.netloc}...')
        tarfile.open(f'{output_dir}/model.tar.gz').extractall(output_dir)

        # assuming yolov5 model is version 1, read in the model name from the custom_config.yaml
        if (output_dir / 'custom_config.yaml').exists():
            found_config = True
            config_path = output_dir / 'custom_config.yaml'
            with open(config_path) as f:
                config = yaml.safe_load(f)
                model_name = config['model']

        if not found_config:
            raise Exception('Missing a valid configuration file')
            
        # download the tracker config
        if parsed_track_config:
            s3.Bucket(parsed_track_config.netloc).download_file(f'{parsed_track_config.path[1:]}', f'{output_dir}/deepsort_config.yaml')
            return output_dir / 'best.pt', model_name, output_dir / 'deepsort_config.yaml'
        else:
            return output_dir / 'best.pt', model_name, None

    except Exception as ex:
        print(ex)
        exit(-1)


def sigterm_handler(signal, frame):
    print(f'Got SIGTERM {signal}')
    global stop_flag
    stop_flag = True

if __name__ == '__main__':
    cli()
