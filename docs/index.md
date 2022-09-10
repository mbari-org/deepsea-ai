---
description: DeepSeaAI installation and usage
---
[![MBARI](https://www.mbari.org/wp-content/uploads/2014/11/logo-mbari-3b.png)](http://www.mbari.org) 

**DeepSeaAI** is a Python package to simplify processing deep sea video in [AWS](https://aws.amazon.com) from a command line. 
 
It includes reasonable defaults that have been optimized for deep sea video. The goal is to simplify running these algorithms in AWS.

DeepSea-AI currently supports:

 - *Training [YOLOv5](http://github.com/ultralytics/yolov5) object detection* models
 - *Processing video with [YOLOv5](http://github.com/ultralytics/yolov5) detection and tracking pipelines* using either:
     * [DeepSort](https://github.com/mikel-brostrom/Yolov5_DeepSort_Pytorch)
     * [StrongSort](https://github.com/mikel-brostrom/Yolov5_StrongSORT_OSNet)
     
   
**See the instructions on the [install page](install.md) or in the [official docs](https://docs.mbari.org/deepsea-ai/install/).** 

## Commands

* [`deepsea-ai train --help` - Train a YOLOv5 model and save the model to a bucket](commands/train.md)
* [`deepsea-ai process --help` - Process one or more videos and save the results to  a bucket](commands/process.md)
* [`deepsea-ai ecsprocess --help` - Process one or more videos using the Elastic Container Service and save the results to a bucket](commands/process.md)
* [`deepsea-ai split --help` - Split your training data. This is required before the train command.](data.md) 
* `deepsea-ai -h` - Print help message and exit.
 
Source code is available at [github.com/mbari-org/deepsea-ai](https://github.com/mbari-org/deepsea-ai/).
  