"""Runtime settings, read from environment variables.

Nothing here needs the internet. The JWT signing secret is either supplied via
JWT_SECRET or generated once and stored next to the SQLite database, so no
secret is ever committed to the repository.
"""
import os
import secrets
from pathlib import Path


def _bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class Settings:
    def __init__(self) -> None:
        self.data_dir = Path(os.getenv("DATA_DIR", "./data")).resolve()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.database_url = os.getenv(
            "DATABASE_URL", f"sqlite:///{self.data_dir / 'dogfood.db'}"
        )
        self.static_dir = Path(os.getenv("STATIC_DIR", "./static")).resolve()
        self.seed_demo_data = _bool("SEED_DEMO_DATA", True)
        self.token_ttl_minutes = int(os.getenv("TOKEN_TTL_MINUTES", "480"))
        # 12 is a sensible production cost; tests lower it to stay fast.
        self.bcrypt_rounds = int(os.getenv("BCRYPT_ROUNDS", "12"))
        self.jwt_secret = os.getenv("JWT_SECRET") or self._load_or_create_secret()

    def _load_or_create_secret(self) -> str:
        secret_file = self.data_dir / ".jwt_secret"
        if secret_file.exists():
            return secret_file.read_text().strip()
        secret = secrets.token_urlsafe(48)
        secret_file.write_text(secret)
        try:
            secret_file.chmod(0o600)
        except OSError:
            pass
        return secret


settings = Settings()
