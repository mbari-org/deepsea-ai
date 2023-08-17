## Configure the application

The ``deepsea-ai setup`` sets up the system defaults which is primarily all that is needed. However,
the application settings can be configured within `config/config.ini` to override the defaults. 

The settings below can be modified to support connecting with a [database](https://github.com/mbari-org/deepsea-ai-backend).
This is useful for avoiding reprocessing videos that have already been processed.
```ini
[database]
site = http://deepsea-ai.shore.mbari.org
gql = %(site)s/graphql 
```

The settings below should be modified if you want to tag the workflow for cost tracking.
```ini
[tags]
organization = mbari
project_number = 902005
stage = dev
application = detection
```

The settings below control what models are used for detection and tracking.
These are the default models that are used when running the ``deepsea-ai process`` command.

```ini
[aws]
sagemaker_arn = arn:aws:iam::548531997526:role/DeepSeaAI
yolov5_ecr = mbari/deepsea-yolov5:1.1.2
strongsort_ecr = mbari/strongsort-yolov5:1.5.0
yolov5_model_s3 = s3://902005-public/models/yolov5x_mbay_benthic_model.tar.gz
strongsort_track_config_s3 = s3://902005-public/models/strong_sort_benthic.yaml
```