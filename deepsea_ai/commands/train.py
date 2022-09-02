# !/usr/bin/env python
__author__ = "Danelle Cline"
__copyright__ = "Copyright 2022, MBARI"
__credits__ = ["MBARI"]
__license__ = "GPL"
__maintainer__ = "Duane Edgington"
__email__ = "duane at mbari.org"
__doc__ = '''

Train a YOLOv5 model

@author: __author__
@status: __status__
@license: __license__
'''

import boto3
import random
from tqdm import tqdm
import sagemaker
import shutil
import tempfile
import tarfile
from pathlib import Path
from urllib.parse import urlparse
from sagemaker.estimator import Estimator

from . import config, bucket

models = ['yolov5n', 'yolov5s', 'yolov5m', 'yolov5l', 'yolov5x', 'yolov5n6', 'yolov5s6', 'yolov5m6', 'yolov5l6',
          'yolov5x6']

def yolov5(data: [Path], input_s3: tuple, ckpts_s3: tuple, model_s3: tuple, epochs:int, batch_size:int, volume_size_gb:int,  model:str, instance_type:str):
    """
    Train a YOLOv5 model with SageMaker
    :param data: three part array with compressed artifacts in the order: 0: images, 1: labels, and 2: a text file with the names to ID mapping
    :param input_s3: Input s3 urlparse tuple to the training data
    :param ckpts_s3: Output s3 urlparse tuple to the model checkpoints
    :param model_s3: Output s3 urlparse tuple to the model
    :param epochs: Number of epochs to train; must be > 0
    :param batch_size: Batch size to use; must be > 0
    :volume_size_gb: Size in GB of the volume to attach to training
    :model: YOLOv5 model type
    :instance_type: Type of the AWS instance used, e.g. ml.p2.xlarge
    """
    sagemaker_session = sagemaker.Session()

    # if you are running this outside of a SageMaker notebook, you must set SAGEMAKER_ROLE
    role = config.get_role()

    tags = config.get_tags()

    # capture the common metrics
    metric_definitions = [{'Name': 'box_loss', 'Regex': 'box_loss = ([0-9.]+)'},
                          {'Name': 'cls_loss', 'Regex': 'cls_loss = ([0-9.]+)'},
                          {'Name': 'AP50', 'Regex': 'AP50 = ([0-9.]+)'}]

    # add a metric definition for each concept to track - these will be reported during training
    labels = []
    with open(data[2]) as label_file:
        labels = [l.strip() for l in label_file.readlines()]

    assert(len(labels) > 0)

    # can only track up to 40 metrics including the common ones above and some overhead metrics
    for i, name in enumerate(labels):
        if i < 37:
            print(f"Monitoring metric 'AP_{name}'")
            metric_definitions.append({'Name': f'AP_{name}',  'Regex': f'AP_\/{name} = ([0-9.]+)'})
        else:
            print(f"40 limit exceeded for metric monitoring in SageMaker. Skipping over monitoring metric 'AP_{name}'")

    # setup the estimator
    print(f'Saving checkpoints to s3://{ckpts_s3.netloc}{ckpts_s3.path}')
    print(f'Saving model to s3://{model_s3.netloc}{model_s3.path}')

    if model not in models:
        raise Exception(f'Model {model} invalid. Choose a model from {models}')

    img_size = 640
    if '6' in model: img_size = 1280  # all larger (1280x1280) models have the number 6 in them, e.g. yolov5n6

    user_name = config.get_username()
    output_ckpts_s3 = f's3://{ckpts_s3.netloc}{ckpts_s3.path}'
    output_model_s3 = f's3://{model_s3.netloc}{model_s3.path}'
    training_s3 = f's3://{input_s3.netloc}{input_s3.path}'
    estimator = Estimator(base_job_name=f'{model}-{user_name}-args',
                           role=role,
                           tags=tags,
                           image_uri='872338704006.dkr.ecr.us-west-2.amazonaws.com/deepsea-yolov5:1.0.0',
                           volume_size = volume_size_gb,
    #                        max_wait=43200,
    #                        max_run=42300,
                           enable_sagemaker_metrics=True,
                           checkpoint_s3_uri=output_ckpts_s3,
                           output_path=output_model_s3,
                           instance_count=1,
                           instance_type=instance_type,
                           sagemaker_session=sagemaker_session,
                           input_mode= 'File',
                           metric_definitions=metric_definitions,
                           hyperparameters={
                               'num-epochs': epochs,
                               'model': model,
                               'img-size': img_size,
                               'batch-size': batch_size,
                               'lr': .08,
                               'images': f'/opt/ml/input/data/training/{data[0].name}',
                               'labels': f'/opt/ml/input/data/training/{data[1].name}',
                               'label-map': f'/opt/ml/input/data/training/{data[2].name}'
                            })

    training_data = sagemaker.inputs.TrainingInput(training_s3, distribution='FullyReplicated', content_type='text/plain', s3_data_type='S3Prefix')

    # launch the training then clean-up the checkpoint bucket
    estimator.fit(inputs={'training': training_data})

    print(f'Checkpoints saved in {output_ckpts_s3}')
    s3 = boto3.resource('s3')
    bb = s3.Bucket(model_s3.netloc)
    for obj in bb.objects.filter(Prefix=model_s3.path.lstrip('/')):
        if 'model.tar.gz' in obj.key:
            print(f'Model saved in {output_model_s3}')
            break

def package(bucket_s3: tuple):
    """
    :Package a YOLOv5 model into a format that the deepsea-ai can use in its pipelines.
    :param bucket_s3: Urlparse tuple to the model checkpoints; packages up the best.pt checkpoint plus other config files
    :return:
    """

    s3 = boto3.client('s3')
    s3_resource = boto3.resource('s3')
    b = s3_resource.Bucket(bucket_s3.netloc)

    with tempfile.TemporaryDirectory() as in_tmp_dir:
        in_tmp_path = Path(in_tmp_dir) / 'in'
        in_tmp_path.mkdir()
        out_tmp_path = Path(in_tmp_dir) / 'out'
        out_tmp_path.mkdir()
        out_tar_path = Path(in_tmp_dir) / 'model.tar.gz'

        # download all .yaml and best.pt checkpoints
        for obj in b.objects.filter(Prefix=bucket_s3.path.lstrip('/')):
            if 'best.pt' in obj.key:
                best_checkpoint = out_tmp_path / 'best.pt'
                print(f'Dowloading {obj.key} to {best_checkpoint.as_posix()}...')
                s3.download_file(
                    bucket_s3.netloc,
                    obj.key,
                    best_checkpoint.as_posix()
                )
            if '.yaml' in obj.key:
                yaml = out_tmp_path / Path(obj.key).name
                print(f'Dowloading {obj.key} to {yaml.as_posix()}...')
                s3.download_file(
                    bucket_s3.netloc,
                    obj.key,
                    yaml.as_posix()
                )

        # compress into a model package
        print(f'Creating {out_tar_path}')
        with tarfile.open(out_tar_path.as_posix(), "w:gz") as tar:
            tar.add(out_tmp_path.as_posix())

        # upload to the bucket
        try:
            with open(out_tar_path.as_posix(), "rb") as f:
                target = f"{bucket_s3.path.rstrip('/')}/{out_tar_path.name}"
                print(f'Uploading {out_tar_path} to s3://{bucket_s3.netloc}/{target}...')
                s3.upload_fileobj(f, bucket_s3.netloc, target)
        except:
            print("error in uploading to s3")

        print(f'Done. s3://{bucket_s3.path}/{out_tar_path.name} is now ready to use in a deepsea-ai detection and tracking pipeline')

def split(input_path:Path, output_path:Path):
    #########################################
    # Credit to http://github.com/ultralytics/yolov5 code for this snippet
    #########################################
    def autosplit(path:Path, weights:tuple, annotated_only:bool):
        files = sorted(x for x in path.rglob('*.*') if x.suffix[1:].lower() in ['bmp', 'dng', 'jpeg', 'jpg', 'mpo', 'png', 'tif', 'tiff', 'webp'])  # image files only
        n = len(files)
        random.seed(0)  # for reproducibility
        indices = random.choices([0, 1, 2], weights=weights, k=n)  # assign each image to a split
        txt = ['autosplit_train.txt', 'autosplit_val.txt', 'autosplit_test.txt']
        [(path.parent / x).unlink(missing_ok=True) for x in txt]  # remove existing
        print(f'Autosplitting images from {path}' + ', using *.txt labeled images only' * annotated_only)
        for i, img in tqdm(zip(indices, files), total=n):
            if not annotated_only or Path(img2label_paths([str(img)])[0]).exists():  # check label
                with open(path.parent / txt[i], 'a') as f:
                    f.write('./' + img.relative_to(path.parent).as_posix() + '\n')  # add image to txt file
    #########################################

    # do the work in a temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        autosplit(path=input_path, weights=(0.85, 0.10, 0.05), annotated_only=False)

        for v in ['train', 'val', 'test']:
            image_path = temp_path / 'images' / v
            label_path = temp_path / 'labels' / v
            image_path.mkdir(parents=True)
            label_path.mkdir(parents=True)
            split_path = (input_path.parent / f'autosplit_{v}.txt')
            print(f'Splitting {split_path}')
            with (split_path).open('r+t') as f:
                for line in tqdm(f):
                    filename = Path(line.strip())
                    shutil.copy2((input_path / 'labels' / f'{filename.stem}.txt').as_posix(),
                                 (label_path / f'{filename.stem}.txt').as_posix())
                    shutil.copy2((input_path.parent / filename).as_posix(),
                                 (image_path / filename.name).as_posix())

        print(f"Creating {(output_path / 'labels.tar.gz').as_posix()}...")
        with tarfile.open((output_path / 'labels.tar.gz').as_posix(), 'w') as t:
            t.add(label_path.parent, arcname='labels')

        print(f"Creating {(output_path / 'images.tar.gz').as_posix()}...")
        with tarfile.open((output_path / 'images.tar.gz').as_posix(), 'w') as t:
            t.add(image_path.parent, arcname='images')

        print('Done')
if __name__ == '__main__':
    package(urlparse('s3://902005-checkpoints-dev/20220821T005204Z/'))
    split(Path.cwd().parent / 'data' / 'training', Path.cwd().parent / 'data')

