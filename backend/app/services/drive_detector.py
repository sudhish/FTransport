from urllib.parse import urlparse
import re
from app.database import DriveType


async def detect_drive_type(url: str) -> DriveType:
    """Detect the type of shared drive from URL"""
    parsed_url = urlparse(url.lower())
    domain = parsed_url.netloc
    
    # Google Drive patterns
    if 'drive.google.com' in domain or 'docs.google.com' in domain:
        return DriveType.GOOGLE_DRIVE
    
    # OneDrive patterns
    if any(pattern in domain for pattern in ['onedrive.live.com', 'onedrive.com', '1drv.ms', 'sharepoint.com']):
        return DriveType.ONEDRIVE
    
    # Dropbox patterns
    if 'dropbox.com' in domain or 'db.tt' in domain:
        return DriveType.DROPBOX
    
    # Default fallback - could also raise an exception
    raise ValueError(f"Unable to detect drive type from URL: {url}")


async def validate_drive_url(url: str) -> dict:
    """Validate if the URL is accessible and extract metadata"""
    try:
        drive_type = await detect_drive_type(url)
        
        # Basic URL format validation
        parsed_url = urlparse(url)
        if not parsed_url.scheme or not parsed_url.netloc:
            return {
                "valid": False,
                "drive_type": None,
                "accessible": False,
                "error_message": "Invalid URL format"
            }
        
        # TODO: Add actual accessibility checks by making API calls
        # For now, just return basic validation
        return {
            "valid": True,
            "drive_type": drive_type,
            "accessible": True,
            "error_message": None
        }
        
    except ValueError as e:
        return {
            "valid": False,
            "drive_type": None,
            "accessible": False,
            "error_message": str(e)
        }
    except Exception as e:
        return {
            "valid": False,
            "drive_type": None,
            "accessible": False,
            "error_message": f"Validation error: {str(e)}"
        }