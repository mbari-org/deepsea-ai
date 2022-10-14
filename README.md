[![MBARI](https://www.mbari.org/wp-content/uploads/2014/11/logo-mbari-3b.png)](http://www.mbari.org)
[![semantic-release](https://img.shields.io/badge/%20%20%F0%9F%93%A6%F0%9F%9A%80-semantic--release-e10079.svg)](https://github.com/semantic-release/semantic-release)
![license-GPL](https://img.shields.io/badge/license-GPL-blue)
[![Python](https://img.shields.io/badge/language-Python-blue.svg)](https://www.python.org/downloads/)

**DeepSeaAI** is a Python package to simplify processing deep sea video in [AWS](https://aws.amazon.com) from a command line. 
 
It includes reasonable defaults that have been optimized for deep sea video. The goal is to simplify running these algorithms in AWS.

DeepSea-AI currently supports:

 - *Training [YOLOv5](http://github.com/ultralytics/yolov5) object detection* models
 - *Processing video with [YOLOv5](http://github.com/ultralytics/yolov5) detection and tracking pipelines* using either:
     * [DeepSort](https://github.com/mikel-brostrom/Yolov5_DeepSort_Pytorch) tracking
     * [StrongSort](https://github.com/mikel-brostrom/Yolov5_StrongSORT_OSNet) tracking

## Install

Setup [an AWS account](https://aws.amazon.com).

After you have setup your AWS account, configure it using the awscli tool, and confirm your AWS Account by listing your s3 buckets

```
pip install awscli
aws configure
aws --version
aws s3 ls 
```

Install and update using [pip](https://pip.pypa.io/en/stable/getting-started/) in a Python>=3.8.0 environment:

```shell
pip install -U deepsea-ai
```

Setup your AWS account for use with this module with

```shell
deepsea-ai setup
```



## Tutorials

* [FathomNet](docs/notebooks/fathomnet_train.ipynb) ✨ Recommended first step to learn more about how to train a YOLOv5 object detection model using freely available FathomNet data

The best way to use the tutorials is with [Anaconda](https://www.anaconda.com/products/distribution).

### Create the Anaconda environment

This will create an environment called *deepsea-ai-notebooks* and make that available in your local jupyter notebook as the kernel named *deepsea-ai-notebooks*
```
conda env create 
conda activate deepsea-ai-notebooks
pip install ipykernel
python -m ipykernel install --user --name=deepsea-ai-notebooks
```

### Launch jupyter

```
cd docs/notebooks
jupyter notebook
```
---

## Commands

* `deepsea-ai setup --help` - Setup the AWS environment. Must run this once before any other commands.
* [`deepsea-ai train --help` - Train a YOLOv5 model and save the model to a bucket](commands/train.md)
* [`deepsea-ai process --help` - Process one or more videos and save the results to  a bucket](commands/process.md)
* [`deepsea-ai ecsprocess --help` - Process one or more videos using the Elastic Container Service and save the results to a bucket](commands/process.md)
* [`deepsea-ai split --help` - Split your training data. This is required before the train command.](data.md) 
* `deepsea-ai -h` - Print help message and exit.
 
Source code is available at [github.com/mbari-org/deepsea-ai](https://github.com/mbari-org/deepsea-ai/).
  
For more details, see the [official documentation](http://docs.mbari.org/deepsea-ai/install).