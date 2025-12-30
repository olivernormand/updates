from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    elevenlabs_api_key: str
    anthropic_api_key: str
    readwise_access_token: str
    api_base_url: str = "http://localhost:8000"
    debug: bool = False

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
