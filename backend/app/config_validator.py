"""
Configuration validation module for FTransport.
Validates that all required configuration is present before app startup.
"""

import os
import sys
from pathlib import Path
from typing import List, Tuple
from app.config import settings


class ConfigValidationError(Exception):
    """Raised when configuration validation fails"""
    pass


class ConfigValidator:
    """Validates application configuration"""
    
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    def validate_file_path(self, file_path: str, description: str, required: bool = True) -> bool:
        """Validate that a file path exists"""
        if not file_path:
            if required:
                self.errors.append(f"❌ {description}: Path not configured")
                return False
            else:
                self.warnings.append(f"⚠️ {description}: Not configured (optional)")
                return True
        
        if not os.path.exists(file_path):
            if required:
                self.errors.append(f"❌ {description}: File not found at {file_path}")
                return False
            else:
                self.warnings.append(f"⚠️ {description}: File not found at {file_path} (optional)")
                return True
        
        # Additional checks for readable files
        if not os.path.isfile(file_path):
            if required:
                self.errors.append(f"❌ {description}: Path exists but is not a file: {file_path}")
                return False
        
        if not os.access(file_path, os.R_OK):
            if required:
                self.errors.append(f"❌ {description}: File exists but is not readable: {file_path}")
                return False
        
        return True
    
    def validate_string(self, value: str, description: str, required: bool = True) -> bool:
        """Validate that a string value is present"""
        if not value or value.strip() == "":
            if required:
                self.errors.append(f"❌ {description}: Not configured")
                return False
            else:
                self.warnings.append(f"⚠️ {description}: Not configured (optional)")
                return True
        return True
    
    def validate_secret_key(self, secret_key: str) -> bool:
        """Validate secret key security"""
        if not secret_key:
            self.errors.append("❌ Secret Key: Not configured")
            return False
        
        # Check for default/insecure values
        insecure_keys = [
            "your-secret-key-here-change-in-production-REQUIRED",
            "dev-secret-key-change-in-production",
            "secret",
            "password",
            "12345"
        ]
        
        if secret_key in insecure_keys:
            self.errors.append("❌ Secret Key: Using default/insecure secret key")
            return False
        
        if len(secret_key) < 32:
            self.errors.append("❌ Secret Key: Too short (minimum 32 characters)")
            return False
        
        return True
    
    def validate_google_service_account(self) -> bool:
        """Validate Google service account configuration"""
        success = True
        
        # Check service account key file
        if not self.validate_file_path(
            settings.google_service_account_key,
            "Google Service Account Key File",
            required=True
        ):
            success = False
        else:
            # Additional validation for JSON format
            try:
                import json
                with open(settings.google_service_account_key, 'r') as f:
                    key_data = json.load(f)
                    
                    required_fields = [
                        'type', 'project_id', 'private_key_id', 'private_key',
                        'client_email', 'client_id', 'auth_uri', 'token_uri'
                    ]
                    
                    for field in required_fields:
                        if field not in key_data:
                            self.errors.append(f"❌ Google Service Account: Missing field '{field}' in key file")
                            success = False
                    
                    if key_data.get('type') != 'service_account':
                        self.errors.append("❌ Google Service Account: Invalid key type (expected 'service_account')")
                        success = False
                        
            except json.JSONDecodeError:
                self.errors.append("❌ Google Service Account: Key file is not valid JSON")
                success = False
            except Exception as e:
                self.errors.append(f"❌ Google Service Account: Error reading key file: {str(e)}")
                success = False
        
        # Check project ID
        if not self.validate_string(
            getattr(settings, 'google_cloud_project_id', None),
            "Google Cloud Project ID",
            required=True
        ):
            success = False
        
        return success
    
    def validate_database_config(self) -> bool:
        """Validate database configuration"""
        if not self.validate_string(settings.database_url, "Database URL", required=True):
            return False
        
        # Additional validation for SQLite
        if settings.database_url.startswith('sqlite:'):
            # Extract file path from SQLite URL
            db_path = settings.database_url.replace('sqlite:///', '').replace('sqlite://', '')
            if db_path and db_path != ':memory:':
                # Check if directory exists (create if needed for SQLite)
                db_dir = os.path.dirname(db_path) if os.path.dirname(db_path) else '.'
                if not os.path.exists(db_dir):
                    try:
                        os.makedirs(db_dir, exist_ok=True)
                    except Exception as e:
                        self.errors.append(f"❌ Database: Cannot create directory {db_dir}: {str(e)}")
                        return False
        
        return True
    
    def validate_all(self) -> Tuple[bool, List[str], List[str]]:
        """Validate all configuration"""
        self.errors.clear()
        self.warnings.clear()
        
        print("🔍 Validating FTransport configuration...")
        
        # Critical configuration
        print("📋 Validating critical configuration...")
        self.validate_database_config()
        self.validate_secret_key(getattr(settings, 'secret_key', None))
        
        # Google Cloud configuration
        print("📋 Validating Google Cloud configuration...")
        self.validate_google_service_account()
        
        # Optional configuration
        print("📋 Validating optional configuration...")
        self.validate_string(
            getattr(settings, 'notebooklm_project_id', None),
            "NotebookLM Project ID",
            required=False
        )
        
        # Check if we have any integration configured
        has_integration = any([
            getattr(settings, 'dropbox_app_key', None),
            getattr(settings, 'onedrive_client_id', None),
            getattr(settings, 'notebooklm_project_id', None)
        ])
        
        if not has_integration:
            self.warnings.append("⚠️ No optional integrations configured (Dropbox, OneDrive, NotebookLM)")
        
        success = len(self.errors) == 0
        return success, self.errors, self.warnings


def validate_config_or_exit():
    """Validate configuration and exit if validation fails"""
    validator = ConfigValidator()
    success, errors, warnings = validator.validate_all()
    
    # Print warnings
    if warnings:
        print("\n⚠️ Configuration Warnings:")
        for warning in warnings:
            print(f"  {warning}")
    
    # Handle errors
    if not success:
        print("\n❌ Configuration Validation Failed!")
        print("The following critical issues must be resolved:")
        for error in errors:
            print(f"  {error}")
        
        print("\n💡 To fix these issues:")
        print("  1. Check your .env file configuration")
        print("  2. Ensure all required files exist and are readable")
        print("  3. Verify Google Cloud service account setup")
        print("  4. Use a secure secret key for production")
        
        print("\n🚫 Application startup aborted due to configuration errors.")
        sys.exit(1)
    
    print("✅ Configuration validation passed!")
    return True


if __name__ == "__main__":
    # Allow running this module directly for testing
    validate_config_or_exit()