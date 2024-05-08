# Shutting down video processing in the ECS 

If you have deployed a model in an ECS and want to shut it down because you have made a mistake or want to save costs, 
you can use the [ecsshutdown](/commands/ecsshutdown) command.  This command will stop
all running services, tasks, and container instances in the ECS cluster. Any completed video track results are also 
removed from S3 and auto-scaling is disabled for the ECS service temporarily to prevent new tasks from starting for 5 minutes.

!!! note "About the ecsshutdown command"
This is not the same as deleting the stack, which will remove all resources including the ECS cluster,
rendering it unusable.  This command is intended to temporarily stop processing and save costs or correct a mistake.

## Examples

To shutdown the ECS cluster called *benthic33k*:

```
deepsea-ai ecsshutdown --cluster benthic33k
```

 
You should see the following response:

```

2024-05-07 17:39:18,912 INFO Logging to /Users/dcline/Dropbox/code/deepsea-ai/deepsea_ai/commands/ecsshutdown_20240508.log
2024-05-07 17:39:18,912 INFO =============== Config file /Users/dcline/Dropbox/code/deepsea-ai/deepsea_ai/config/config.ini =================

...

2024-05-07 17:39:19,729 INFO Found cluster benthic33k ARN arn:aws:ecs:us-west-2:168552337187:cluster/benthic33k-clustery5x315k4871A792-5nHEy3gwdISI
arn:aws:ecs:us-west-2:168552337187:cluster/benthic33k-clustery5x315k4871A792-5nHEy3gwdISI
2024-05-07 17:39:20,245 DEBUG {'ResponseMetadata': {'RequestId': 'e93a9198-e9ea-4928-989e-9587da64b898', 'HTTPStatusCode': 200, 'HTTPHeaders': {'x-amzn-requestid': 'e93a9198-e9ea-4928-989e-9587da64b898', 'content-type': 'text/xml', 'content-length': '231', 'date': 'Wed, 08 May 2024 00:39:19 GMT'}, 'RetryAttempts': 0}}
2024-05-07 17:39:20,245 INFO Autoscaling disabled for capacity provider benthic33k-asgy5x315kcapacityprovider21F5C2F6-0yhqf6Ix2hIL
2024-05-07 17:39:20,525 INFO Stopped service arn:aws:ecs:us-west-2:168552337187:service/benthic33k-clustery5x315k4871A792-5nHEy3gwdISI/benthic33k-serviceobjectObjectService10D8676F-bc7xtyXkwlMH
2024-05-07 17:39:20,618 INFO Stopped container instance arn:aws:ecs:us-west-2:168552337187:container-instance/benthic33k-clustery5x315k4871A792-5nHEy3gwdISI/4d5c7a9d295c490a82a2ea22d1f9e0ae
2024-05-07 17:39:20,797 INFO No messages available in benthic33k-trackC8D9330E-wgSOCZUJzVC8.fifo. Track clean-up and shutdown complete
Received 1 messages
Sending message {'MessageId': 'a060e1ec-6f70-4c77-8c3d-fe41f725fd75', 'ReceiptHandle': 'AQEBA7BiOsLpJtuVYJmvVPP3LB1uw4PWVzEeDhVPFEccBWOXbNYQwNlpEW4GdcYMRhCVGRj05IKoyed+l/gyN8NdJ3lbcLWJLuPv16Yc5C4J7X8M4ximabObJTrPiAArDldeAAFG0A3qe9ITG+8mxQ9CniQVQcUU0XXy1tp4cE9Tt+odNn4wK8GTT+S9h4xdqCqtyAeZToobScRkyeVN2jADedD1edkINz2KbCsMsZc7+t4GV59x1QhVdHq0yvF6XZYcvhJW30pccyBNEEDrOm/KxWMppgEponAbgCAIUQ95KjgwNGX+8VXDuUz3GyACKsUN', 'MD5OfBody': 'ff91f22db46e165071cbea443f52c3bf', 'Body': '{\n    "video": "dcline/Dropbox/code/deepsea-ai/tests/data/V4361_20211006T163856Z_h265_1sec.mp4",\n    "clean": "True",\n    "user_name": "dcline",\n    "metadata_b64": "eyJtZXNzYWdlX3V1aWQiOiAiZWIxYjViYTgtNmMwOC00YTJiLWI5ZjEtMjIyYzViNTI1YzZlIn0=",\n    "job_name": "Pycharm test yolov5x-mbay-benthic model from ecsprocess with args",\n    "args": "--agnostic-nms --iou-thres=0.2 --conf-thres=0.001"\n}', 'Attributes': {'SenderId': 'AROAX7NYOBNLHGR6NT7GO:dcline@mbari.org', 'ApproximateFirstReceiveTimestamp': '1715128760831', 'ApproximateReceiveCount': '1', 'SentTimestamp': '1715128495537', 'SequenceNumber': '18885816968567023616', 'MessageDeduplicationId': '80132457153d857a101d4cedf5db1e710590b1f5552f2bff0e3add75a5c1a56c', 'MessageGroupId': '20240508T003455-V4361_20211006T163856Z_h265_1sec.mp4'}} to dead queue benthic33k-dead9A6F9BCE-P8fRoyrLgBjO.fifo
2024-05-07 17:39:20,870 DEBUG {'MD5OfMessageBody': '97db372cf9aee247cff4aba2c6e329a6', 'MessageId': 'a041e56c-0219-40ab-a4c0-21bba0c79348', 'SequenceNumber': '18885817036492015872', 'ResponseMetadata': {'RequestId': '3e5ae064-7c86-5804-ad57-bed0b77efd34', 'HTTPStatusCode': 200, 'HTTPHeaders': {'x-amzn-requestid': '3e5ae064-7c86-5804-ad57-bed0b77efd34', 'date': 'Wed, 08 May 2024 00:39:20 GMT', 'content-type': 'text/xml', 'content-length': '431', 'connection': 'keep-alive'}, 'RetryAttempts': 0}}
2024-05-07 17:39:20,902 DEBUG {'MD5OfMessageBody': '648a41216191ffbcb6b794f70a69d921', 'MessageId': 'd41b86af-70e9-4f32-b39f-a69e91123372', 'SequenceNumber': '18885817036500463616', 'ResponseMetadata': {'RequestId': '1c8b8d46-02a5-539e-9af4-d3f2c95db6ae', 'HTTPStatusCode': 200, 'HTTPHeaders': {'x-amzn-requestid': '1c8b8d46-02a5-539e-9af4-d3f2c95db6ae', 'date': 'Wed, 08 May 2024 00:39:20 GMT', 'content-type': 'text/xml', 'content-length': '431', 'connection': 'keep-alive'}, 'RetryAttempts': 0}}
2024-05-07 17:39:20,902 INFO No messages available in benthic33k-videoC740E53C-qG4Vah2lWyhV.fifo. Video shutdown complete. No videos were being processed during shutdown.
2024-05-07 17:39:20,902 INFO Shutdown of ECS cluster benthic33k complete. Waiting 5 minutes before restarting autoscaling to reenable 

```