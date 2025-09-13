from prefect import flow, task, get_run_logger
from prefect.context import get_run_context
import asyncio
import uuid
from datetime import datetime
from typing import List, Dict, Any
from sqlalchemy.orm import Session

from app.database import get_db, Transfer, FileTransfer, TransferStatus, DriveType
from app.services.drive_detector import detect_drive_type, validate_drive_url
from app.services.google_drive_service import GoogleDriveService
from app.services.dropbox_service import DropboxService
from app.services.onedrive_service import OneDriveService
from app.services.notebooklm_service import NotebookLMService


async def update_progress(transfer_id: str, status: TransferStatus, **kwargs):
    """Update transfer progress and notify WebSocket clients"""
    from app.main import app
    
    # Update database
    db = next(get_db())
    try:
        transfer = db.query(Transfer).filter(Transfer.id == transfer_id).first()
        if transfer:
            transfer.status = status
            for key, value in kwargs.items():
                if hasattr(transfer, key):
                    setattr(transfer, key, value)
            db.commit()
            
            # Send WebSocket update
            manager = getattr(app.state, 'connection_manager', None)
            if manager:
                progress_data = {
                    "transfer_id": transfer_id,
                    "status": status.value,
                    "overall_progress": transfer.overall_progress,
                    "files_completed": transfer.files_completed,
                    "total_files": transfer.total_files,
                    "current_file": {
                        "name": transfer.current_file_name,
                        "progress": transfer.current_file_progress
                    } if transfer.current_file_name else None
                }
                await manager.send_progress_update(transfer_id, progress_data)
    finally:
        db.close()


@task
async def scan_source_drive(transfer_id: str, source_url: str, drive_type: DriveType):
    """Scan source drive and discover files"""
    logger = get_run_logger()
    logger.info(f"Starting scan of {drive_type.value} drive: {source_url}")
    
    # Update status to scanning
    await update_progress(transfer_id, TransferStatus.SCANNING)
    
    # Get appropriate service based on drive type
    if drive_type == DriveType.GOOGLE_DRIVE:
        service = GoogleDriveService()
    elif drive_type == DriveType.DROPBOX:
        service = DropboxService()
    elif drive_type == DriveType.ONEDRIVE:
        service = OneDriveService()
    else:
        raise ValueError(f"Unsupported drive type: {drive_type}")
    
    # Discover files
    files = await service.list_files(source_url)
    logger.info(f"Discovered {len(files)} files")
    
    # Update database with file list
    db = next(get_db())
    try:
        # Update transfer with total file count
        transfer = db.query(Transfer).filter(Transfer.id == transfer_id).first()
        transfer.total_files = len(files)
        db.commit()
        
        # Create file transfer records
        for file_info in files:
            file_transfer = FileTransfer(
                transfer_id=transfer_id,
                file_name=file_info['name'],
                file_size=file_info.get('size'),
                file_type=file_info.get('type'),
                source_path=file_info['path']
            )
            db.add(file_transfer)
        db.commit()
    finally:
        db.close()
    
    await update_progress(transfer_id, TransferStatus.SCANNING, total_files=len(files))
    return files


@task
async def create_landing_zone(transfer_id: str):
    """Create landing zone folder in Google Drive"""
    logger = get_run_logger()
    
    google_service = GoogleDriveService()
    folder_name = f"ftransport_{transfer_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    folder_id = await google_service.create_folder(folder_name)
    
    logger.info(f"Created landing zone folder: {folder_id}")
    
    # Update database
    await update_progress(transfer_id, TransferStatus.TRANSFERRING, landing_zone_folder_id=folder_id)
    
    return folder_id


@task
async def transfer_single_file(
    transfer_id: str, 
    file_info: Dict[str, Any], 
    landing_zone_id: str,
    source_service: Any
):
    """Transfer a single file from source to Google Drive landing zone"""
    logger = get_run_logger()
    
    file_name = file_info['name']
    logger.info(f"Starting transfer of file: {file_name}")
    
    # Update current file being transferred
    await update_progress(
        transfer_id, 
        TransferStatus.TRANSFERRING,
        current_file_name=file_name,
        current_file_progress=0.0
    )
    
    try:
        # Progress callback for file transfer
        async def progress_callback(bytes_transferred: int, total_bytes: int):
            progress = (bytes_transferred / total_bytes) * 100 if total_bytes > 0 else 0
            await update_progress(
                transfer_id,
                TransferStatus.TRANSFERRING,
                current_file_progress=progress
            )
        
        # Download file from source
        file_content = await source_service.download_file(file_info['path'], progress_callback)
        
        # Upload to Google Drive landing zone
        google_service = GoogleDriveService()
        destination_file_id = await google_service.upload_file(
            file_name, 
            file_content, 
            landing_zone_id,
            progress_callback
        )
        
        # Update file transfer record
        db = next(get_db())
        try:
            file_transfer = db.query(FileTransfer).filter(
                FileTransfer.transfer_id == transfer_id,
                FileTransfer.file_name == file_name
            ).first()
            
            if file_transfer:
                file_transfer.status = "completed"
                file_transfer.destination_path = destination_file_id
                file_transfer.bytes_transferred = len(file_content)
                file_transfer.completed_at = datetime.utcnow()
                db.commit()
        finally:
            db.close()
        
        logger.info(f"Successfully transferred file: {file_name}")
        return destination_file_id
        
    except Exception as e:
        logger.error(f"Failed to transfer file {file_name}: {str(e)}")
        
        # Update file transfer record with error
        db = next(get_db())
        try:
            file_transfer = db.query(FileTransfer).filter(
                FileTransfer.transfer_id == transfer_id,
                FileTransfer.file_name == file_name
            ).first()
            
            if file_transfer:
                file_transfer.status = "failed"
                file_transfer.error_message = str(e)
                db.commit()
        finally:
            db.close()
        
        raise e


@task
async def upload_to_notebooklm(transfer_id: str, landing_zone_id: str):
    """Upload files from landing zone to NotebookLM Enterprise"""
    logger = get_run_logger()
    logger.info("Starting upload to NotebookLM Enterprise")
    
    await update_progress(transfer_id, TransferStatus.UPLOADING)
    
    notebooklm_service = NotebookLMService()
    
    # Create notebook
    notebook_id = await notebooklm_service.create_notebook(f"FTransport_{transfer_id}")
    
    # Get files from landing zone
    google_service = GoogleDriveService()
    files = await google_service.list_files_in_folder(landing_zone_id)
    
    # Upload each file to NotebookLM
    for file_info in files:
        await notebooklm_service.upload_file(notebook_id, file_info)
    
    await update_progress(
        transfer_id, 
        TransferStatus.COMPLETED,
        notebooklm_notebook_id=notebook_id,
        completed_at=datetime.utcnow()
    )
    
    logger.info(f"Successfully uploaded to NotebookLM: {notebook_id}")
    return notebook_id


@flow(name="data_transfer_workflow")
async def data_transfer_workflow(transfer_id: str, source_url: str):
    """Main workflow for transferring data from shared drives to NotebookLM Enterprise"""
    logger = get_run_logger()
    logger.info(f"Starting data transfer workflow for: {source_url}")
    
    try:
        # Detect drive type
        drive_type = await detect_drive_type(source_url)
        
        # Scan source drive
        files = await scan_source_drive(transfer_id, source_url, drive_type)
        
        # Create landing zone
        landing_zone_id = await create_landing_zone(transfer_id)
        
        # Get source service
        if drive_type == DriveType.GOOGLE_DRIVE:
            source_service = GoogleDriveService()
        elif drive_type == DriveType.DROPBOX:
            source_service = DropboxService()
        elif drive_type == DriveType.ONEDRIVE:
            source_service = OneDriveService()
        
        # Transfer files one by one
        transferred_files = []
        for i, file_info in enumerate(files):
            try:
                file_id = await transfer_single_file(
                    transfer_id, 
                    file_info, 
                    landing_zone_id,
                    source_service
                )
                transferred_files.append(file_id)
                
                # Update overall progress
                progress = ((i + 1) / len(files)) * 100
                await update_progress(
                    transfer_id,
                    TransferStatus.TRANSFERRING,
                    files_completed=i + 1,
                    overall_progress=progress
                )
                
            except Exception as e:
                logger.error(f"Failed to transfer file {file_info['name']}: {str(e)}")
                continue
        
        # Upload to NotebookLM Enterprise
        notebook_id = await upload_to_notebooklm(transfer_id, landing_zone_id)
        
        logger.info(f"Workflow completed successfully. Notebook ID: {notebook_id}")
        return notebook_id
        
    except Exception as e:
        logger.error(f"Workflow failed: {str(e)}")
        await update_progress(
            transfer_id, 
            TransferStatus.FAILED,
            error_message=str(e)
        )
        raise e