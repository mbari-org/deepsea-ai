# deepsea-ai, Apache-2.0 license
# Filename: pipeline/run_strongsort.py
# Description: Runs strongsort tracking algorithm on YOLOv5 models
import click
import datetime
import boto3
import tempfile
import json
import signal
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
else:
    default_input = Path(__file__).parent.parent / 'test' / 'in'
    default_output = Path(__file__).parent.parent / 'test' / 'out'

processing_job_cfg_path = Path('/opt/ml/config/processingjobconfig.json')
stop_flag = False

# A known pretrained model
default_model_s3 = 's3://902005-public/models/yolov5x_mbay_benthic_model.tar.gz'  # yolov5 model

MAX_TIMEOUT_SECS = 3 * 60 * 60  # maximum time a file should take to process is 3 hours


@click.group(context_settings={'help_option_names': ['-h', '--help']})
@click.version_option(
    __version__,
    '-V', '--version',
    message=f'%(prog)s, version %(version)s'
)
def cli():
    """
    StrongSort Detect and Track
    """


@cli.command(name="dettrack")
@click.option('-c', '--config-s3', type=click.STRING, help='Location of strongsort tracking algorithm config yaml file')
@click.option('-r', '--reid-weights', type=click.STRING, help='Location to the reid weights')
@click.option('-i', '--input', type=click.STRING, default=default_input,
                                help='Path to video files. These can be either mp4 or mov files that ffmpeg understands.')
@click.option('-o', '--output', type=click.STRING, default=default_output,
                                help='Path to the output to save the results')
@click.option('-m', '--model-s3', type=str, default=default_model_s3,
              help='S3 path to the trained model tar gz file - must contain a valid YOLOv5 Pytorch model. ')
@click.option('--debug', is_flag=True, help='Debugging flag. Skips processing and downloading of the model.')
@click.option('--args', type=str, help='Additional arguments to pass to strong sort track.py script')
def process_command(config_s3, reid_weights, input, output, model_s3, debug, args):
    """
    Process a collection of videos either from an input folder, or from a sqs queue
    """
    signal.signal(signal.SIGTERM, sigterm_handler)
    global stop_flag
    print(f'{__version__}')
    print(f'Processing videos in {input}. ')
    input_path = Path(input)
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    processor = queue_processor.QueueProcessor(input_path, output_path)

    # download and setup the model once in a temp dir
    download_fini = False
    with tempfile.TemporaryDirectory() as model_temp_dir:

        # strongsort track.py requires separate input/output so let's create that here
        with tempfile.TemporaryDirectory() as in_tmp_dir:
            in_tmp_path = Path(in_tmp_dir) / 'in'
            in_tmp_path.mkdir()
            out_tmp_path = Path(in_tmp_dir) / 'out'
            out_tmp_path.mkdir()

            while processor.has_video() and not stop_flag:
                try:
                    # start fetching new video
                    video = processor.next(out_tmp_path, debug)

                    if video is None:
                        break

                    # only download the model if we have a video to process
                    if not debug and not download_fini:
                        download_fini = True
                        model_path, config_path = download_config(model_s3, config_s3, Path(model_temp_dir))

                    # output tar to save the results to
                    out_tar_path = Path(output_path) / f'{video.stem}.tracks.tar.gz'
                    out_tar_path.parent.mkdir(parents=True, exist_ok=True)

                    start_utc = datetime.datetime.utcnow()

                    # Strip off the quotes
                    if args:
                        args = args.strip('"')

                    if not debug:
                        cmd_track = f'python3 track.py ' \
                                    f'--source {video.input_path} ' \
                                    f'--project {in_tmp_path} ' \
                                    f'--name {video.input_path.stem} ' \
                                    f'--save-txt ' \
                                    f'{args} '
                        if model_path:
                            cmd_track += f'--yolo-weights {model_path} '
                        if reid_weights:
                            cmd_track += f'--strong-sort-weights {reid_weights} '
                        if config_path:
                            cmd_track += f'--config-strongsort {config_path} '
                    else:
                        cmd_track = [f"echo track {input_path} && sleep 60"]

                    print(f'Running {cmd_track}')
                    processor.message_run(video)
                    track_proc = subprocess.Popen(cmd_track, shell=True)
                    track_proc.wait(timeout=MAX_TIMEOUT_SECS)

                    if track_proc.returncode != 0:
                        processor.message_fail(video, track_proc.stdout)
                        continue

                    track_path = in_tmp_path / video.input_path.stem
                    track_path.mkdir(parents=True, exist_ok=True)

                    # copy any configuration files to further downstream data loading/processing
                    if processing_job_cfg_path.exists():
                        print(f'Copying {processing_job_cfg_path} to {track_path}')
                        shutil.copy2(processing_job_cfg_path.as_posix(), track_path.as_posix())
                    else:
                        # create a new job file in the temp_dir with job metadata
                        with open(f"{track_path.as_posix()}/processingjobconfig.json", "w", encoding="utf-8") as j:
                            image_uri = os.environ[
                                'IMAGE_URI'] if 'IMAGE_URI' in os.environ else "mbari/strongsort-yolov5:latest"
                            processor_name = os.environ[
                                'PROCESSOR'] if 'PROCESSOR' in os.environ else "strongsort-yolov5"
                            json.dump({
                                "UserName": video.user_name,
                                "ProcessingJobName": f"{processor_name}-{video.job_name}",
                                "AppSpecification": {
                                    "ImageUri": image_uri,
                                    "ContainerArguments": sys.argv
                                }
                            }, j)

                    # insert the video path into the processing job config file
                    with open(f"{track_path.as_posix()}/processingjobconfig.json", "r", encoding="utf-8") as f:
                        json_dict = json.load(f)

                    json_dict['VideoName'] = video.input_path.name

                    with open(f"{track_path.as_posix()}/processingjobconfig.json", "w", encoding="utf-8") as j:
                        json.dump(json_dict, j, indent=4)

                    # capture the number of unique tracks
                    unique_track_ids = set()

                    # convert the yolo output to a more friendly json output
                    # yolo output is a simple .txt file with the same file prefix as the video_path,
                    # e.g. myvideo.mov output is myvideo.txt
                    yolo_results = track_path / 'tracks' / f'{video.input_path.stem}.txt'

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
                                with open(f"{track_path}/f{last_frame:06}.json", 'w', encoding='utf-8') as f:
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
                            unique_track_ids.add(e['track_uuid'])

                            if len(visual_events) > 0:
                                with open(f"{track_path}/f{last_frame:06}.json", 'w',
                                          encoding='utf-8') as f:
                                    json.dump(["visualevents", visual_events], f)

                    # make the output unique with a timestamp
                    total_time = datetime.datetime.utcnow() - start_utc
                    processor.message_save(track_path, out_tar_path, video, len(unique_track_ids), total_time.total_seconds())

                    print(f'Captured {len(unique_track_ids)} in {video.name}. Total processing time {total_time}. Started at {start_utc}')

                    # clean temp input dir and remove output
                    for i in in_tmp_path.glob('*'):
                        if not i.is_dir(): i.unlink()
                    for o in out_tmp_path.glob('*'):
                        o.unlink()
                    processor.clean(video)

                except Exception as ex:
                    print(f'System failure exception {ex}')
                    exit(-1)
    print('Done')


def download_s3_file(bucket: str, key: str, local_path: Path) -> bool:
    """
    Download a file from s3 to a local path
    :param bucket:  Bucket name
    :param key: prefix/key to the object
    :param local_path: Local path to save the file
    :return:  True if successful, False otherwise
    """
    try:
        print(f'Downloading s3://{bucket}/{key} to {local_path.as_posix()}')
        if 'AWS_DEFAULT_PROFILE' in os.environ:
            print(f'Using AWS profile {os.environ["AWS_DEFAULT_PROFILE"]}')
            session = boto3.Session(profile_name=os.environ['AWS_DEFAULT_PROFILE'])
            s3 = session.resource('s3')
        else:
            s3 = boto3.resource('s3')
        s3.Bucket(bucket).download_file(key, local_path.as_posix())
        return True
    except Exception as ex:
        print(f'Exception {ex}')
        return False


def download_config(model_uri: str, track_uri: str, output_dir: Path):
    """
    Downloads and unpacks the model data and optionally a tracker config yaml

    :param model_uri: full path to model bucket object
    :param track_uri: full path to track bucket object or None if using default
    :param output_dir: full path to directory to save the output
    :return:  a Path object with the path to the model, path to the tracker config
    e.g. /tmp/9sdfggg/best.pt,  /tmp/9sdfggg/strongsort_config.yaml
    """
    # download the model
    parsed_track_config = None
    if track_uri: parsed_track_config = urlparse(track_uri, allow_fragments=False)
    parsed_url_model = urlparse(model_uri, allow_fragments=False)

    found_config = False
    model_out_path = output_dir / Path(parsed_url_model.path).name
    track_out_yaml = output_dir / 'strongsort_config.yaml'

    try:
        if not download_s3_file(parsed_url_model.netloc, parsed_url_model.path.lstrip('/'), model_out_path):
            raise Exception(f'Cannot find model {model_uri}')

        # download the tracker config
        if parsed_track_config:
            if not download_s3_file(parsed_track_config.netloc, parsed_track_config.path.lstrip('/'), track_out_yaml):
                raise Exception(f'Cannot find tracker config {parsed_track_config}')
            found_config = True

        # If model is a tar file, unpack it
        if model_out_path.suffix == '.gz' or model_out_path.suffix == '.tar':
            print(f'Unpacking model {model_out_path}...')
            tarfile.open(model_out_path).extractall(output_dir)
            print(os.listdir(output_dir))
            # Find the name of the .pt file and use that as the model
            for f in Path(output_dir).rglob('*.pt'):
                if f.suffix == '.pt':
                    model_out_path = output_dir / f
                    break

        # Error if we don't have a model with a .pt extension
        if model_out_path.suffix != '.pt':
            raise Exception(f'Cannot find model {model_out_path}')

        return model_out_path, track_out_yaml if found_config else None

    except Exception as ex:
        print(ex)
        exit(-1)


def sigterm_handler(signal, frame):
    print(f'Got SIGTERM {signal}')
    global stop_flag
    stop_flag = True


if __name__ == '__main__':
    cli()
