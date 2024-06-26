
[![MBARI](https://www.mbari.org/wp-content/uploads/2014/11/logo-mbari-3b.png)](http://www.mbari.org)
[![semantic-release](https://img.shields.io/badge/%20%20%F0%9F%93%A6%F0%9F%9A%80-semantic--release-e10079.svg)](https://github.com/semantic-release/semantic-release)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/language-Python-blue.svg)](https://www.python.org/downloads/)

**DeepSeaAI** is a Python package to simplify processing deep sea video in [AWS](https://aws.amazon.com) from a command line. 
 
It includes reasonable defaults that have been optimized for deep sea video. The goal is to simplify running these algorithms in AWS.

DeepSea-AI currently supports:

 - *Training [YOLOv5](http://github.com/ultralytics/yolov5) object detection* models with up to 8 GPUs using the best available instances in AWS
 - Processing video with [YOLOv5](http://github.com/ultralytics/yolov5) detection and tracking pipeline using 
     * [StrongSort](https://github.com/mikel-brostrom/Yolov5_StrongSORT_OSNet) tracking
 - Scaling processing with [AWS Elastic Container Service](https://aws.amazon.com/ecs/)
[click image below to see larger example]
[![ Image link ](docs/imgs/ecs_arch_small.png)](docs/imgs/ecs_arch.png)

The cost to process a video is typically less than **$1.25** per 1-hour video using a model designed for a 640 pixel size.

The cost to train a YOLOv5 model depends on your data size and the number of GPUs you use.A large collection with 30K images and 
300K localizations may cost **$300-$600** to process, depending on the instance you choose to train on. This is reasonably small for a 
research project, and small in comparison to purchasing your own GPU hardware.

See the full documentation at [MBARI deepsea-ai](http://docs.mbari.org/deepsea-ai).
 
## Processing
The processing technology uses the [AWS Elastic Container Service](https://aws.amazon.com/ecs/) with an architecture
that includes a SQS messaging queue to start the processing. Simply upload a video 
to an S3 bucket then submit a job with the location of that video to the queue to 
start processing. The result is returned to a S3 bucket and the video is optionally 
removed to reduce storage cost.


## Getting Started
## Install

There are two main requirements to use this:

1.  [An account with AWS Amazon Web Services](https://aws.amazon.com).
2.  [An account with Docker](http://docker.com).
3.  Install and update using [pip](https://pip.pypa.io/en/stable/getting-started/) in a Python>=3.8.0 environment:

After you have setup your AWS account, configure it using the awscli tool  

```
pip install awscli
aws configure
aws --version
```

Then install directly from pypi

```shell
pip install deepsea-ai
```

Setting up the AWS environment is done with the setup mirror command.  This only needs to be done once, or when you upgrade
the module.   This command will setup the appropriate AWS permissions and mirror the images used in the commands
from [Docker Hub](https://hub.docker.com) to your ECR Elastic Container Registry. 

Be patient - this takes a while, but only needs to be run once.

```shell
deepsea-ai setup --mirror
```

## Tutorials

* [FathomNet](docs/notebooks/fathomnet_train.ipynb) ✨ Recommended first step to learn more about how to train a YOLOv5 object detection model using freely available FathomNet data

### Create the Anaconda environment

The fastest way to get started is to use the Anaconda environment.  This will create a conda environment called *deepsea-ai* and make that available in your local jupyter notebook as the kernel named *deepsea-ai*

```shell
conda env create 
conda activate deepsea-ai
pip install ipykernel
python -m ipykernel install --user --name=deepsea-ai
```

### Launch jupyter

```
cd docs/notebooks
jupyter notebook
```
---

## Commands

* `deepsea-ai setup --help` - Setup the AWS environment. Must run this once before any other commands.
* [`deepsea-ai train --help` - Train a YOLOv5 model and save the model to a bucket](docs/commands/train.md)
* [`deepsea-ai process --help` - Process one or more videos and save the results to  a bucket](docs/commands/process.md)
* [`deepsea-ai ecsprocess --help` - Process one or more videos using the Elastic Container Service and save the results to a bucket](docs/commands/process.md)
* [`deepsea-ai split --help` - Split your training data. This is required before the train command.](docs/data.md) 
* [`deepsea-ai monitor --help` - Monitor processing. Use this after the ecsprocess train command.](docs/commands/monitor.md)
* `deepsea-ai -h` - Print help message and exit.

## Setting up an Elastic Container Service (ECS) cluster 

To process videos in bulk, you can setup an ECS cluster to process videos in parallel.
See the [ECS setup documentation](docs/commands/ecsdeploy.md) for more details.

---
Source code is available at [github.com/mbari-org/deepsea-ai](https://github.com/mbari-org/deepsea-ai/).
  
For more details, see the [official documentation](http://docs.mbari.org/deepsea-ai/install).