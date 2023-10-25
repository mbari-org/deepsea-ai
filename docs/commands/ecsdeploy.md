# Deploying a model in the Elastic Container Service

The elastic video processing stack manages the deployment of a model in the Elastic Container Service (ECS).
This stack is designed to be used with the [ecsprocess](/commands/process) command.
These instructions assume that you have already trained a model using the [train](/commands/train) command
and know the location of that model in S3.

## Architecture

The architecture of the elastic video processing stack includes:

 * A cloud watch alarm that triggers the auto scaling based on number of videos in a SQQ queue.
 * An autoscaling ECS cluster optimized for fast spin-up and fast spin-down of computing resources. 

When the [ecsprocess](/commands/process) is executed, video is uploaded to a S3 bucket then a message is sent to a video
SQS queue. Messages are sent as soon as the video is successfully uploaded. This triggers a cloud watch alarm to 
start scaling up the ECS cluster.  The ECS cluster will start mulitple tasks to process the video, and these tasks 
will continue to process as long as videos messages are in the queue. When the queue is empty, the container will 
stop processing and the ECS cluster will scale down. Results are stored in a S3 bucket as a .tracks.tar.gz file which
can be downloaded and analyzed.

![ Image link ](/imgs/ecs_arch.png)
 
## Deploying a new model

The following is the YAML formatting that describes the model. 

 * Note that the **StackName** cannot start with a number.
 * The **TaskDefinition** is the name of the ECS task definition that will be created.  
 * The **ContainerImage** is the location of the docker image that will be deployed.  This corresponds to the docker image that was setup with the [train](/commands/train) command.
 * The **FleetSize** is the number of CUDA enabled Amazon Machine Instances that will be deployed.

### Example YAML file

```yaml
Comment: This stack deploys the Megadetector YOLOv5 model
StackName: Megadetector
TaskDefinition: strongsort-yolov5
ContainerImage: 548531997526.dkr.ecr.us-west-2.amazonaws.com/mbari/strongsort-yolov5:1.10.0
FleetSize: 1
model_location: s3://deepsea-ai-548531997526-models/Megadetector.pt
track_config: s3://deepsea-ai-548531997526-track-conf/strong_sort_benthic.yaml
```

Create a .yaml file with this content, e.g. megadetector.yaml

```shell
echo "Comment: This stack deploys the Megadetector YOLOv5 model
StackName: Megadetector
TaskDefinition: strongsort-yolov5
ContainerImage: 548531997526.dkr.ecr.us-west-2.amazonaws.com/mbari/strongsort-yolov5:b8c720b
FleetSize: 1
model_location: s3://deepsea-ai-548531997526-models/Megadetector.pt
track_config: s3://deepsea-ai-548531997526-track-conf/strong_sort_benthic.yaml" > megadetector.yaml
```

Then deploy the stack with the following command:
 
### Deploy with the YAML file and save the stack output

Optionally, deploy and save the stack output to a directory, e.g. to directory named `stacks/megadetector`:

```shell
mkdir stacks/megadetector
docker run -v $PWD:/data \
            -v $HOME/.aws/credentials:/root/.aws/credentials \
            mbari/ecsdeploy \
            /data/megadetector.yaml \
            /data/stacks/megadetector
```

