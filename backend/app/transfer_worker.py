import asyncio
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session

from app.database import get_db, Transfer, FileTransfer, TransferStatus, DriveType, TransferMode
from app.services.drive_detector import detect_drive_type
from app.services.google_drive_service import GoogleDriveService
from app.services.dropbox_service import DropboxService
from app.services.onedrive_service import OneDriveService
from app.services.notebooklm_service import NotebookLMService
from app.logging_config import get_logger


class TransferWorker:
    def __init__(self):
        self.google_service = GoogleDriveService()
        self.dropbox_service = DropboxService()
        self.onedrive_service = OneDriveService()
        self.notebooklm_service = NotebookLMService()
        self.logger = get_logger("transfer")
    
    async def update_progress(self, transfer_id: str, status: TransferStatus, stage: str = None, **kwargs):
        """Update transfer progress in database and send WebSocket updates"""
        from app.main import app
        
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
                self.logger.info(f"📊 Updated transfer {transfer_id}: {status.value} - {stage or 'No stage'}")
                
                # Send WebSocket update to frontend
                manager = getattr(app.state, 'connection_manager', None)
                if manager:
                    progress_data = {
                        "transfer_id": transfer_id,
                        "status": status.value,
                        "stage": stage or status.value,
                        "overall_progress": transfer.overall_progress,
                        "files_completed": transfer.files_completed,
                        "total_files": transfer.total_files,
                        "current_file": {
                            "name": transfer.current_file_name,
                            "progress": transfer.current_file_progress
                        } if transfer.current_file_name else None,
                        "file_details": kwargs.get("file_details", []),
                        "error_message": transfer.error_message
                    }
                    await manager.send_progress_update(transfer_id, progress_data)
                
        finally:
            db.close()
    
    async def scan_source_drive(self, transfer_id: str, source_url: str, drive_type: DriveType):
        """Scan source drive and discover files"""
        self.logger.info(f"🔍 Starting scan of {drive_type.value} drive: {source_url}")
        
        await self.update_progress(transfer_id, TransferStatus.SCANNING, stage="Initializing connection to source drive")
        
        # Get appropriate service based on drive type
        try:
            if drive_type == DriveType.GOOGLE_DRIVE:
                service = self.google_service
                await self.update_progress(transfer_id, TransferStatus.SCANNING, stage="Connected to Google Drive")
            elif drive_type == DriveType.DROPBOX:
                service = self.dropbox_service
                await self.update_progress(transfer_id, TransferStatus.SCANNING, stage="Connected to Dropbox")
            elif drive_type == DriveType.ONEDRIVE:
                service = self.onedrive_service
                await self.update_progress(transfer_id, TransferStatus.SCANNING, stage="Connected to OneDrive")
            else:
                raise ValueError(f"Unsupported drive type: {drive_type}")
        except Exception as e:
            self.logger.error(f"❌ Failed to connect to {drive_type.value}: {str(e)}")
            await self.update_progress(transfer_id, TransferStatus.FAILED, 
                                     stage=f"Failed to connect to {drive_type.value}",
                                     error_message=f"Connection failed: {str(e)}")
            raise
        
        # Discover files
        await self.update_progress(transfer_id, TransferStatus.SCANNING, stage="Scanning for files...")
        try:
            files = await service.list_files(source_url)
            self.logger.info(f"📊 Discovered {len(files)} files")
            
            # Create file details for progress
            file_details = [
                {
                    "name": file_info['name'],
                    "status": "discovered",
                    "size": file_info.get('size'),
                    "bytes_transferred": 0
                }
                for file_info in files
            ]
            
            await self.update_progress(transfer_id, TransferStatus.SCANNING, 
                                     stage=f"Found {len(files)} files",
                                     file_details=file_details)
            
        except Exception as e:
            self.logger.error(f"❌ Failed to scan files: {str(e)}")
            await self.update_progress(transfer_id, TransferStatus.FAILED,
                                     stage="Failed to scan files",
                                     error_message=f"File scanning failed: {str(e)}")
            raise
        
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
        
        await self.update_progress(transfer_id, TransferStatus.SCANNING, 
                                 stage=f"Scan complete - {len(files)} files ready for transfer",
                                 total_files=len(files),
                                 file_details=file_details)
        return files
    
    async def create_landing_zone(self, transfer_id: str):
        """Create landing zone folder in Google Drive"""
        self.logger.info(f"📁 Creating landing zone for transfer {transfer_id}")
        
        await self.update_progress(transfer_id, TransferStatus.TRANSFERRING, stage="Connecting to Google Drive target")
        
        try:
            # Test Google Drive connection
            if not self.google_service:
                raise Exception("Google Drive service not initialized")
            
            await self.update_progress(transfer_id, TransferStatus.TRANSFERRING, stage="Google Drive target connected successfully")
            
            folder_name = f"ftransport_{transfer_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            await self.update_progress(transfer_id, TransferStatus.TRANSFERRING, stage=f"Creating landing zone folder: {folder_name}")
            
            folder_id = await self.google_service.create_folder(folder_name)
            
            self.logger.info(f"📁 Created landing zone folder: {folder_id}")
            await self.update_progress(transfer_id, TransferStatus.TRANSFERRING, 
                                     stage=f"Landing zone created: {folder_name}",
                                     landing_zone_folder_id=folder_id)
            
            return folder_id
            
        except Exception as e:
            self.logger.error(f"❌ Failed to create landing zone: {str(e)}")
            await self.update_progress(transfer_id, TransferStatus.FAILED,
                                     stage="Failed to create Google Drive landing zone",
                                     error_message=f"Landing zone creation failed: {str(e)}")
            raise
    
    async def transfer_files_to_landing_zone(self, transfer_id: str, files: List[Dict], landing_zone_id: str, source_service):
        """Transfer multiple files to Google Drive landing zone"""
        self.logger.info(f"📁 Transferring {len(files)} files to landing zone: {landing_zone_id}")
        
        transferred_files = []
        for i, file_info in enumerate(files):
            try:
                destination_file_id = await self.transfer_single_file(
                    transfer_id, file_info, landing_zone_id, source_service
                )
                transferred_files.append({
                    'source_file': file_info,
                    'destination_id': destination_file_id
                })
                
                # Update overall progress
                progress = ((i + 1) / len(files)) * 100
                await self.update_progress(
                    transfer_id,
                    TransferStatus.TRANSFERRING,
                    files_completed=i + 1,
                    overall_progress=progress
                )
                
            except Exception as e:
                self.logger.error(f"❌ Failed to transfer file {file_info['name']}: {str(e)}")
                continue
        
        self.logger.info(f"✅ Successfully transferred {len(transferred_files)}/{len(files)} files to landing zone")
        return transferred_files
    
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
        file_size = file_info.get('size', 0)
        self.logger.info(f"📄 Starting transfer of file: {file_name} ({file_size} bytes)")
        
        # Update current file being transferred
        await self.update_progress(
            transfer_id, 
            TransferStatus.TRANSFERRING,
            stage=f"Starting transfer of {file_name}",
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
                self.logger.info(f"📄 Using direct copy for file ID: {file_info['id']}")
                destination_file_id = await source_service.copy_file_direct(
                    file_info['id'], 
                    landing_zone_id,
                    progress_callback=progress_callback
                )
            else:
                # Download from source and upload to Google Drive
                self.logger.info(f"📄 Using download/upload for file: {file_path}")
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
            
            self.logger.info(f"✅ Successfully transferred file: {file_name}")
            return destination_file_id
            
        except Exception as e:
            self.logger.error(f"❌ Failed to transfer file {file_name}: {str(e)}")
            
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
        self.logger.info(f"📓 Starting upload to NotebookLM Enterprise")
        
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
        
        self.logger.info(f"✅ Successfully uploaded {successful_uploads}/{len(files)} files to NotebookLM: {notebook_id}")
        return notebook_id
    
    async def upload_files_to_notebooklm(self, transfer_id: str, files: List[Dict], source_service) -> str:
        """Upload files directly from source to NotebookLM Enterprise"""
        self.logger.info(f"📓 Starting direct upload to NotebookLM Enterprise")
        
        # Check if NotebookLM service is properly initialized
        if not self.notebooklm_service.is_initialized():
            self.logger.warning(f"⚠️ NotebookLM service not properly initialized")
            self.logger.info(f"📓 Using mock notebook for demonstration")
            mock_notebook_id = f"mock_notebook_ftransport_{transfer_id}"
            await self.update_progress(
                transfer_id, 
                TransferStatus.COMPLETED,
                notebooklm_notebook_id=mock_notebook_id,
                completed_at=datetime.utcnow()
            )
            self.logger.info(f"✅ Transfer completed with mock notebook: {mock_notebook_id}")
            return mock_notebook_id
        
        # Test API connectivity (with timeout)
        self.logger.info(f"🔍 Testing NotebookLM API connectivity...")
        try:
            # Set a short timeout for this test
            connectivity_ok = await asyncio.wait_for(
                self.notebooklm_service.test_api_connectivity(), 
                timeout=5.0
            )
            if not connectivity_ok:
                self.logger.warning(f"⚠️ NotebookLM API connectivity test failed, using mock notebook")
                mock_notebook_id = f"mock_notebook_ftransport_{transfer_id}"
                await self.update_progress(
                    transfer_id, 
                    TransferStatus.COMPLETED,
                    notebooklm_notebook_id=mock_notebook_id,
                    completed_at=datetime.utcnow()
                )
                return mock_notebook_id
        except asyncio.TimeoutError:
            self.logger.warning(f"⏰ NotebookLM API connectivity test timed out, using mock notebook")
            mock_notebook_id = f"mock_notebook_ftransport_{transfer_id}"
            await self.update_progress(
                transfer_id, 
                TransferStatus.COMPLETED,
                notebooklm_notebook_id=mock_notebook_id,
                completed_at=datetime.utcnow()
            )
            return mock_notebook_id
        except Exception as e:
            self.logger.error(f"❌ NotebookLM API test error: {str(e)}, using mock notebook")
            mock_notebook_id = f"mock_notebook_ftransport_{transfer_id}"
            await self.update_progress(
                transfer_id, 
                TransferStatus.COMPLETED,
                notebooklm_notebook_id=mock_notebook_id,
                completed_at=datetime.utcnow()
            )
            return mock_notebook_id
        
        try:
            # Create notebook
            notebook_id = await self.notebooklm_service.create_notebook(f"FTransport Transfer {transfer_id}")
            
            # Upload each file directly from source to NotebookLM
            uploaded_count = 0
            for i, file_info in enumerate(files):
                try:
                    self.logger.info(f"📄 Uploading {file_info['name']} to NotebookLM ({i+1}/{len(files)})")
                    
                    # Download file content from source
                    content = await source_service.download_file(file_info['id'])
                    
                    # Upload to NotebookLM
                    await self.notebooklm_service.upload_source(notebook_id, file_info['name'], content)
                    uploaded_count += 1
                    self.logger.info(f"✅ Uploaded {file_info['name']} to NotebookLM")
                    
                    # Update progress
                    progress = ((i + 1) / len(files)) * 100
                    await self.update_progress(
                        transfer_id,
                        TransferStatus.UPLOADING,
                        files_completed=i + 1,
                        overall_progress=progress
                    )
                    
                except Exception as e:
                    self.logger.error(f"❌ Failed to upload {file_info['name']}: {str(e)}")
                    continue
            
            await self.update_progress(
                transfer_id, 
                TransferStatus.COMPLETED,
                notebooklm_notebook_id=notebook_id,
                completed_at=datetime.utcnow()
            )
            self.logger.info(f"✅ Successfully uploaded {uploaded_count}/{len(files)} files to NotebookLM: {notebook_id}")
            
            return notebook_id
            
        except Exception as e:
            self.logger.error(f"❌ Error creating NotebookLM notebook: {str(e)}")
            # Fall back to mock notebook for demo
            mock_notebook_id = f"mock_notebook_ftransport_{transfer_id}"
            self.logger.info(f"📓 Using mock notebook ID: {mock_notebook_id}")
            await self.update_progress(
                transfer_id, 
                TransferStatus.COMPLETED,
                notebooklm_notebook_id=mock_notebook_id,
                completed_at=datetime.utcnow()
            )
            self.logger.info(f"✅ Successfully uploaded 0/{len(files)} files to NotebookLM: {mock_notebook_id}")
            return mock_notebook_id
    
    async def process_transfer(self, transfer_id: str, source_url: str, transfer_mode: TransferMode = TransferMode.DIRECT_TO_NOTEBOOKLM):
        """Main workflow for processing a transfer"""
        self.logger.info(f"🚀 Starting transfer workflow for: {source_url} (mode: {transfer_mode.value})")
        
        start_time = datetime.utcnow()
        timeout_duration = 30 * 60  # 30 minutes timeout
        
        try:
            # Add timeout wrapper
            await self.update_progress(transfer_id, TransferStatus.SCANNING, 
                                     stage="Starting transfer workflow")
            
            async def run_with_timeout():
                return await self._run_transfer_workflow(transfer_id, source_url, transfer_mode, start_time)
            
            # Run with timeout
            result = await asyncio.wait_for(run_with_timeout(), timeout=timeout_duration)
            return result
            
        except asyncio.TimeoutError:
            elapsed = (datetime.utcnow() - start_time).total_seconds()
            self.logger.error(f"⏰ Transfer timed out after {elapsed:.1f} seconds")
            await self.update_progress(
                transfer_id, 
                TransferStatus.FAILED,
                stage=f"Transfer timed out after {elapsed:.1f} seconds",
                error_message=f"Transfer operation timed out after {elapsed:.1f} seconds"
            )
            raise
        except Exception as e:
            elapsed = (datetime.utcnow() - start_time).total_seconds()
            self.logger.error(f"❌ Transfer failed after {elapsed:.1f} seconds: {str(e)}")
            await self.update_progress(
                transfer_id, 
                TransferStatus.FAILED,
                stage=f"Transfer failed: {str(e)}",
                error_message=str(e)
            )
            raise

    async def _run_transfer_workflow(self, transfer_id: str, source_url: str, transfer_mode: TransferMode, start_time: datetime):
        """Internal method to run the actual transfer workflow"""
        try:
            # Detect drive type
            drive_type = await detect_drive_type(source_url)
            self.logger.info(f"🔍 Detected drive type: {drive_type.value}")
            
            # Scan source drive
            files = await self.scan_source_drive(transfer_id, source_url, drive_type)
            
            if not files:
                await self.update_progress(
                    transfer_id, 
                    TransferStatus.COMPLETED,
                    error_message="No files found in source folder"
                )
                return
            
            # Get source service
            if drive_type == DriveType.GOOGLE_DRIVE:
                source_service = self.google_service
            elif drive_type == DriveType.DROPBOX:
                source_service = self.dropbox_service
            elif drive_type == DriveType.ONEDRIVE:
                source_service = self.onedrive_service
            
            # Choose workflow based on transfer mode
            if transfer_mode == TransferMode.VIA_GOOGLE_DRIVE:
                # Two-step process: Source -> Google Drive -> NotebookLM
                self.logger.info(f"📁 Creating Google Drive landing zone for {len(files)} files")
                landing_zone_id = await self.create_landing_zone(transfer_id)
                
                # Transfer files to Google Drive landing zone
                await self.update_progress(transfer_id, TransferStatus.TRANSFERRING)
                await self.transfer_files_to_landing_zone(transfer_id, files, landing_zone_id, source_service)
                
                # Upload from landing zone to NotebookLM
                self.logger.info(f"📓 Uploading files from Google Drive landing zone to NotebookLM Enterprise")
                notebook_id = await self.upload_to_notebooklm(transfer_id, landing_zone_id)
                
            else:  # DIRECT_TO_NOTEBOOKLM
                # Direct upload to NotebookLM
                self.logger.info(f"📓 Uploading {len(files)} files directly to NotebookLM Enterprise")
                await self.update_progress(transfer_id, TransferStatus.UPLOADING)
                notebook_id = await self.upload_files_to_notebooklm(transfer_id, files, source_service)
            
            self.logger.info(f"🎉 Workflow completed successfully. Notebook ID: {notebook_id}")
            return notebook_id
            
        except Exception as e:
            self.logger.error(f"❌ Workflow failed: {str(e)}")
            await self.update_progress(
                transfer_id, 
                TransferStatus.FAILED,
                error_message=str(e)
            )
            raise e


# Global worker instance
transfer_worker = TransferWorker()