# deepsea-ai, Apache-2.0 license
# Filename: database/job/database.py
# Description: Job database

from typing import List

from pydantic_sqlalchemy import sqlalchemy_to_pydantic
from sqlalchemy import Column, ForeignKey, Integer, String, create_engine, func, TIMESTAMP
from sqlalchemy.orm import relationship, sessionmaker, declarative_base

from deepsea_ai.config.config import Config
from deepsea_ai.database.job.misc import JobType, Status
from deepsea_ai.logger import info

Base = declarative_base()


class JobBase(Base):
    __abstract__ = True

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    engine = Column(String, nullable=False)
    job_type = Column(String, nullable=False, default=JobType.SAGEMAKER)
    createdAt = Column(TIMESTAMP(timezone=True),
                       nullable=False, server_default=func.now())


class MediaBase(Base):
    __abstract__ = True

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    status = Column(String, nullable=False, default=Status.UNKNOWN)
    metadata_b64 = Column(String, nullable=True)
    createdAt = Column(TIMESTAMP(timezone=True),
                       nullable=False, server_default=func.now())
    updatedAt = Column(TIMESTAMP(timezone=True),
                       default=None, onupdate=func.now())


class Job(JobBase):
    __tablename__ = "jobs"

    medias = relationship(
        "Media", back_populates="job", cascade="all, delete, delete-orphan"
    )


class Media(MediaBase):
    __tablename__ = "medias"

    job_id = Column(Integer, ForeignKey("jobs.id"))
    job = relationship("Job", back_populates="medias")


PydanticJob = sqlalchemy_to_pydantic(Job)
PydanticMedia = sqlalchemy_to_pydantic(Media)


class PydanticJobWithMedias(PydanticJob):
    medias: List[PydanticMedia] = []


def init_db(cfg: Config, reset: bool = False) -> sessionmaker:
    """
    Initialize the job cache database
    :param cfg: The configuration
    :param reset: Whether to reset the database
    :return: A sessionmaker
    """
    job_db_path = cfg.job_db_path
    account = cfg('aws', 'account_id')

    # Create the output path to store the database if it doesn't exist
    job_db_path.mkdir(parents=True, exist_ok=True)

    # Name the database based on the account number to avoid collisions
    db = f'sqlite_job_cache_{account}.db'
    info(f"Initializing job cache database in {job_db_path} as {db}")
    engine = create_engine(f"sqlite:///{db}", connect_args={"check_same_thread": True}, echo=False)

    if reset:
        # Reset the database
        Base.metadata.drop_all(engine)

    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)