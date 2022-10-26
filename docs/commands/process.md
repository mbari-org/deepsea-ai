If you have just a few videos to process, or are experimenting, the **process** command is recommended.
This creates a SageMaker Processing Job which uses the [SageMaker ScriptProcessor](https://docs.aws.amazon.com/sagemaker/latest/dg/processing-container-run-scripts.html).
 
Because this command uses SageMaker, so you may need to set your SageMaker IAM role. **If you are running this in SageMaker Studio**, you can skip setting the *SAGEMAKER_ROLE* because it is automatically set for you.

```
export SAGEMAKER_ROLE="arn:aws:iam::872338704006:role/902005-sagemaker-exec"
```



To run one or more videos in a directory with the job name *"DocRickets dive 1423"*  

```
deepsea-ai process -j "DocRickets dive 1423" -i /Volumes/M3/mezzanine/DocRicketts/2022/02/1423/ 
```

or, to specify the tracker as either **strongsort** or **deepsort**

```
deepsea-ai process -j "DocRickets dive 1423" -i /Volumes/M3/mezzanine/DocRicketts/2022/02/1423/ --tracker strongsort 
```

To use a different pretrained model, use the *model-s3* option e.g.

```
deepsea-ai process -j "DocRickets dive 1423" -i /Volumes/M3/mezzanine/DocRicketts/2022/02/1423/ --tracker strongsort --model-s3 s3://902005-public/models/yolov5x_mbay_benthic_model.tar.gz
```

## Elastic Cluster Processing 

If you have setup an Elastic Cluster Service to processing data in batch, you can use it with the **ecsprocess**
option. This is the most cost-effective way to process data in bulk.

To process videos in a directory with the job name *"DocRickets dive 1423"* in your cluster called *benthic33k* : 

```
deepsea-ai ecsprocess -c benthic33k -j "DocRickets dive 1423" -i /Volumes/M3/mezzanine/DocRicketts/2022/02/1423/ 
```