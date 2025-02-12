from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "IVX WhatsApp Assistant"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    GRAPH_API_TOKEN: str
    WEBHOOK_VERIFY_TOKEN: str
    WHATSAPP_BUSINESS_ACCOUNT_ID: str

    BUBBLE_API_KEY: str
    BUBBLE_API_URL: str
    OPENAI_API_KEY: str

    class Config:
        env_file = ".env"

settings = Settings()