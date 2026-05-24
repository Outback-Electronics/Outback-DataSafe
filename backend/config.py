import os
from pathlib import Path
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Server settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Storage paths
    BASE_DIR: Path = Path(__file__).parent.parent
    STORAGE_DIR: Path = BASE_DIR / "storage"
    FILES_DIR: Path = STORAGE_DIR / "files"
    PHOTOS_DIR: Path = STORAGE_DIR / "photos"
    THUMBNAILS_DIR: Path = STORAGE_DIR / "thumbnails"
    DATABASE_PATH: Path = BASE_DIR / "data" / "database.db"
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-this")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 1 week
    
    # Storage tiers/plans (in bytes)
    STORAGE_TIERS: dict = {
        "free": 15 * 1024 * 1024 * 1024,      # 15GB free
        "basic": 100 * 1024 * 1024 * 1024,     # 100GB
        "standard": 200 * 1024 * 1024 * 1024,  # 200GB
        "premium": 2 * 1024 * 1024 * 1024 * 1024,  # 2TB
        "ultimate": 10 * 1024 * 1024 * 1024 * 1024  # 10TB
    }
    
    # Default tier for new users
    DEFAULT_TIER: str = os.getenv("DEFAULT_TIER", "free")
    
    # Photo settings
    MAX_PHOTO_SIZE: int = 50 * 1024 * 1024  # 50 MB
    THUMBNAIL_SIZE: int = 300
    SUPPORTED_PHOTO_FORMATS: list = [".jpg", ".jpeg", ".png", ".webp", ".heic"]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Create directories
        self.STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        self.FILES_DIR.mkdir(parents=True, exist_ok=True)
        self.PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
        self.THUMBNAILS_DIR.mkdir(parents=True, exist_ok=True)
        self.DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

settings = Settings()
