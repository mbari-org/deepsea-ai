# deepsea-ai, Apache-2.0 license
# Filename: commands/monitor.py
# Description: Thread to monitor the status of processing jobs in an ECS cluster.

import time
from pathlib import Path
from threading import Thread

from sqlalchemy.orm import sessionmaker

from deepsea_ai.commands.monitor_utils import log_scaling_activities, log_queue_status
from deepsea_ai.database.job.misc import JobType
from deepsea_ai.database.report_generator import create_report
from deepsea_ai.logger import info, warn, err
from deepsea_ai.database.job.database import Job, Media
from deepsea_ai.database.job.database_helper import json_b64_decode

default_update_period = 60 * 30  # 30 minutes


class Monitor(Thread):
    """
    A new single threaded executor to run the monitor and update the status.
    Run one per cluster.
    """

    def __init__(self, session_maker: sessionmaker,
                 report_path: Path,
                 resources: dict,
                 update_period: int = default_update_period,
                 sim: bool = False):
        """
        :param session_maker: Session maker to connect to the database
        :param report_path: Path to save the report
        :param resources: Dictionary of resources in the cluster
        :param update_period: Period to update the status of jobs messages in the queues
        :param sim: If true, simulate the monitor
        """
        Thread.__init__(self)
        self.report_path = report_path
        self.resources = resources
        self.update_period = update_period
        self.sim = sim
        self.session_maker = session_maker

        info(f'Creating report path {self.report_path} if it does not exist.')
        self.report_path.mkdir(parents=True, exist_ok=True)

    def run(self):
        try:
            if self.sim:
                with self.session_maker() as db:
                    # check the status of the job in the database
                    job = db.query(Job).first()
                    if job:
                        create_report(job, self.report_path, self.resources)
                return

            # Run forever until Ctrl-C
            while True:
                num_activities = log_scaling_activities(self.resources, num_records=10)

                queue_dict = log_queue_status(self.session_maker, self.resources)
                queue_activity = sum([int(i) for i in queue_dict.values()])

                if num_activities == 0 and queue_activity == 0:
                    info(f'No activity for {self.resources["PROCESSOR"]}.')
                else:
                    # Generate a report every update_period when there is activity
                    if queue_activity > 0:
                        info(f"Getting all media being processed in cluster {self.resources['CLUSTER']}")

                        with self.session_maker() as db:
                            # Get all jobs with the job type ECS
                            jobs_in_clusters = db.query(Job).filter(Job.job_type == JobType.ECS).all()

                            # Get all media in the jobs that are in the cluster
                            for job in jobs_in_clusters:
                                medias = db.query(Media).filter(Media.job_id == job.id).all()
                                info(f"Found {len(medias)} media in job {job.name}")
                                if len(medias) > 0:  # if there are media in the cluster, create a report
                                    create_report(job, self.report_path, self.resources)

                info(f'Checking again in {self.update_period} seconds. Ctrl-C to stop.')
                time.sleep(self.update_period)
        except KeyboardInterrupt:
            pass
        except Exception as e:
            err(e)
            raise e