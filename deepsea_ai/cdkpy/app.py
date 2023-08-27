from aws_cdk import core
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_ecs as ecs
from aws_cdk import aws_autoscaling as autoscaling
from aws_cdk import aws_sqs as sqs
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_iam as iam
import os

class AutoScalingTaskStack(core.Stack):

    def __init__(self, scope: core.Construct, config, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Get Availability Zones, Region, Account
        print('availability zones 🪸', self.availability_zones)
        print('region 🦭', self.region)
        print('accountId 🐟', self.account)
        print('fleet size 🐳', config['FleetSize'])

        vpc = ec2.Vpc.from_lookup(self, "VPC", vpc_name="default")

        asg = autoscaling.AutoScalingGroup(self, f"asg-{config['StackName']}",
            instance_type=ec2.InstanceType.of(
                instance_class=ec2.InstanceClass.G4DN,
                instance_size=ec2.InstanceSize.XLARGE
            ),
            machine_image=ecs.EcsOptimizedImage.amazon_linux2(ecs.AmiHardwareType.GPU),
            desired_capacity=0,
            min_capacity=0,
            max_capacity=config['FleetSize'],
            cooldown=core.Duration.minutes(15),
            block_devices=[autoscaling.BlockDevice(device_name='/dev/sdh', volume=autoscaling.BlockDeviceVolume.ebs(10))],
            vpc=vpc
        )

        cluster = ecs.Cluster(self, f"cluster-{config['StackName']}", vpc=vpc)
        capacity_provider = ecs.AsgCapacityProvider(self, f"asg-{config['StackName']}-capacity-provider",
            auto_scaling_group=asg,
            enable_managed_scaling=True,
            enable_managed_termination_protection=True,
            minimum_scaling_step_size=1,
            maximum_scaling_step_size=1,
            target_capacity_percent=100
        )
        cluster.add_auto_scaling_group(capacity_provider)

        max_receive_count = 600
        video_timeout = core.Duration.hours(2)
        track_timeout = core.Duration.minutes(30)

        dead_letter_queue = sqs.Queue(self, 'dead',
            retention_period=core.Duration.days(10),
            fifo=True,
            content_based_deduplication=True
        )

        video_sqs_queue = sqs.Queue(self, 'video',
            visibility_timeout=video_timeout,
            fifo=True,
            content_based_deduplication=True,
            dead_letter_queue=sqs.DeadLetterQueue(queue=dead_letter_queue, max_receive_count=max_receive_count)
        )

        track_sqs_queue = sqs.Queue(self, 'track',
            visibility_timeout=track_timeout,
            fifo=True,
            content_based_deduplication=True,
            dead_letter_queue=sqs.DeadLetterQueue(queue=dead_letter_queue, max_receive_count=max_receive_count)
        )

        video_sqs_queue.add_to_resource_policy(
            iam.PolicyStatement(
                sid="allow-sns-messages",
                effect=iam.Effect.ALLOW,
                resources=[video_sqs_queue.queue_arn],
                actions=['sqs:*'],
                principals=[
                    iam.ArnPrincipal(f"arn:aws:iam::{os.environ.get('CDK_DEPLOY_ACCOUNT') or os.environ.get('CDK_DEFAULT_ACCOUNT')}:role/DeepSeaAI")
                ]
            )
        )

        track_sqs_queue.add_to_resource_policy(
            iam.PolicyStatement(
                sid="allow-sns-messages",
                effect=iam.Effect.ALLOW,
                resources=[track_sqs_queue.queue_arn],
                actions=['sqs:*'],
                principals=[
                    iam.ArnPrincipal(f"arn:aws:iam::{os.environ.get('CDK_DEPLOY_ACCOUNT') or os.environ.get('CDK_DEFAULT_ACCOUNT')}:role/DeepSeaAI")
                ]
            )
        )

        core.CfnOutput(self, 'video-queue-deadletter', value=dead_letter_queue.queue_name)
        core.CfnOutput(self, 'video-queue-deadletter-arn', value=dead_letter_queue.queue_arn)

        core.CfnOutput(self, 'video-queue', value=video_sqs_queue.queue_name)
        core.CfnOutput(self, 'video-queue-arn', value=video_sqs_queue.queue_arn)
        core.CfnOutput(self, 'track-queue', value=track_sqs_queue.queue_name)
        core.CfnOutput(self, 'track-queue-arn', value=track_sqs_queue.queue_arn)

        video_bucket_in = s3.Bucket(self, 'video-', removal_policy=core.RemovalPolicy.DESTROY)
        track_bucket_out = s3.Bucket(self, 'tracks-', removal_policy=core.RemovalPolicy.DESTROY)

        logging = ecs.AwsLogDriver(stream_prefix=f"{config['StackName']}")

        role = iam.Role(self, "DeepSeaAI-ecs-taskexec-sqs-s3",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AmazonECSTaskExecutionRolePolicy")
            ]
        )
        role.add_to_policy(iam.PolicyStatement(
            resources=["*"],
            actions=["sqs:*", "s3:*"]
        ))

        task_definition = ecs.Ec2TaskDefinition(self, config['TaskDefinition'],
            task_role=role,
            execution_role=role
        )

        task_definition.add_container(config['StackName'],
            image=ecs.ContainerImage.from_registry(config['ContainerImage']),
            memory_reservation_mib=3072,
            gpu_count=1,
            stop_timeout=core.Duration.hours(2),
            logging=logging,
            environment={
                "PROCESSOR": config['StackName'],
                "VIDEO_QUEUE": video_sqs_queue.queue_name,
                "TRACK_QUEUE": track_sqs_queue.queue_name,
                "DEAD_QUEUE": dead_letter_queue.queue_name,
                "VIDEO_BUCKET": video_bucket_in.bucket_name,
                "TRACK_BUCKET": track_bucket_out.bucket_name,
                "AWS_REGION": os.environ.get('CDK_DEPLOY_REGION') or os.environ.get('CDK_AWS_REGION') or 'us-west-2',
                "DEFAULT_MAX_CALL_ATTEMPTS": "6"
            },
            command=[
                "dettrack",
                "-c", config['track_config'],
                "--model-s3", config['model_location']
            ]
        )

        scale_queue_metric = video_sqs_queue.metric_approximate_number_of_messages_visible(
            period=core.Duration.minutes(5),
            statistic="Average"
        )

        service = ecs.Ec2Service(self, f"service-{config['StackName']}",
            cluster=cluster,
            desired_count=0,
            task_definition=task_definition,
            placement_strategies=[ecs.PlacementStrategy.spread_across('instanceId')]
        )

        video_sqs_queue.grant_consume_messages
