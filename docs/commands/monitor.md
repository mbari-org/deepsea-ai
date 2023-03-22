## Monitor the ECS cluster

### Scaling
The Elastic Cluster scales up and down based on the number of videos in the queue. 
You can monitor the cluster scaling by name using the ``deepsea-ai monitor`` command
with your cluster name.

**Please ask if you need to increase the number of videos that can be processed in parallel.**
The default is 6 videos.

To see the last autoscaling 10 logs from the cluster public33k, run

```
deepsea-ai monitor --cluster public33k --autoscaling True --records 10 
```

### Queues
The status of the queues can also be monitored to see how many videos are in the queue,
and how many are being processed.

To see the status of the cluster public33k queues, run

```
deepsea-ai monitor --cluster public33k --queues True
```

## Reporting
The monitor command can also be used to monitor and generate a report of a job status in a cluster.
The report is a simple .txt file generated in the reports/ directory.

For example, to generate a report for the job "Dive1377" in the cluster public33k, run

```
deepsea-ai monitor --cluster public33k --job "Dive1377" 
```

This will generate a report in the reports/ directory, e.g. reports/public33k_Dive1377_.txt

```text
DeepSea-AI 1.20.0
Job: Dive1377, Total media: 8, Created at: 20230321T232058, Last update: 20230321T234534 
==============================================================================================
Index, Media, Last Updated, Status
0, D232_20110526T093251.130Z_alt_h264.mp4, 20230321T214929, FAIL
1, D232_20110526T093251.130Z_h264.mp4, 20230321T214929, FAIL
2, V4361_20211006T162656Z_h265_1min.mp4, 20230321T195956, SUCCESS
3, V4361_20211006T162656Z_h265_1sec.mp4, 20230321T213437, FAIL
4, V4361_20211006T163256Z_h265_1min.mp4, 20230321T195956, SUCCESS
5, V4361_20211006T163256Z_h265_1sec.mp4, 20230321T213437, FAIL
6, V4361_20211006T163856Z_h265_1min.mp4, 20230321T044540, SUCCESS
7, V4361_20211006T163856Z_h265_1sec.mp4, 20230321T213437, FAIL
```

!!! info inline end
    To get more frequent updates, use the --update-period, e.g. to get updates every 60 seconds, run
    ``` 
        deepsea-ai monitor --cluster public33k --job Dive1377  --update-period 60
    ```

    By default, reports are generated when the job is complete, or when the job is older than 4 days.
    To generate reports during the job, use the --generate-report option, e.g. to generate a report every 300 seconds, run
    ```
        deepsea-ai monitor --cluster public33k --job Dive1377  --report-update-period 300
    ```

 


### Need more?
If you want to see more detail with the monitor command, please submit a github issue with a request to add more detail to the monitor command.
There are many ways to monitor the cluster, and we are open to suggestions.

If you have a deepsea-ai dashboard, you can see some basic information on the
queue status in the dashboard, e.g. [http://deepsea-ai.shore.mbari.org/#/clusters](http://deepsea-ai.shore.mbari.org/#/clusters)