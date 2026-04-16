from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class AppConfig:
    app_name: str
    environment: str
    host: str
    port: int
    openai_api_key: str
    openai_model: str
    openai_reasoning_effort: str
    openai_timeout_seconds: float
    openai_store: bool
    use_openai: bool
    groq_api_key: str
    groq_model: str
    groq_temperature: float
    use_groq: bool
    llm_provider: str
    public_base_url: str
    frontend_origin: str
    allowed_origins: list[str]
    mongodb_uri: str
    mongodb_database: str
    use_mongodb: bool
    google_client_id: str
    google_client_secret: str
    jwt_secret: str
    jwt_expiration_minutes: int
    auth_skip_google_verification: bool
    auth_mode: str
    demo_user_email: str
    demo_user_name: str

    @classmethod
    def from_env(cls, base_dir: Path | None = None) -> "AppConfig":
        root = base_dir or Path.cwd()
        _load_env_file(root / ".env")
        allowed_origins = [
            origin.strip()
            for origin in os.getenv("ALLOWED_ORIGINS", "*").split(",")
            if origin.strip()
        ]
        openai_api_key = os.getenv("OPENAI_API_KEY", "")
        use_openai = os.getenv("USE_OPENAI", "true").lower() == "true" and bool(openai_api_key)
        groq_api_key = os.getenv("GROQ_API_KEY", "")
        use_groq = os.getenv("USE_GROQ", "true").lower() == "true" and bool(groq_api_key)
        mongodb_uri = os.getenv("MONGODB_URI", "")
        frontend_origin = os.getenv("FRONTEND_ORIGIN", "http://127.0.0.1:3000")
        llm_provider = "groq" if use_groq else "openai" if use_openai else "stub"

        return cls(
            app_name=os.getenv("APP_NAME", "Courtroom Trading System"),
            environment=os.getenv("APP_ENV", "development"),
            host=os.getenv("HOST", "0.0.0.0"),
            port=int(os.getenv("PORT", "8000")),
            openai_api_key=openai_api_key,
            openai_model=os.getenv("OPENAI_MODEL", "gpt-5.4-mini"),
            openai_reasoning_effort=os.getenv("OPENAI_REASONING_EFFORT", "medium"),
            openai_timeout_seconds=float(os.getenv("OPENAI_TIMEOUT_SECONDS", "60")),
            openai_store=os.getenv("OPENAI_STORE", "false").lower() == "true",
            use_openai=use_openai,
            groq_api_key=groq_api_key,
            groq_model=os.getenv("GROQ_MODEL", "llama3-70b-8192"),
            groq_temperature=float(os.getenv("GROQ_TEMPERATURE", "0.3")),
            use_groq=use_groq,
            llm_provider=llm_provider,
            public_base_url=os.getenv("PUBLIC_BASE_URL", ""),
            frontend_origin=frontend_origin,
            allowed_origins=allowed_origins or [frontend_origin],
            mongodb_uri=mongodb_uri,
            mongodb_database=os.getenv("MONGODB_DATABASE", "courtroom_trading"),
            use_mongodb=os.getenv("USE_MONGODB", "true").lower() == "true" and bool(mongodb_uri),
            google_client_id=os.getenv("GOOGLE_CLIENT_ID", ""),
            google_client_secret=os.getenv("GOOGLE_CLIENT_SECRET", ""),
            jwt_secret=os.getenv("JWT_SECRET", "dev-courtroom-secret"),
            jwt_expiration_minutes=int(os.getenv("JWT_EXPIRATION_MINUTES", "720")),
            auth_skip_google_verification=os.getenv("AUTH_SKIP_GOOGLE_VERIFICATION", "false").lower()
            == "true",
            auth_mode=os.getenv("AUTH_MODE", "demo"),
            demo_user_email=os.getenv("DEMO_USER_EMAIL", "demo.trader@example.com"),
            demo_user_name=os.getenv("DEMO_USER_NAME", "Demo Trader"),
        )


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            if line.startswith("gsk_"):
                os.environ.setdefault("GROQ_API_KEY", line)
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
