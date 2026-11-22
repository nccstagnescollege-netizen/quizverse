from typing import List, Optional, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "QUIZVERSE API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"

    # CORS Configuration
    FRONTEND_URL: Optional[str] = "https://quizverse-iota.vercel.app"
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
    SUPER_ADMIN_DEFAULT_EMAIL: str = "dhanush10607@gmail.com"
    SUPER_ADMIN_DEFAULT_PASSWORD: str = "Dhanush@062007"
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

    def validate_production_configuration(self) -> List[str]:
        """
        Validates environment configuration against production standards.
        Returns a list of warnings or advisories without leaking secret values.
        """
        warnings = []
        if self.ENVIRONMENT == "production":
            if not self.DATABASE_URL:
                warnings.append("CRITICAL: DATABASE_URL is not configured for production.")
            if self.SECRET_KEY.startswith("quizverse-jwt-secret-key-change-in-production"):
                warnings.append("SECURITY: Default SECRET_KEY is in use; rotate to an environment-injected secret.")
            if not self.SUPABASE_URL:
                warnings.append("CONFIG: SUPABASE_URL is not configured.")
            if "*" in (self.BACKEND_CORS_ORIGINS if isinstance(self.BACKEND_CORS_ORIGINS, list) else [self.BACKEND_CORS_ORIGINS]):
                warnings.append("SECURITY: Wildcard CORS origin detected in production.")
        elif self.ENVIRONMENT in ("development", "staging", "testing"):
            if not self.DATABASE_URL:
                warnings.append("NOTICE: Running in development mode with local/sqlite database.")
        return warnings

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
