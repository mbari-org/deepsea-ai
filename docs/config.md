## Configure the application

The ``deepsea-ai setup`` sets up the system defaults which is primarily all that is needed. However,
the application settings can be configured within `config/config.ini` to override the defaults. 
Pass that in with the ``--config`` option. For example:

```shell
deepsea-ai process --config config/config.ini
```

The settings below can be modified to 
* Support connecting with a [deepsea-ai database](https://github.com/mbari-org/deepsea-ai-database).
This is useful for avoiding reprocessing videos that have already been processed
* Processing jobs commands and their status are captured  with the --monitor 
command in a SQLite database.  The default location is the current directory, 
but this can be changed with the job_db_path setting.
```ini
[database]
track_db_api = http://deepsea-ai.shore.mbari.org/graphql
job_db_path = .
```

## Cost tracking with AWS tags
The settings below should be modified if you want to tag the workflow for cost tracking.
```ini
[tags]
organization = mbari
project_number = 902005
stage = dev
application = detection
```

## Tracking and detection models with the process command
The settings below control what models are used for detection and tracking.
These are the default models that are used when running the ``deepsea-ai process``
command. If you want to use different models, you can override these settings
, then pass in the ``--config`` option to the ``deepsea-ai process`` command.

```ini
[aws]
model = s3://deepsea-ai-548531997526-models/yolov5x_mbay_benthic_model.tar.gz
track_config = s3://deepsea-ai-548531997526-track-conf/strong_sort_benthic.yaml
```

## Tracking and detection models with the ecsprocess command
The settings below control what models are used for detection and tracking with the ecsprocess command
and are only used with the setup --mirror option to mirror the models to the Elastic Container Registry (ECR).


```shell
deepsea-ai process --config config/config.ini --mirror
```

```ini
[docker]
yolov5_container = mbari/deepsea-yolov5:1.1.2
strongsort_container = mbari/strongsort-yolov5:1.10.0
```
---
**Updated: 2024-08-14**



