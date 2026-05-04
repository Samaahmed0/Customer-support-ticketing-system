from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    database_url: str = "postgresql://ticketing:ticketing@localhost:5432/ticketing"
    rabbitmq_url: str = "amqp://ticketing:ticketing@localhost:5672/"
    service_name: str = "ticket-service"
    log_level: str = "INFO"


settings = Settings()
