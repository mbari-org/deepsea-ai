## Training a YOLOv5 model

Before training, see the instructions on **[preparing your data](data)**.

If your training has been scaled to 640x640, use yolov5s or yolov5x, e.g.

!!! info inline end 
    Be sure your --batch-size is a multiple of the available GPUs, e.g.  --batch-size 1,2,3,4 for ml.p3.2xlarge --batch-size 4 for ml.p3.8xlarge, --batch-size 8, or 16 for  ml.p3.16xlarge.

```
deepsea-ai train --model yolov5x --instance-type ml.p3.xlarge \
--labels split/labels.tar.gz \
--images split/images.tar.gz \
--label-map names.txt \
--input-s3 s3://benthic-dive-training/ \
--output-s3 s3://benthic-dive-checkpoints/ \
--epochs 1 \
--batch-size 2
```

## Resuming from a previously trained YOLOv5 model

To resume from a previously trained model, pass in the checkpoint bucket from the previous training run. For example,
to resume training for another 4 epochs

```
deepsea-ai train --model yolov5x --instance-type ml.p3.xlarge \
--labels split/labels.tar.gz \
--images split/images.tar.gz \
--label-map names.txt \
--input-s3 s3://benthic-dive-training/20220901T221143Z/checkpoints/ \
--output-s3 s3://benthic-dive-checkpoints/ \
--resume True --epochs 4 \
--batch-size 2
```

## YOLOv5 Models and Instance Types

SageMaker has a number of instances available. The instance type chosen depends on the model and how larger your batch size is, e.g.
for a batch size of 2:

| Model (the --model option)  | Training Image Size (pixels) | Recommended Instance Type (instance-type option) | # GPUs   | COCO mAP<sup>val<br>0.5:0.95 |
|---|------------------------------|-----------------------------------------------------|-----------------------|--------------------|
|yolov5s| 640x640                  | ml.p3.2xlarge                                    | 1  | 36.7                         |
|yolov5x| 640x640                  | ml.p3.2xlarge                                      | 1 | **50.4**                     |
|yolov5s6| 1280x1280               | ml.p3.8xlarge, ml.p3.16xlarge or ml.p4d.24xlarge   | 4, 8, 8 | 43.3                         |
|yolov5x6| 1280x1280               | ml.p3.16xlarge,  or ml.p4d.24xlarge | 8, 8 | **54.4**                     |
v