# deepsea-ai, Apache-2.0 license
# Filename: database/report_generator.py
# Description: Report generator for jobs that are being consumed by an ECS cluster or SageMaker

from pathlib import Path

from deepsea_ai import __version__
from deepsea_ai.config import config as cfg
from deepsea_ai.database.job.database import Job, PydanticJobWithMedias
from deepsea_ai.database.job.misc import job_hash
from deepsea_ai.database.tracks import api, queries
from deepsea_ai.logger import info, debug, err
from datetime import datetime as dt

# Get the model and test data paths
default_config = cfg.Config()


def create_report(job: Job, output_path: Path, resources: dict = None):
    """
    Create a report of the jobs that were run
    :param job: The job
    :param output_path: Path to write the report to
    :param resources: (optional) The resources dictionary of the cluster
    """

    # create the output path if it doesn't exist
    output_path.mkdir(parents=True, exist_ok=True)

    # create a file name that replaces spaces with underscores and adds a timestamp
    job_report_name = f"{job.name.replace(' ', '_')}_{dt.utcnow().strftime('%Y%m%d')}.txt"
    output_path = output_path / job_report_name
    info(f"Creating job report for {job.name} in {output_path}")

    jobs_p = PydanticJobWithMedias.from_orm(job)
    created_time = jobs_p.createdAt
    num_media = len(jobs_p.media)

    job_report_name = f"{jobs_p.name}, Total media: {num_media}, Created at: {created_time} "

    # Get additional information from the deepsea_ai database if it exists
    if default_config('database', 'gql') and resources:
        try:
            database = api.DeepSeaAIClient(default_config('database', 'gql'))
            jobs_q = database.execute(queries.GET_JOB_SUMMARY, job_uuid=job_hash(f"{resources['PROCESSOR']}{job.name}"))
            if len(jobs_q['data']['jobs']) > 0:
                job_id = jobs_q['data']['jobs'][0]['id']
                job_detail = jobs_q['data']['jobs'][0]['detail']
                debug(f"JobCache: Found job id: {job_id}")
                job_report_name += f", Job: {job_id}, {job_detail}"
        except Exception as e:
            err(f"Unable to fetch job id from deepsea_ai database: {e}")

    # Remove the report if it exists
    if output_path.exists():
        output_path.unlink()

    # Write the report
    with open(output_path.as_posix(), 'w') as f:
        f.write(f"DeepSea-AI {__version__}\n")
        f.write(f"Job: {job_report_name}\n")
        f.write(f"==============================================================================================\n")
        f.write(f"Index, Media, Created, Last Updated, Status\n")

        # Write the status of each media file in the job
        names = [m.name for m in jobs_p.media]
        for idx, name in enumerate(sorted(names)):
            # Get the media with the name
            media = [m for m in jobs_p.media if m.name == name][0]
            f.write(f"{idx}, {name}, {media.createdAt}, {media.updatedAt}, {media.status}\n")

    # Write the report in a web-friendly table format, highlighting the status in red if it is not complete
    # with open(output_path.as_posix().replace('.txt', '.html'), 'w') as f:
    #     f.write(f"<html><head><title>DeepSea-AI {__version__}</title></head><body>")
    #     f.write(f"<h1>Job: {job_report_name}</h1>")
    #     f.write(f"<table border=1><tr><th>Index</th><th>Media</th><th>Last Updated</th><th>Status</th></tr>")
    #     for idx, name in enumerate(sorted(names)):
    #         # Get the media with the name
    #         media = [m for m in jobs_p.media if m.name == name][0]
    #         if media.status != 'COMPLETE':
    #             f.write(f"<tr><td>{idx}</td><td>{name}</td><td>{media.updatedAt}</td><td><font color='red'>{media.status}</font></td></tr>")
    #         else:
    #             f.write(f"<tr><td>{idx}</td><td>{name}</td><td>{media.updatedAt}</td><td>{media.status}</td></tr>")
    #     f.write(f"</table></body></html>")
