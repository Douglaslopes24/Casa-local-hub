from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Casa Local Core"
    version: str = "0.5.0"
    host: str = "127.0.0.1"
    port: int = 8799
    data_dir: Path = Path("./data")

    model_config = SettingsConfigDict(env_prefix="CASA_LOCAL_", env_file=".env")

    @property
    def database_path(self) -> Path:
        return self.data_dir / "casa_local.db"

    @property
    def master_key_path(self) -> Path:
        return self.data_dir / "master.key"

    @property
    def mobile_private_key_path(self) -> Path:
        return self.data_dir / "mobile_rsa_private.pem"

    @property
    def mobile_public_key_path(self) -> Path:
        return self.data_dir / "mobile_rsa_public.pem"


settings = Settings()
