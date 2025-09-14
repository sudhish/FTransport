import os
import yaml
from pathlib import Path
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class AppConfig(BaseModel):
    name: str = "FTransport"
    version: str = "1.0.0"
    environment: str = "development"


class APIConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:8080"]


class DatabaseConfig(BaseModel):
    url: str = "sqlite:///./ftransport.db"
    echo: bool = False


class SecurityConfig(BaseModel):
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    secret_key: Optional[str] = None


class GoogleConfig(BaseModel):
    service_account_key_path: Optional[str] = None
    project_id: Optional[str] = None
    drive_landing_zone_id: Optional[str] = None
    scopes: List[str] = [
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/cloud-platform"
    ]


class DropboxConfig(BaseModel):
    app_key: Optional[str] = None
    app_secret: Optional[str] = None


class OneDriveConfig(BaseModel):
    client_id: Optional[str] = None
    client_secret: Optional[str] = None


class NotebookLMConfig(BaseModel):
    project_id: Optional[str] = None
    api_base_url: str = "https://aiplatform.googleapis.com/v1"


class IntegrationsConfig(BaseModel):
    dropbox: DropboxConfig = DropboxConfig()
    onedrive: OneDriveConfig = OneDriveConfig()
    notebooklm: NotebookLMConfig = NotebookLMConfig()


class EmailConfig(BaseModel):
    enabled: bool = False
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None


class TransferConfig(BaseModel):
    max_concurrent: int = 5
    max_file_size_gb: int = 2
    min_transfer_rate_mbps: int = 10
    retry_attempts: int = 3
    retry_delay_seconds: int = 5


class MonitoringConfig(BaseModel):
    log_level: str = "INFO"
    enable_metrics: bool = True
    enable_health_checks: bool = True


class Settings(BaseSettings):
    app: AppConfig = AppConfig()
    api: APIConfig = APIConfig()
    database: DatabaseConfig = DatabaseConfig()
    security: SecurityConfig = SecurityConfig()
    google: GoogleConfig = GoogleConfig()
    integrations: IntegrationsConfig = IntegrationsConfig()
    email: EmailConfig = EmailConfig()
    transfer: TransferConfig = TransferConfig()
    monitoring: MonitoringConfig = MonitoringConfig()
    
    class Config:
        env_file = ".env"
        env_nested_delimiter = "__"
        extra = "allow"  # Allow extra fields and dynamic attributes


def load_yaml_config(config_path: str) -> Dict[str, Any]:
    """Load configuration from YAML file"""
    try:
        with open(config_path, 'r') as file:
            return yaml.safe_load(file) or {}
    except FileNotFoundError:
        print(f"⚠️ Config file not found: {config_path}")
        return {}
    except Exception as e:
        print(f"❌ Error loading config file {config_path}: {str(e)}")
        return {}


def create_settings() -> Settings:
    """Create settings with proper configuration precedence"""
    
    # Get configuration environment
    config_env = os.getenv("FTRANSPORT_ENV", "development")
    print(f"🔧 Loading FTransport configuration for environment: {config_env}")
    
    # Configuration file paths
    config_dir = Path(__file__).parent.parent / "config"
    default_config_path = config_dir / "default.yml"
    env_config_path = config_dir / f"{config_env}.yml"
    
    # Load configurations in order of precedence (later overrides earlier)
    config = {}
    
    # 1. Load default config
    default_config = load_yaml_config(str(default_config_path))
    if default_config:
        config.update(default_config)
        print(f"✅ Loaded default configuration")
    
    # 2. Load environment-specific config
    env_config = load_yaml_config(str(env_config_path))
    if env_config:
        config.update(env_config)
        print(f"✅ Loaded {config_env} configuration")
    
    # 3. Override with environment variables (highest precedence)
    env_overrides = {}
    
    # Map environment variables to config structure
    env_mappings = {
        # Database
        "DATABASE_URL": "database.url",
        
        # Security
        "SECRET_KEY": "security.secret_key",
        "ACCESS_TOKEN_EXPIRE_MINUTES": "security.access_token_expire_minutes",
        
        # Google Cloud
        "GOOGLE_SERVICE_ACCOUNT_KEY": "google.service_account_key_path",
        "GOOGLE_CLOUD_PROJECT_ID": "google.project_id", 
        "GOOGLE_DRIVE_LANDING_ZONE": "google.drive_landing_zone_id",
        
        # Integrations
        "DROPBOX_APP_KEY": "integrations.dropbox.app_key",
        "DROPBOX_APP_SECRET": "integrations.dropbox.app_secret",
        "ONEDRIVE_CLIENT_ID": "integrations.onedrive.client_id",
        "ONEDRIVE_CLIENT_SECRET": "integrations.onedrive.client_secret",
        "NOTEBOOKLM_PROJECT_ID": "integrations.notebooklm.project_id",
        
        # Email
        "SMTP_HOST": "email.smtp_host",
        "SMTP_PORT": "email.smtp_port",
        "SMTP_USER": "email.smtp_user", 
        "SMTP_PASSWORD": "email.smtp_password",
        
        # API
        "API_HOST": "api.host",
        "API_PORT": "api.port",
    }
    
    for env_var, config_path in env_mappings.items():
        env_value = os.getenv(env_var)
        if env_value:
            # Set nested config value
            keys = config_path.split('.')
            current = env_overrides
            for key in keys[:-1]:
                if key not in current:
                    current[key] = {}
                current = current[key]
            current[keys[-1]] = env_value
            print(f"🔐 Environment override: {env_var}")
    
    # Merge environment overrides
    def deep_merge(base: Dict, override: Dict) -> Dict:
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                deep_merge(base[key], value)
            else:
                base[key] = value
        return base
    
    if env_overrides:
        config = deep_merge(config, env_overrides)
    
    # Ensure nested configs have proper structure
    if 'integrations' not in config:
        config['integrations'] = {}
    if 'dropbox' not in config['integrations']:
        config['integrations']['dropbox'] = {}
    if 'onedrive' not in config['integrations']:
        config['integrations']['onedrive'] = {}
    if 'notebooklm' not in config['integrations']:
        config['integrations']['notebooklm'] = {}
    
    # Create Settings instance from merged config
    try:
        settings = Settings(**config)
        print(f"✅ Configuration loaded successfully")
        return settings
    except Exception as e:
        print(f"❌ Error creating settings: {str(e)}")
        print("🔄 Falling back to default settings")
        return Settings()


# Global settings instance
settings = create_settings()

# Backwards compatibility properties for existing code
settings.database_url = settings.database.url
settings.google_service_account_key = settings.google.service_account_key_path
settings.notebooklm_project_id = settings.integrations.notebooklm.project_id
settings.google_drive_landing_zone = settings.google.drive_landing_zone_id
settings.dropbox_app_key = settings.integrations.dropbox.app_key
settings.dropbox_app_secret = settings.integrations.dropbox.app_secret
settings.onedrive_client_id = settings.integrations.onedrive.client_id
settings.onedrive_client_secret = settings.integrations.onedrive.client_secret
settings.secret_key = settings.security.secret_key or "dev-secret-key-change-in-production"
settings.algorithm = settings.security.algorithm
settings.access_token_expire_minutes = settings.security.access_token_expire_minutes
settings.allowed_origins = settings.api.cors_origins