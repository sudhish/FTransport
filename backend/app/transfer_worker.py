import asyncio
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.database import get_db, Transfer, FileTransfer, TransferStatus, DriveType
from app.services.drive_detector import detect_drive_type
from app.services.google_drive_service import GoogleDriveService
from app.services.dropbox_service import DropboxService
from app.services.onedrive_service import OneDriveService
from app.services.notebooklm_service import NotebookLMService


class TransferWorker:
    def __init__(self):
        self.google_service = GoogleDriveService()
        self.dropbox_service = DropboxService()
        self.onedrive_service = OneDriveService()
        self.notebooklm_service = NotebookLMService()
    
    async def update_progress(self, transfer_id: str, status: TransferStatus, **kwargs):
        """Update transfer progress in database"""
        db = next(get_db())
        try:
            transfer = db.query(Transfer).filter(Transfer.id == transfer_id).first()
            if transfer:
                transfer.status = status
                for key, value in kwargs.items():
                    if hasattr(transfer, key):
                        setattr(transfer, key, value)
                
                # Set started_at when first moving from PENDING
                if status != TransferStatus.PENDING and not transfer.started_at:
                    transfer.started_at = datetime.utcnow()
                
                # Set completed_at when finished
                if status in [TransferStatus.COMPLETED, TransferStatus.FAILED, TransferStatus.CANCELLED]:
                    transfer.completed_at = datetime.utcnow()
                
                db.commit()
                print(f"📊 Updated transfer {transfer_id}: {status.value}")
                
                # TODO: Send WebSocket update to frontend
                # manager.send_progress_update(transfer_id, progress_data)
                
        finally:
            db.close()
    
    async def scan_source_drive(self, transfer_id: str, source_url: str, drive_type: DriveType):
        """Scan source drive and discover files"""
        print(f"🔍 Starting scan of {drive_type.value} drive: {source_url}")
        
        await self.update_progress(transfer_id, TransferStatus.SCANNING)
        
        # Get appropriate service based on drive type
        if drive_type == DriveType.GOOGLE_DRIVE:
            service = self.google_service
        elif drive_type == DriveType.DROPBOX:
            service = self.dropbox_service
        elif drive_type == DriveType.ONEDRIVE:
            service = self.onedrive_service
        else:
            raise ValueError(f"Unsupported drive type: {drive_type}")
        
        # Discover files
        files = await service.list_files(source_url)
        print(f"📊 Discovered {len(files)} files")
        
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
                    source_path=file_info['path'],
                    status="pending"
                )
                db.add(file_transfer)
            db.commit()
        finally:
            db.close()
        
        await self.update_progress(transfer_id, TransferStatus.SCANNING, total_files=len(files))
        return files
    
    async def create_landing_zone(self, transfer_id: str):
        """Create landing zone folder in Google Drive"""
        print(f"📁 Creating landing zone for transfer {transfer_id}")
        
        folder_name = f"ftransport_{transfer_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        folder_id = await self.google_service.create_folder(folder_name)
        
        print(f"📁 Created landing zone folder: {folder_id}")
        await self.update_progress(transfer_id, TransferStatus.TRANSFERRING, landing_zone_folder_id=folder_id)
        
        return folder_id
    
    async def transfer_single_file(
        self, 
        transfer_id: str, 
        file_info: Dict[str, Any], 
        landing_zone_id: str,
        source_service: Any
    ):
        """Transfer a single file to Google Drive landing zone"""
        file_name = file_info['name']
        file_path = file_info['path']
        print(f"📄 Starting transfer of file: {file_name}")
        
        # Update current file being transferred
        await self.update_progress(
            transfer_id, 
            TransferStatus.TRANSFERRING,
            current_file_name=file_name,
            current_file_progress=0.0
        )
        
        # Update file status to in_progress
        db = next(get_db())
        try:
            file_transfer = db.query(FileTransfer).filter(
                FileTransfer.transfer_id == transfer_id,
                FileTransfer.file_name == file_name
            ).first()
            
            if file_transfer:
                file_transfer.status = "in_progress"
                file_transfer.started_at = datetime.utcnow()
                db.commit()
        finally:
            db.close()
        
        try:
            # Progress callback for file transfer
            async def progress_callback(bytes_transferred: int, total_bytes: int):
                progress = (bytes_transferred / total_bytes) * 100 if total_bytes > 0 else 0
                await self.update_progress(
                    transfer_id,
                    TransferStatus.TRANSFERRING,
                    current_file_progress=progress
                )
                
                # Update file transfer record
                db = next(get_db())
                try:
                    file_transfer = db.query(FileTransfer).filter(
                        FileTransfer.transfer_id == transfer_id,
                        FileTransfer.file_name == file_name
                    ).first()
                    if file_transfer:
                        file_transfer.bytes_transferred = bytes_transferred
                        db.commit()
                finally:
                    db.close()
            
            destination_file_id = None
            
            # For Google Drive to Google Drive, use direct copy (more efficient)
            if isinstance(source_service, self.google_service.__class__) and 'id' in file_info:
                print(f"📄 Using direct copy for file ID: {file_info['id']}")
                destination_file_id = await source_service.copy_file_direct(
                    file_info['id'], 
                    landing_zone_id,
                    progress_callback=progress_callback
                )
            else:
                # Download from source and upload to Google Drive
                print(f"📄 Using download/upload for file: {file_path}")
                file_content = await source_service.download_file(file_info['id'], progress_callback)
                destination_file_id = await self.google_service.upload_file(
                    file_name, 
                    file_content, 
                    landing_zone_id,
                    progress_callback
                )
            
            # Update file transfer record as completed
            db = next(get_db())
            try:
                file_transfer = db.query(FileTransfer).filter(
                    FileTransfer.transfer_id == transfer_id,
                    FileTransfer.file_name == file_name
                ).first()
                
                if file_transfer:
                    file_transfer.status = "completed"
                    file_transfer.destination_path = destination_file_id
                    file_transfer.bytes_transferred = file_info.get('size', 0)
                    file_transfer.completed_at = datetime.utcnow()
                    db.commit()
            finally:
                db.close()
            
            print(f"✅ Successfully transferred file: {file_name}")
            return destination_file_id
            
        except Exception as e:
            print(f"❌ Failed to transfer file {file_name}: {str(e)}")
            
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
    
    async def upload_to_notebooklm(self, transfer_id: str, landing_zone_id: str):
        """Upload files from landing zone to NotebookLM Enterprise"""
        print(f"📓 Starting upload to NotebookLM Enterprise")
        
        await self.update_progress(transfer_id, TransferStatus.UPLOADING)
        
        # Create notebook
        notebook_id = await self.notebooklm_service.create_notebook(f"FTransport_{transfer_id}")
        
        # Get files from landing zone
        files = await self.google_service.list_files_in_folder(landing_zone_id)
        
        # Upload each file to NotebookLM
        successful_uploads = 0
        for file_info in files:
            try:
                success = await self.notebooklm_service.upload_file(notebook_id, file_info)
                if success:
                    successful_uploads += 1
            except Exception as e:
                print(f"❌ Failed to upload {file_info['name']} to NotebookLM: {str(e)}")
        
        await self.update_progress(
            transfer_id, 
            TransferStatus.COMPLETED,
            notebooklm_notebook_id=notebook_id,
            completed_at=datetime.utcnow()
        )
        
        print(f"✅ Successfully uploaded {successful_uploads}/{len(files)} files to NotebookLM: {notebook_id}")
        return notebook_id
    
    async def process_transfer(self, transfer_id: str, source_url: str):
        """Main workflow for processing a transfer"""
        print(f"🚀 Starting transfer workflow for: {source_url}")
        
        try:
            # Detect drive type
            drive_type = await detect_drive_type(source_url)
            print(f"🔍 Detected drive type: {drive_type.value}")
            
            # Scan source drive
            files = await self.scan_source_drive(transfer_id, source_url, drive_type)
            
            if not files:
                await self.update_progress(
                    transfer_id, 
                    TransferStatus.COMPLETED,
                    error_message="No files found in source folder"
                )
                return
            
            # Create landing zone
            landing_zone_id = await self.create_landing_zone(transfer_id)
            
            # Get source service
            if drive_type == DriveType.GOOGLE_DRIVE:
                source_service = self.google_service
            elif drive_type == DriveType.DROPBOX:
                source_service = self.dropbox_service
            elif drive_type == DriveType.ONEDRIVE:
                source_service = self.onedrive_service
            
            # Transfer files one by one
            transferred_files = []
            for i, file_info in enumerate(files):
                try:
                    file_id = await self.transfer_single_file(
                        transfer_id, 
                        file_info, 
                        landing_zone_id,
                        source_service
                    )
                    transferred_files.append(file_id)
                    
                    # Update overall progress
                    progress = ((i + 1) / len(files)) * 100
                    await self.update_progress(
                        transfer_id,
                        TransferStatus.TRANSFERRING,
                        files_completed=i + 1,
                        overall_progress=progress
                    )
                    
                except Exception as e:
                    print(f"❌ Failed to transfer file {file_info['name']}: {str(e)}")
                    continue
            
            # Upload to NotebookLM Enterprise
            notebook_id = await self.upload_to_notebooklm(transfer_id, landing_zone_id)
            
            print(f"🎉 Workflow completed successfully. Notebook ID: {notebook_id}")
            return notebook_id
            
        except Exception as e:
            print(f"❌ Workflow failed: {str(e)}")
            await self.update_progress(
                transfer_id, 
                TransferStatus.FAILED,
                error_message=str(e)
            )
            raise e


# Global worker instance
transfer_worker = TransferWorker()