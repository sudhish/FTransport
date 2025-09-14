from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import uuid
from datetime import datetime

from app.database import get_db, Transfer, FileTransfer, TransferStatus, TransferMode
from app.schemas import TransferCreate, TransferResponse, FileTransferResponse, URLValidationResponse
from app.services.drive_detector import detect_drive_type, validate_drive_url
from app.transfer_worker import transfer_worker
from app.logging_config import get_logger

router = APIRouter()
api_logger = get_logger("api")


@router.post("/", response_model=TransferResponse)
async def create_transfer(
    transfer_data: TransferCreate,
    db: Session = Depends(get_db)
):
    """Start a new data transfer"""
    
    # Validate URL and detect drive type
    validation = await validate_drive_url(transfer_data.source_url)
    if not validation["valid"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=validation["error_message"]
        )
    
    # Create transfer record
    transfer_id = str(uuid.uuid4())
    transfer = Transfer(
        id=transfer_id,
        source_url=transfer_data.source_url,
        drive_type=validation["drive_type"],
        transfer_mode=transfer_data.transfer_mode,
        status=TransferStatus.PENDING,
        created_at=datetime.utcnow()
    )
    
    db.add(transfer)
    db.commit()
    db.refresh(transfer)
    
    # Start the transfer workflow asynchronously
    import asyncio
    asyncio.create_task(transfer_worker.process_transfer(transfer_id, transfer_data.source_url, transfer_data.transfer_mode))
    api_logger.info(f"🚀 Transfer workflow started: {transfer_id} for URL: {transfer_data.source_url} (mode: {transfer_data.transfer_mode.value})")
    
    return transfer


@router.get("/", response_model=List[TransferResponse])
def list_transfers(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get list of all transfers"""
    transfers = db.query(Transfer).offset(skip).limit(limit).all()
    return transfers


@router.get("/{transfer_id}", response_model=TransferResponse)
def get_transfer(
    transfer_id: str,
    db: Session = Depends(get_db)
):
    """Get details of a specific transfer"""
    transfer = db.query(Transfer).filter(Transfer.id == transfer_id).first()
    if not transfer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transfer not found"
        )
    return transfer


@router.get("/{transfer_id}/files", response_model=List[FileTransferResponse])
def get_transfer_files(
    transfer_id: str,
    db: Session = Depends(get_db)
):
    """Get list of files in a transfer"""
    # Verify transfer exists
    transfer = db.query(Transfer).filter(Transfer.id == transfer_id).first()
    if not transfer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transfer not found"
        )
    
    files = db.query(FileTransfer).filter(FileTransfer.transfer_id == transfer_id).all()
    return files


@router.delete("/{transfer_id}")
def cancel_transfer(
    transfer_id: str,
    db: Session = Depends(get_db)
):
    """Cancel an active transfer"""
    api_logger.info(f"🚫 Cancelling transfer: {transfer_id}")
    transfer = db.query(Transfer).filter(Transfer.id == transfer_id).first()
    if not transfer:
        api_logger.warning(f"⚠️ Transfer not found for cancellation: {transfer_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transfer not found"
        )
    
    if transfer.status in [TransferStatus.COMPLETED, TransferStatus.FAILED, TransferStatus.CANCELLED]:
        api_logger.warning(f"⚠️ Cannot cancel transfer {transfer_id} with status: {transfer.status.value}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel transfer with status: {transfer.status.value}"
        )
    
    # TODO: Actually cancel the running Prefect workflow
    transfer.status = TransferStatus.CANCELLED
    db.commit()
    api_logger.info(f"✅ Transfer cancelled successfully: {transfer_id}")
    
    return {"message": "Transfer cancelled successfully"}


@router.delete("/")
def clear_completed_transfers(
    db: Session = Depends(get_db)
):
    """Clear all completed, failed, and cancelled transfers"""
    api_logger.info("🧹 Clearing completed/failed/cancelled transfers")
    try:
        # Delete completed, failed, and cancelled transfers
        deleted_count = db.query(Transfer).filter(
            Transfer.status.in_([
                TransferStatus.COMPLETED,
                TransferStatus.FAILED,
                TransferStatus.CANCELLED
            ])
        ).delete(synchronize_session=False)
        
        db.commit()
        api_logger.info(f"✅ Successfully cleared {deleted_count} transfers")
        
        return {
            "message": f"Successfully cleared {deleted_count} transfers",
            "cleared_count": deleted_count
        }
    except Exception as e:
        db.rollback()
        api_logger.error(f"❌ Failed to clear transfers: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear transfers: {str(e)}"
        )


@router.get("/{transfer_id}/status")
def get_transfer_status(
    transfer_id: str,
    db: Session = Depends(get_db)
):
    """Get current status of a transfer"""
    transfer = db.query(Transfer).filter(Transfer.id == transfer_id).first()
    if not transfer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transfer not found"
        )
    
    # Get file details
    files = db.query(FileTransfer).filter(FileTransfer.transfer_id == transfer_id).all()
    file_details = [
        {
            "name": f.file_name,
            "status": f.status,
            "size": f.file_size,
            "bytes_transferred": f.bytes_transferred
        }
        for f in files
    ]
    
    return {
        "transfer_id": transfer_id,
        "status": transfer.status.value,
        "overall_progress": transfer.overall_progress,
        "files_completed": transfer.files_completed,
        "total_files": transfer.total_files,
        "current_file": {
            "name": transfer.current_file_name,
            "progress": transfer.current_file_progress
        } if transfer.current_file_name else None,
        "file_details": file_details,
        "error_message": transfer.error_message
    }


@router.post("/validate-url", response_model=URLValidationResponse)
async def validate_url(url_data: dict):
    """Validate a shared drive URL"""
    url = url_data.get("url")
    if not url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="URL is required"
        )
    
    validation = await validate_drive_url(url)
    return URLValidationResponse(**validation)