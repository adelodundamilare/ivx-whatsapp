from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "IVX WhatsApp Assistant"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    # SECRET_KEY: str
    # ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    # REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    GRAPH_API_TOKEN: str
    WEBHOOK_VERIFY_TOKEN: str
    WHATSAPP_BUSINESS_ACCOUNT_ID: str

    BUBBLE_API_KEY: str
    BUBBLE_API_URL: str
    OPENAI_API_KEY: str

    # Database Configuration
    # DATABASE_HOST: str
    # DATABASE_PORT: str
    # DATABASE_USER: str
    # DATABASE_PASSWORD: str
    # DATABASE_NAME: str

    # DATABASE_URL: str = ""

    # def __init__(self, **data):
    #     super().__init__(**data)
    #     self.DATABASE_URL = (
    #         f'postgresql://{self.DATABASE_USER}:{self.DATABASE_PASSWORD}'
    #         f'@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}'
    #     )

    # Email
    # SMTP_SERVER: str
    # SMTP_PORT: int
    # SMTP_USERNAME: str
    # SMTP_PASSWORD: str
    # EMAILS_FROM_EMAIL: str
    # EMAILS_FROM_NAME: str

    # CLOUDINARY_CLOUD_NAME: str
    # CLOUDINARY_API_KEY: str
    # CLOUDINARY_API_SECRET: str

    class Config:
        env_file = ".env"

settings = Settings()