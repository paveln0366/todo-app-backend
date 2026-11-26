from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    DATABASE_URL: str
    redis_url: str
    cache_ttl_seconds: int
    cache_tasks_key: str
    cors_allowed_origins: list[str]


def get_settings() -> Settings:
    return Settings(
        DATABASE_URL="postgresql+psycopg://postgres:admin@127.0.0.1:15432/postgres",
        redis_url="redis://localhost:6379/0",
        cache_ttl_seconds=3600,
        cache_tasks_key="cache:tasks_list",
        cors_allowed_origins=["http://localhost:3000"],
    )
