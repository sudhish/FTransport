from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Float, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import enum

from app.config import settings

# Create database engine
engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class TransferStatus(enum.Enum):
    PENDING = "pending"
    SCANNING = "scanning"
    TRANSFERRING = "transferring"
    UPLOADING = "uploading"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DriveType(enum.Enum):
    GOOGLE_DRIVE = "google_drive"
    ONEDRIVE = "onedrive"
    DROPBOX = "dropbox"


class Transfer(Base):
    __tablename__ = "transfers"

    id = Column(String, primary_key=True, index=True)
    source_url = Column(String, nullable=False)
    drive_type = Column(Enum(DriveType), nullable=False)
    status = Column(Enum(TransferStatus), default=TransferStatus.PENDING)
    
    # Progress tracking
    total_files = Column(Integer, default=0)
    files_completed = Column(Integer, default=0)
    current_file_name = Column(String)
    current_file_progress = Column(Float, default=0.0)
    overall_progress = Column(Float, default=0.0)
    
    # Metadata
    landing_zone_folder_id = Column(String)
    notebooklm_notebook_id = Column(String)
    error_message = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    # User info (simplified for MVP)
    user_id = Column(String, default="default_user")


class FileTransfer(Base):
    __tablename__ = "file_transfers"

    id = Column(Integer, primary_key=True, index=True)
    transfer_id = Column(String, nullable=False, index=True)
    
    file_name = Column(String, nullable=False)
    file_size = Column(Integer)
    file_type = Column(String)
    source_path = Column(String)
    destination_path = Column(String)
    
    status = Column(String, default="pending")  # pending, in_progress, completed, failed
    bytes_transferred = Column(Integer, default=0)
    error_message = Column(Text)
    
    started_at = Column(DateTime)
    completed_at = Column(DateTime)


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()