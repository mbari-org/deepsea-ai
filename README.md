[![MBARI](https://www.mbari.org/wp-content/uploads/2014/11/logo-mbari-3b.png)](http://www.mbari.org)
[![semantic-release](https://img.shields.io/badge/%20%20%F0%9F%93%A6%F0%9F%9A%80-semantic--release-e10079.svg)](https://github.com/semantic-release/semantic-release)
![license-GPL](https://img.shields.io/badge/license-GPL-blue)
[![Python](https://img.shields.io/badge/language-Python-blue.svg)](https://www.python.org/downloads/)

DeepSea-AI is a Python package to simplify processing deep sea video in [AWS](https://aws.amazon.com) from a command line. 

It includes reasonable defaults that have been optimized for deep sea video. The goal is to simplify running these algorithms in AWS.

DeepSea-AI currently supports:
 - *Training [YOLOv5](http://github.com/ultralytics/yolov5) object detection models*
 - *Running [YOLOv5](http://github.com/ultralytics/yolov5) detection and tracking pipelines* on video using either:
   - [DeepSort](https://github.com/mikel-brostrom/Yolov5_DeepSort_Pytorch)
   - [StrongSort](https://github.com/mikel-brostrom/Yolov5_StrongSORT_OSNet) 
 

Authors: Danelle Cline, [dcline@mbari.org](mailto:dcline@mbari.org), Duane Edgington, [duane@mbari.org](mailto:duane@mbari.org)
----

### For details on AWS installation, see [docs.mbari.org/deepsea-ai/install](http://docs.mbari.org/deepsea-ai/install)  

Assuming you have completed the AWS installation, install and update using [pip](https://pip.pypa.io/en/stable/getting-started/):

```shell
$ pip install -U deepsea-ai
```
----


## Commands

* [`deepsea-ai train --help` - Train a YOLOv5 model and save the model to a bucket](https://docs.mbari.org/deepsea-ai/train/)
* [`deepsea-ai process --help` - Process one or more videos and save the results to  a bucket](https://docs.mbari.org/deepsea-ai/process/)
* [`deepsea-ai ecsprocess --help` - Process one or more videos using the Elastic Container Service and save the results to  a bucket](https://docs.mbari.org/deepsea-ai/process/)
* [`deepsea-ai split --help` - Split your training data; required before the train command.](https://docs.mbari.org/deepsea-ai/split/) 
* `deepsea-ai -h` - Print help message and exit.