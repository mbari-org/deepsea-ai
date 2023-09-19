## Configure the application

The ``deepsea-ai setup`` sets up the system defaults which is primarily all that is needed. However,
the application settings can be configured within `config/config.ini` to override the defaults. 
Pass that in with the ``--config`` option. For example:

```shell
deepsea-ai process --config config/config.ini
```

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
These are the default models that are used when running the ``deepsea-ai process``
command. If you want to use different models, you can override these settings
, then pass in the ``--config`` option to the ``deepsea-ai process`` command.

```ini
[aws]
model = s3://deepsea-ai-548531997526-models/yolov5x_mbay_benthic_model.tar.gz
track_config = s3://deepsea-ai-548531997526-track-conf/strong_sort_benthic.yaml
```


