## Monitor the ECS cluster autoscaling

The Elastic Cluster scales up and down based on the number of videos in the queue. 
You can monitor the cluster scaling by name using the ``deepsea-ai monitor`` command
with your cluster name.

**Please ask if you need to increase the number of videos that can be processed in parallel.
The default is 6 videos.

To see the last autoscaling 10 logs from the cluster public33k, run

```
deepsea-ai monitor --cluster public33k --autoscaling True --records 10 
```

If you want to see more detail with the monitor command, please submit a github issue with a request to add more detail to the monitor command.
There are many ways to monitor the cluster, and we are open to suggestions.

If you have a deepsea-ai dashboard, you can see the jobs in the dashboard,
e.g. http://deepsea-ai.shore.mbari.org/#/clusters