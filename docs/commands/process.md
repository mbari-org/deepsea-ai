!!! note "About the process command"

    If you have just a few videos to process, or are experimenting, the **process** command is recommended.
    This creates a SageMaker Processing Job which uses the [SageMaker ScriptProcessor](https://docs.aws.amazon.com/sagemaker/latest/dg/processing-container-run-scripts.html).
    which processes videos one-by-one in sequence. This is the easiest way to get started, but it is not the most efficient or cost-effective way to process videos.
    For processing videos in bulk, use the **ecsprocess** command with an elastic cluster.
 
## Process Examples

!!! info inline end
    The SAGEMAKER_ROLE environment variable is used in the process command. This role is captured in the following order or precedence:
    1. Through the SAGEMAKER_ROLE environment variable
    2. Through the --config option in the [aws] section or when you run the ``deepsea-ai setup`` command
    
    If you are switching AWS accounts, you will need to either set SAGEMAKER_ROLE  or run ``deepsea-ai setup`` again in that new account (recommended).
    
    ```
    export SAGEMAKER_ROLE="arn:aws:iam::872338704006:role/DeepSeaAI"
    ```

To run in **dry-run** mode, which will show you the command that will be run, but not actually run it:

```shell
deepsea-ai process -j "DocRickets dive 1423" -i /Volumes/M3/mezzanine/DocRicketts/2022/02/1423/ --dry-run
```

To run one or more videos in a directory with the job name *"DocRickets dive 1423"*  

```
deepsea-ai process -j "DocRickets dive 1423" -i /Volumes/M3/mezzanine/DocRicketts/2022/02/1423/  --args "--agnostic-nms --iou-thres=0.5 --conf-thres=0.01 --imgsz=640"
```

To use a different pretrained model, use the *model-s3* option e.g.

```
deepsea-ai process -j "DocRickets dive 1423" -i /Volumes/M3/mezzanine/DocRicketts/2022/02/1423/ --model-s3 s3://902005-public/models/yolov5x_mbay_benthic_model.tar.gz --args "--agnostic-nms --iou-thres=0.5 --conf-thres=0.01 --imgsz=640"
```
 

To process a single video, e.g.

```
deepsea-ai process -j "DocRickets dive 1423" -i  /Volumes/M3/mezzanine/DocRicketts/2022/02/1423/D1423_20220221T164250Z_h265.mp4  --args "--agnostic-nms --iou-thres=0.5 --conf-thres=0.01 --imgsz=640"
```

## ECS (Elastic Cluster Service) Process Examples

If you have setup an Elastic Cluster Service to process data in batch, you can use it with the **ecsprocess**
command. This is the most cost-effective way to process data in bulk. See [ECS Cluster Setup](/commands/ecsdeploy) 
for more information on setting up an ECS cluster with your own pretrained model.

To process videos in a directory with the job name *"DocRickets 2022/02"* in your cluster called *benthic33k* : 

```
deepsea-ai ecsprocess -u -c benthic33k -j "DocRickets dive 1423" -i /Volumes/M3/mezzanine/DocRicketts/2022/02/1423/ --args "--agnostic-nms --iou-thres=0.5 --conf-thres=0.01 --imgsz=640"
```

To process videos in a directory with the job name "DocRicketts 2021/08 with a cluster called mbari315k model", excluding any dives with the name D1371, D1374, or D1375

```
deepsea-ai ecsprocess -u \
        --job "DocRicketts 2021/08 with benthic model" \
        --cluster benthic33k  \
        --config 902005prod.ini \
        --input /Volumes/M3/mezzanine/DocRicketts/2021/08/ \
        --exclude D1371 --exclude D1374 --exclude D1375 \
        --args "--agnostic-nms --iou-thres=0.5 --conf-thres=0.01 --imgsz=640" \
```

---
**Updated: 2024-08-14**