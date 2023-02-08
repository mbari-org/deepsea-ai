---
description: DeepSeaAI installation and usage
---
[![MBARI](https://www.mbari.org/wp-content/uploads/2014/11/logo-mbari-3b.png)](http://www.mbari.org) 

DeepSea-AI currently supports:

 - *Training [YOLOv5](http://github.com/ultralytics/yolov5) object detection* models
 - *Processing video with [YOLOv5](http://github.com/ultralytics/yolov5) detection and tracking pipelines* using either:
     * [DeepSort](https://github.com/mikel-brostrom/Yolov5_DeepSort_Pytorch) tracking
     * [StrongSort](https://github.com/mikel-brostrom/Yolov5_StrongSORT_OSNet) tracking

There are three main requirements to use this module:

1.  [An account with AWS Amazon Web Services](https://aws.amazon.com).
2.  [An account with Docker](http://docker.com).
3.  Install and update using [pip](https://pip.pypa.io/en/stable/getting-started/) in a Python>=3.8.0 environment:

After you have setup your AWS account, configure it using the awscli tool  

```
pip install awscli
aws configure
aws --version
```

Then install the module

```shell
pip install -U deepsea-ai
```

Setting up the AWS environment is done with the setup *mirror* command.  This only needs to be done once, or when you upgrade
the module and need the latest docker images.   This command will setup the appropriate AWS permissions and mirror the images used in the commands
from [Docker Hub](https://hub.docker.com) to your ECR Elastic Container Registry. 

Be patient - this takes a while, but only needs to be run once.

```shell
deepsea-ai setup --mirror
```

## Tutorials

* [FathomNet](docs/notebooks/fathomnet_train.ipynb) ✨ Recommended first step to learn more about how to train a YOLOv5 object detection model using freely available FathomNet data
* [Processing video with YOLOv5](docs/notebooks/yolov5_process.ipynb) ✨ Recommended first step to learn more about how to process video with YOLOv5

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
* [`deepsea-ai train --help` - Train a YOLOv5 model and save the model to a bucket](commands/train.md)
* [`deepsea-ai process --help` - Process one or more videos and save the results to  a bucket](commands/process.md)
* [`deepsea-ai ecsprocess --help` - Process one or more videos using the Elastic Container Service and save the results to a bucket](commands/process.md)
* [`deepsea-ai split --help` - Split your training data. This is required before the train command.](data.md) 
* `deepsea-ai -h` - Print help message and exit.
 
Source code is available at [github.com/mbari-org/deepsea-ai](https://github.com/mbari-org/deepsea-ai/).
  
For more details, see the [official documentation](http://docs.mbari.org/deepsea-ai/install).
