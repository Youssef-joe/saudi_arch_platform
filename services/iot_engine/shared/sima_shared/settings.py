from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    ENV: str = "dev"
    JWT_SECRET: str = "change_me"
    ADMIN_EMAIL: str = "admin@sima.local"
    ADMIN_PASSWORD: str = "Admin@12345"

    POSTGRES_HOST: str = "db"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "sima"
    POSTGRES_USER: str = "sima"
    POSTGRES_PASSWORD: str = "sima"

    REDIS_URL: str = "redis://redis:6379/0"

    S3_ENDPOINT: str = "http://minio:9000"
    S3_ACCESS_KEY: str = "minioadmin"
    S3_SECRET_KEY: str = "minioadmin"
    S3_BUCKET: str = "sima"
    S3_REGION: str = "us-east-1"

    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4.1-mini"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
