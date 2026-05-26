from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "retail"
    postgres_user: str = "airflow"
    postgres_password: str = "airflow"
    llm_provider: str = "ollama"
    ollama_base_url: str = "http://host.docker.internal:11434"
    ollama_model: str = "qwen2.5:3b"
    yandex_api_key: str = ""
    yandex_base_url: str = "https://llm.api.cloud.yandex.net/v1"
    yandex_model: str = "gpt://<folder_id>/yandexgpt-lite/latest"
    llm_timeout_seconds: float = 60.0
    disable_data_logging: bool = True
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
