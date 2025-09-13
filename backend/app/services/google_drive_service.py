import os
import io
from typing import List, Dict, Any, Callable, Optional
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload
from googleapiclient.errors import HttpError
import urllib.parse
import re

from app.config import settings


class GoogleDriveService:
    def __init__(self):
        self.credentials = None
        self.service = None
        self._initialize_service()
    
    def _initialize_service(self):
        """Initialize Google Drive service with service account credentials"""
        try:
            if settings.google_service_account_key and os.path.exists(settings.google_service_account_key):
                self.credentials = service_account.Credentials.from_service_account_file(
                    settings.google_service_account_key,
                    scopes=['https://www.googleapis.com/auth/drive']
                )
                self.service = build('drive', 'v3', credentials=self.credentials)
                
                # Debug: Print the actual project ID being used
                import json
                with open(settings.google_service_account_key, 'r') as f:
                    key_data = json.load(f)
                    print(f"✅ Google Drive service initialized")
                    print(f"📋 Service Account Project: {key_data.get('project_id')}")
                    print(f"📋 Service Account Email: {key_data.get('client_email')}")
            else:
                print(f"❌ Service account key not found at: {settings.google_service_account_key}")
        except Exception as e:
            print(f"❌ Failed to initialize Google Drive service: {str(e)}")
    
    def _extract_folder_id_from_url(self, url: str) -> str:
        """Extract folder ID from Google Drive URL"""
        # Pattern for different Google Drive URL formats
        patterns = [
            r'/folders/([a-zA-Z0-9-_]+)',  # https://drive.google.com/drive/folders/ID
            r'/folderview\?id=([a-zA-Z0-9-_]+)',  # Legacy format
            r'id=([a-zA-Z0-9-_]+)'  # Generic id parameter
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        # If no pattern matches, assume the last part after / is the ID
        return url.split('/')[-1].split('?')[0]
    
    async def list_files(self, source_url: str) -> List[Dict[str, Any]]:
        """Scan and list all files in a Google Drive folder"""
        if not self.service:
            raise Exception("Google Drive service not initialized")
        
        folder_id = self._extract_folder_id_from_url(source_url)
        print(f"📁 Scanning Google Drive folder: {folder_id}")
        
        files = []
        try:
            # Get files in the folder recursively
            files = await self._list_files_recursive(folder_id)
            print(f"📊 Found {len(files)} files in Google Drive folder")
            return files
        except HttpError as e:
            print(f"❌ Error accessing Google Drive folder: {str(e)}")
            if e.resp.status == 404:
                raise Exception(f"Folder not found or not accessible: {folder_id}")
            elif e.resp.status == 403:
                raise Exception(f"Permission denied accessing folder: {folder_id}")
            else:
                raise Exception(f"Google Drive API error: {str(e)}")
    
    async def _list_files_recursive(self, folder_id: str, path: str = "") -> List[Dict[str, Any]]:
        """Recursively list all files in a folder and its subfolders"""
        files = []
        page_token = None
        
        while True:
            try:
                # Query for files in this folder
                query = f"'{folder_id}' in parents and trashed=false"
                results = self.service.files().list(
                    q=query,
                    pageSize=100,
                    pageToken=page_token,
                    fields="nextPageToken, files(id, name, size, mimeType, parents, modifiedTime)"
                ).execute()
                
                items = results.get('files', [])
                
                for item in items:
                    file_path = f"{path}/{item['name']}" if path else item['name']
                    
                    if item['mimeType'] == 'application/vnd.google-apps.folder':
                        # It's a folder, recurse into it
                        subfolder_files = await self._list_files_recursive(item['id'], file_path)
                        files.extend(subfolder_files)
                    else:
                        # It's a file
                        files.append({
                            'id': item['id'],
                            'name': item['name'],
                            'path': file_path,
                            'size': int(item.get('size', 0)) if item.get('size') else 0,
                            'type': item['mimeType'],
                            'modified': item.get('modifiedTime'),
                            'parent_id': folder_id
                        })
                
                page_token = results.get('nextPageToken')
                if not page_token:
                    break
                    
            except HttpError as e:
                print(f"❌ Error listing files in folder {folder_id}: {str(e)}")
                break
        
        return files
    
    async def download_file(self, file_id: str, progress_callback: Optional[Callable] = None) -> bytes:
        """Download a file from Google Drive"""
        if not self.service:
            raise Exception("Google Drive service not initialized")
        
        try:
            # Get file metadata
            file_metadata = self.service.files().get(fileId=file_id).execute()
            file_size = int(file_metadata.get('size', 0))
            
            # Download the file
            request = self.service.files().get_media(fileId=file_id)
            file_io = io.BytesIO()
            downloader = MediaIoBaseDownload(file_io, request)
            
            done = False
            downloaded_bytes = 0
            
            while not done:
                status, done = downloader.next_chunk()
                if status:
                    downloaded_bytes = int(status.resumable_progress)
                    if progress_callback and file_size > 0:
                        await progress_callback(downloaded_bytes, file_size)
            
            file_io.seek(0)
            return file_io.read()
            
        except HttpError as e:
            print(f"❌ Error downloading file {file_id}: {str(e)}")
            raise Exception(f"Failed to download file: {str(e)}")
    
    async def create_folder(self, folder_name: str, parent_folder_id: Optional[str] = None) -> str:
        """Create a folder in Google Drive"""
        if not self.service:
            raise Exception("Google Drive service not initialized")
        
        try:
            # Use the configured landing zone as parent if none specified
            if not parent_folder_id:
                parent_folder_id = settings.google_drive_landing_zone
            
            folder_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            
            if parent_folder_id:
                folder_metadata['parents'] = [parent_folder_id]
            
            folder = self.service.files().create(
                body=folder_metadata,
                fields='id'
            ).execute()
            
            folder_id = folder.get('id')
            print(f"📁 Created folder '{folder_name}' with ID: {folder_id}")
            return folder_id
            
        except HttpError as e:
            print(f"❌ Error creating folder: {str(e)}")
            raise Exception(f"Failed to create folder: {str(e)}")
    
    async def upload_file(
        self, 
        file_name: str, 
        file_content: bytes, 
        parent_folder_id: str,
        progress_callback: Optional[Callable] = None
    ) -> str:
        """Upload a file to Google Drive"""
        if not self.service:
            raise Exception("Google Drive service not initialized")
        
        try:
            # Prepare file metadata
            file_metadata = {
                'name': file_name,
                'parents': [parent_folder_id]
            }
            
            # Create media upload
            file_io = io.BytesIO(file_content)
            media = MediaIoBaseUpload(
                file_io, 
                mimetype='application/octet-stream',
                resumable=True
            )
            
            # Upload the file
            request = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            )
            
            response = None
            uploaded_bytes = 0
            total_bytes = len(file_content)
            
            while response is None:
                status, response = request.next_chunk()
                if status:
                    uploaded_bytes = int(status.resumable_progress)
                    if progress_callback:
                        await progress_callback(uploaded_bytes, total_bytes)
            
            file_id = response.get('id')
            print(f"📄 Uploaded file '{file_name}' with ID: {file_id}")
            return file_id
            
        except HttpError as e:
            print(f"❌ Error uploading file: {str(e)}")
            raise Exception(f"Failed to upload file: {str(e)}")
    
    async def copy_file_direct(
        self, 
        source_file_id: str, 
        dest_folder_id: str, 
        new_name: Optional[str] = None,
        progress_callback: Optional[Callable] = None
    ) -> str:
        """Copy a file directly within Google Drive (more efficient than download/upload)"""
        if not self.service:
            raise Exception("Google Drive service not initialized")
        
        try:
            # Get source file metadata
            source_file = self.service.files().get(fileId=source_file_id).execute()
            
            # Prepare copy metadata
            copy_metadata = {
                'parents': [dest_folder_id]
            }
            
            if new_name:
                copy_metadata['name'] = new_name
            else:
                copy_metadata['name'] = source_file['name']
            
            # Copy the file
            copied_file = self.service.files().copy(
                fileId=source_file_id,
                body=copy_metadata,
                fields='id'
            ).execute()
            
            # Simulate progress for UI feedback
            if progress_callback:
                await progress_callback(100, 100)
            
            file_id = copied_file.get('id')
            print(f"📄 Copied file '{source_file['name']}' to folder {dest_folder_id}")
            return file_id
            
        except HttpError as e:
            print(f"❌ Error copying file: {str(e)}")
            raise Exception(f"Failed to copy file: {str(e)}")
    
    async def list_files_in_folder(self, folder_id: str) -> List[Dict[str, Any]]:
        """List files in a specific folder (for NotebookLM upload)"""
        if not self.service:
            raise Exception("Google Drive service not initialized")
        
        try:
            query = f"'{folder_id}' in parents and trashed=false and mimeType != 'application/vnd.google-apps.folder'"
            results = self.service.files().list(
                q=query,
                fields="files(id, name, size, mimeType, webViewLink)"
            ).execute()
            
            return results.get('files', [])
            
        except HttpError as e:
            print(f"❌ Error listing files in folder: {str(e)}")
            raise Exception(f"Failed to list files: {str(e)}")