from typing import List, Optional, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "QUIZVERSE API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"

    # CORS Configuration
    BACKEND_CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://quizverse.vercel.app",
        "https://quizverse-iota.vercel.app",
    ]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # Supabase PostgreSQL Database Settings
    DATABASE_URL: Optional[str] = None
    SUPABASE_URL: Optional[str] = None
    SUPABASE_KEY: Optional[str] = None  # Anon public key
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = None  # Server-side privileged key
    SUPABASE_JWT_SECRET: Optional[str] = None

    # Security & RBAC Configuration
    SECRET_KEY: str = "quizverse-jwt-secret-key-change-in-production-only-super-safe-32b"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 hours

    # Super Admin Bootstrap Settings
    SUPER_ADMIN_DEFAULT_EMAIL: str = "superadmin@quizverse.io"
    SUPER_ADMIN_DEFAULT_PASSWORD: str = "QuizverseSuperAdmin2026!"
    SUPER_ADMIN_DEFAULT_NAME: str = "System Super Administrator"

    @property
    def effective_jwt_secret(self) -> str:
        """Returns the configured Supabase JWT secret or fallback system secret key."""
        return self.SUPABASE_JWT_SECRET or self.SECRET_KEY

    # Optional Future Integrations
    REDIS_URL: Optional[str] = None

    # Server Runtime Settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
