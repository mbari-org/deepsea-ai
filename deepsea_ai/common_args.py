# deepsea-ai, Apache-2.0 license
# Filename: common_args.py
# Description: Common arguments for processing commands

import click

# Common arguments for processing commands
job_option = click.option('--job', type=str, required=True,
                          help='Name of the job, e.g. DiveV4361 benthic outline')
cluster_option = click.option('--cluster', type=str, required=True,
                              help='Name of the cluster to use to batch process. '
                                   'This must correspond to an available Elastic '
                                   'Container Service cluster. Clusters names correspond '
                                   'to available model names')
dry_run_option = click.option('--dry-run', is_flag=True, default=False,
                              help='Run the command without actually submitting the job.')
config_s3_option = click.option('--config-s3', type=str,
                                help='S3 location of tracking algorithm config yaml file')
args = click.option('--args', type=str, help='Arguments to pass directly to the docker image ')
