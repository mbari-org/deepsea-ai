import * as actions from 'aws-cdk-lib/aws-cloudwatch-actions'
import * as cdk from 'aws-cdk-lib'
import * as cw from 'aws-cdk-lib/aws-cloudwatch'
import * as ecs from 'aws-cdk-lib/aws-ecs'
import * as ec2 from 'aws-cdk-lib/aws-ec2'
import * as iam from "aws-cdk-lib/aws-iam"
import * as logs from 'aws-cdk-lib/aws-logs'
import * as process from "process"
import * as s3 from 'aws-cdk-lib/aws-s3'
import * as sqs from 'aws-cdk-lib/aws-sqs'
import * as autoscaling from "aws-cdk-lib/aws-autoscaling"
import * as appautoscaling from 'aws-cdk-lib/aws-applicationautoscaling'
import { TaskConfig } from './config'

export class AutoScalingTaskStack extends cdk.Stack {
  constructor(scope: cdk.App, config: TaskConfig, id: string, props: cdk.StackProps) {
    super(scope, id, props)

    //  Get Availability Zones, Region, Account
    console.log('availability zones 🪸', cdk.Stack.of(this).availabilityZones)
    console.log('region 🦭', cdk.Stack.of(this).region)
    console.log('accountId 🐟', cdk.Stack.of(this).account)
    console.log('fleet size 🐳', config.FleetSize)

    const vpc = ec2.Vpc.fromLookup(this, "VPC", {vpcName: "default"})

    const asg = new autoscaling.AutoScalingGroup(this, `asg-${config.StackName}`, {
      instanceType: ec2.InstanceType.of(ec2.InstanceClass.G4DN, ec2.InstanceSize.XLARGE),
      machineImage: ecs.EcsOptimizedImage.amazonLinux2(ecs.AmiHardwareType.GPU),
      desiredCapacity: 0,
      minCapacity: 0,
      maxCapacity: config.FleetSize,
      cooldown: cdk.Duration.minutes(15),
      blockDevices: [{ deviceName: '/dev/sdh', volume:  autoscaling.BlockDeviceVolume.ebs(20)}],
      vpc
    })

    const cluster = new ecs.Cluster(this, `cluster-${config.StackName}`, { vpc })
    const capacityProvider = new ecs.AsgCapacityProvider(this, `asg-${config.StackName}-capacity-provider`, {
      autoScalingGroup: asg,
      enableManagedScaling: true,
      enableManagedTerminationProtection: true,
      minimumScalingStepSize: 1,
      maximumScalingStepSize: 1,
      targetCapacityPercent: 100,
    })
    cluster.addAsgCapacityProvider(capacityProvider)

    const maxReceiveCount = 600

    // Set the video processing visibility timeout to the maximum time that it takes to process a video once the message is dequeued
    const videoTimeout = cdk.Duration.hours(2)

    // Set the track processing visibility timeeout to the maximum time that it takes to ingest the track once the message is dequeued
    // or the maximum time that it takes to monitor the status of the job
    const trackTimeout = cdk.Duration.hours(2)

    const deadLetterQueue = new sqs.Queue(this, 'dead', {
      retentionPeriod: cdk.Duration.days(10),
      fifo: true,
      contentBasedDeduplication: true,
    })

    const videoSqsQueue = new sqs.Queue(this, 'video', {
      visibilityTimeout: videoTimeout,
      fifo: true,
      contentBasedDeduplication: true,
      deadLetterQueue: {
        queue: deadLetterQueue,
        maxReceiveCount: maxReceiveCount,
      },
    })

    const trackSqsQueue = new sqs.Queue(this, 'track', {
      visibilityTimeout: trackTimeout,
      fifo: true,
      contentBasedDeduplication: true,
      deadLetterQueue: {
        queue: deadLetterQueue,
        maxReceiveCount: maxReceiveCount,
      },
    })

    // Add Policy to queue to allow the accounts with DeepSeaAI role access to write to it
    videoSqsQueue.addToResourcePolicy(new iam.PolicyStatement({
      sid: "allow-sns-messages",
      effect: iam.Effect.ALLOW,
      resources: [videoSqsQueue.queueArn],
      actions: ['sqs:*'],
      principals: [
        new iam.ArnPrincipal(`arn:aws:iam::${process.env.CDK_DEPLOY_ACCOUNT || process.env.CDK_DEFAULT_ACCOUNT}:role/DeepSeaAI`)
      ],
    }))

    // Add Policy to queue to allow the accounts with DeepSeaAI role access to write to it
    trackSqsQueue.addToResourcePolicy(new iam.PolicyStatement({
      sid: "allow-sns-messages",
      effect: iam.Effect.ALLOW,
      resources: [trackSqsQueue.queueArn],
      actions: ['sqs:*'],
      principals: [
        new iam.ArnPrincipal(`arn:aws:iam::${process.env.CDK_DEPLOY_ACCOUNT || process.env.CDK_DEFAULT_ACCOUNT}:role/DeepSeaAI`)
      ],
    }))

    new cdk.CfnOutput(this, 'video-queue-deadletter', { value: deadLetterQueue.queueName })
    new cdk.CfnOutput(this, 'video-queue-deadletter-arn', { value: deadLetterQueue.queueArn })

    new cdk.CfnOutput(this, 'video-queue', { value: videoSqsQueue.queueName })
    new cdk.CfnOutput(this, 'video-queue-arn', { value: videoSqsQueue.queueArn })
    new cdk.CfnOutput(this, 'track-queue', { value: trackSqsQueue.queueName })
    new cdk.CfnOutput(this, 'track-queue-arn', { value: trackSqsQueue.queueArn })

    // Remove the buckets upon destroying - this will fail if there is any data in the buckets which is the desired behavior
    const video_bucket_in = new s3.Bucket(this, 'video-', {removalPolicy: cdk.RemovalPolicy.DESTROY})
    const track_bucket_out = new s3.Bucket(this, 'tracks-', {removalPolicy: cdk.RemovalPolicy.DESTROY});

    // Create a log group for the stack called dsai
    const logGroup = new logs.LogGroup(this, 'dsai', {
      logGroupName: `/ecs/${config.StackName}`,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      retention: logs.RetentionDays.ONE_MONTH
    })

    // Create a task definition with CloudWatch Logs to capture logs from containers and send them to CloudWatch
    // Retain the logs for a month
    const logging = new ecs.AwsLogDriver({
      logGroup: logGroup,
      streamPrefix: 'task',
    })

    // IAM role for EC2 to execute, pull from the ECR, S3 full access (to read and write), logging full access, and SQS (Queue) service full access
    const role = new iam.Role( this, "DeepSeaAI-ecs-taskexec-sqs-s3-log", {
        assumedBy: new iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
        managedPolicies: [
          iam.ManagedPolicy.fromAwsManagedPolicyName( "service-role/AmazonECSTaskExecutionRolePolicy" )
        ]
      }
    )
    // TODO: refine policy to the exact sqs and s3 buckets per best practice
    role.addToPolicy( new iam.PolicyStatement({
        resources: ["*"],
        actions: ["sqs:*","s3:*","logs:*"]
      })
    )

    // Create a Task Definition for the container to start
    // Pass through any of the docker override and reservations for memory and GPU
    const taskDefinition = new ecs.Ec2TaskDefinition(this, config.TaskDefinition,
      {taskRole: role, executionRole: role})

    taskDefinition.addContainer(config.StackName, {
      image: ecs.ContainerImage.fromRegistry(config.ContainerImage),
      memoryReservationMiB: 3072,
      stopTimeout: cdk.Duration.seconds(60),
      logging,
      environment: {
        "PROCESSOR": `${config.StackName}`,
        "VIDEO_QUEUE": videoSqsQueue.queueName,
        "TRACK_QUEUE": trackSqsQueue.queueName,
        "DEAD_QUEUE": deadLetterQueue.queueName,
        "VIDEO_BUCKET": video_bucket_in.bucketName,
        "TRACK_BUCKET": track_bucket_out.bucketName,
        "AWS_REGION": process.env['CDK_DEPLOY_REGION'] || process.env['CDK_AWS_REGION'] || 'us-west-2',
        "DEFAULT_MAX_CALL_ATTEMPTS": "6"
      },
      command: [
        "dettrack",
        "-c", `${config.track_config}`,
        "--model-s3", `${config.model_location}`
      ]
    })

    const scaleOutQueueMetric = videoSqsQueue.metricApproximateNumberOfMessagesVisible({
      period: cdk.Duration.minutes(1),
      statistic: "Average"
    })

    const scaleInQueueMetric = videoSqsQueue.metricApproximateNumberOfMessagesVisible({
      period: cdk.Duration.minutes(60),
      statistic: "Average"
    })

    // Spin-up one service, two tasks per instance
    const service = new ecs.Ec2Service(this, `service-${config}`, {
      cluster: cluster,
      desiredCount: 2,
      taskDefinition: taskDefinition
    })

    // Grant SQS permissions to an ECS service.
    videoSqsQueue.grantConsumeMessages(service.taskDefinition.taskRole)
    trackSqsQueue.grantConsumeMessages(service.taskDefinition.taskRole)

    // Task scaling steps
    const serviceOutScaling = service.autoScaleTaskCount({minCapacity: 0, maxCapacity: config.FleetSize});
    serviceOutScaling.scaleOnMetric(`scaling-${config}`, {
      metric: scaleOutQueueMetric,
      scalingSteps: [
        { upper: 0, change: -1 },
        { lower: 1, change: 1 }
      ],
      cooldown: cdk.Duration.minutes(5),
      adjustmentType: appautoscaling.AdjustmentType.CHANGE_IN_CAPACITY
    })

    // Alarm to scale out the cluster
    const scaleOut = scaleOutQueueMetric.createAlarm(this, 'scale-out', {
      threshold: 1,
      evaluationPeriods: 1,
      comparisonOperator: cw.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
      treatMissingData: cw.TreatMissingData.NOT_BREACHING})

    const scalingOutAction = new autoscaling.StepScalingAction(this, 'scale-out-action', {
      autoScalingGroup: asg,
      estimatedInstanceWarmup:  cdk.Duration.minutes(2),
      adjustmentType: autoscaling.AdjustmentType.CHANGE_IN_CAPACITY})

    // The threshold is set to 1 so the lower bound must be equal to 0
    scalingOutAction.addAdjustment({adjustment: 1, lowerBound: 0})
    scaleOut.addAlarmAction(new actions.AutoScalingAction(scalingOutAction))

    // Alarm to scale in the cluster
    const scaleIn = scaleInQueueMetric.createAlarm(this, 'scale-in', {
      threshold: 0,
      evaluationPeriods: 1,
      comparisonOperator: cw.ComparisonOperator.LESS_THAN_OR_EQUAL_TO_THRESHOLD,
      treatMissingData: cw.TreatMissingData.BREACHING})

    const scalingInAction = new autoscaling.StepScalingAction(this, 'scale-in-action', {
      autoScalingGroup: asg,
      adjustmentType: autoscaling.AdjustmentType.CHANGE_IN_CAPACITY})
    scalingInAction.addAdjustment({adjustment: -1, upperBound: 0})
    scaleIn.addAlarmAction(new actions.AutoScalingAction(scalingInAction))

  }

  get availabilityZones(): string[] {
    return process.env['CDK_DEPLOY_REGION'] === 'us-west-2' ? ['us-west-2a', 'us-west-2b', 'us-west-2c'] : ['us-east-1a']
  }
}
