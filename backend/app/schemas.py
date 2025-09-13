from pydantic import BaseModel, HttpUrl
from datetime import datetime
from typing import Optional, List
from enum import Enum


class DriveType(str, Enum):
    GOOGLE_DRIVE = "google_drive"
    ONEDRIVE = "onedrive"
    DROPBOX = "dropbox"


class TransferStatus(str, Enum):
    PENDING = "pending"
    SCANNING = "scanning"
    TRANSFERRING = "transferring"
    UPLOADING = "uploading"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TransferCreate(BaseModel):
    source_url: str


class TransferResponse(BaseModel):
    id: str
    source_url: str
    drive_type: DriveType
    status: TransferStatus
    
    total_files: int
    files_completed: int
    current_file_name: Optional[str]
    current_file_progress: float
    overall_progress: float
    
    landing_zone_folder_id: Optional[str]
    notebooklm_notebook_id: Optional[str]
    error_message: Optional[str]
    
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


class FileTransferResponse(BaseModel):
    file_name: str
    file_size: Optional[int]
    status: str
    bytes_transferred: int
    error_message: Optional[str]

    class Config:
        from_attributes = True


class TransferProgress(BaseModel):
    transfer_id: str
    status: TransferStatus
    stage: str
    overall_progress: float
    files_completed: int
    total_files: int
    current_file: Optional[dict] = None
    file_details: List[dict] = []


class URLValidationResponse(BaseModel):
    valid: bool
    drive_type: Optional[DriveType]
    accessible: bool
    error_message: Optional[str]


class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: datetime