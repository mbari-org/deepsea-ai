# deepsea-ai, Apache-2.0 license
# Filename: database/job/database.py
# Description: Job database

from typing import List

import boto3
from pydantic_sqlalchemy import sqlalchemy_to_pydantic
from sqlalchemy import Column, ForeignKey, Integer, String, create_engine, func, TIMESTAMP
from sqlalchemy.engine import Engine
# from sqlalchemy.engine import Engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, relationship, sessionmaker
# from sqlalchemy.orm.decl_api import _DeclarativeBase

from deepsea_ai.config.config import Config
from deepsea_ai.database.job.misc import JobType, Status
from deepsea_ai.logger import warn, info

Base = declarative_base()


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    cluster = Column(String, nullable=False)
    job_type = Column(String, nullable=False, default=JobType.SAGEMAKER)
    createdAt = Column(TIMESTAMP(timezone=True),
                       nullable=False, server_default=func.now())

    medias = relationship(
        "Media", back_populates="job", cascade="all, delete, delete-orphan"
    )


class Media(Base):
    __tablename__ = "medias"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    status = Column(String, nullable=False, default=Status.UNKNOWN)
    job_id = Column(Integer, ForeignKey("jobs.id"))
    createdAt = Column(TIMESTAMP(timezone=True),
                       nullable=False, server_default=func.now())
    updatedAt = Column(TIMESTAMP(timezone=True),
                       default=None, onupdate=func.now())

    job = relationship("Job", back_populates="medias")


PydanticJob = sqlalchemy_to_pydantic(Job)
PydanticMedia = sqlalchemy_to_pydantic(Media)


class PydanticJobWithMedias(PydanticJob):
    medias: List[PydanticMedia] = []


def init_db(cfg: Config) -> tuple[Session, Engine]:
    """
    Initialize the job cache database
    :param cfg: The configuration
    :return: The database session
    """
    job_db_path = cfg.job_db_path
    account = cfg('aws', 'account_id')

    # Create the output path to store the database if it doesn't exist
    job_db_path.mkdir(parents=True, exist_ok=True)

    # Name the database based on the account number to avoid collisions
    db = f'sqlite_job_cache_{account}.db'
    info(f"Initializing job cache database in {job_db_path} as {db}")
    engine = create_engine(f"sqlite:///{db}", connect_args={"check_same_thread": False}, echo=False)

    Base.metadata.create_all(engine)
    LocalSession = sessionmaker(bind=engine)
    db: Session = LocalSession()
    return db, engine


def reset_local_db(cfg: Config) -> Session:
    _, engine = init_db(cfg)
    # Reset the database
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    LocalSession = sessionmaker(bind=engine)
    db_reset: Session = LocalSession()
    return db_reset