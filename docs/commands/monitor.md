## Monitor your jobs in the ECS cluster

## Continuous monitoring
The monitor command can be used to continuously monitor and generate a report of a job status in an ECS cluster.

Each cluster is assigned a unique name, e.g. *public33k*. This name is used to identify the cluster in the AWS console,
and is used here to identify the cluster with the --cluster option.

This is useful to monitor the progress of a job, e.g. how many videos are processing, how many are left, and how many have failed.
This also generates a simple report of the job status by default every 30 minutes (1800 seconds).
This is configurable using the --update-period option.
 
```
deepsea-ai monitor --cluster public33k " 
```

This will generate a report in the reports/ directory for each job, e.g. *reports/DocRicketts_Dive_D1377_20230323.txt*
while continuously monitoring the job status.

```text
cat reports/DocRicketts_Dive_D1377_20230323.txt
```

```text
DeepSea-AI 1.20.0
Job: Dive1377, Total media: 8, Created at: 20230321T232058, Last update: 20230321T234534 
==============================================================================================
Index, Media, Last Updated, Status
0, D232_20110526T093251.130Z_alt_h264.mp4, 20230321T214929, QUEUED
1, D232_20110526T093251.130Z_h264.mp4, 20230321T214929, QUEUED
2, V4361_20211006T162656Z_h265_1min.mp4, 20230321T195956, SUCCESS
3, V4361_20211006T162656Z_h265_1sec.mp4, 20230321T213437, SUCCESS
4, V4361_20211006T163256Z_h265_1min.mp4, 20230321T195956, SUCCESS
5, V4361_20211006T163256Z_h265_1sec.mp4, 20230321T213437, SUCCESS
6, V4361_20211006T163856Z_h265_1min.mp4, 20230321T044540, SUCCESS
7, V4361_20211006T163856Z_h265_1sec.mp4, 20230321T213437, FAIL
```

!!! info inline end
    Updates are printed to the console (and logs) every 30 minutes, and a report is generated in the reports/ directory.
    By default, this update is every 30 minutes, or when the job starts.
    To get more frequent updates, use the --update-period, e.g. to get updates every 2 minutes or 120 seconds, run
    ``` 
        deepsea-ai monitor --cluster public33k  --update-period 120
    ``` 

!!! alert inline end
    The reporting uses a lightweight approach storing the data in a local file called *job_cache_{your aws acount#}.db*.
    This file is used to store the job status and is updated every 30 minutes. Keep this file safe, as it is used to generate the reports.

### Scaling
The Elastic Cluster scales up and down based on the number of videos in the queue.  The default is 6 videos.

**Please ask if you need to increase the number of videos that can be processed in parallel.** 
  