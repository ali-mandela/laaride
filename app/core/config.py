from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # API Settings
    PROJECT_NAME: str = "LaaRide API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # Security Settings
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # App Settings
    IS_DEVELOPMENT: bool = True

    # MongoDB Settings
    MONGODB_URL: str
    DATABASE_NAME: str

    # Firebase Settings
    FIREBASE_PROJECT_ID: str = ""
    FIREBASE_SERVICE_ACCOUNT_KEY: Optional[str] = None

    # CORS
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:8081"]

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    REDIS_URL: Optional[str] = None

    # Logging
    LOG_LEVEL: str = "INFO"

    # Razorpay Settings
    RAZORPAY_KEY_ID: Optional[str] = None
    RAZORPAY_KEY_SECRET: Optional[str] = None
    RAZORPAY_WEBHOOK_SECRET: Optional[str] = None

    # Fast2SMS — Indian OTP delivery (https://fast2sms.com)
    FAST2SMS_API_KEY: Optional[str] = None

    # Backblaze B2 (S3-compatible storage)
    BACKBLAZE_KEY_ID: Optional[str] = None
    BACKBLAZE_APPLICATION_KEY: Optional[str] = None
    BACKBLAZE_BUCKET_NAME: Optional[str] = None
    BACKBLAZE_REGION: str = "us-west-004"

    model_config = SettingsConfigDict(
        env_file=".env", case_sensitive=True, extra="ignore"
    )


settings = Settings()
