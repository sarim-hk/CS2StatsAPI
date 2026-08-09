import json
from functools import lru_cache
from pathlib import Path
from pydantic import BaseModel, Field

class Settings(BaseModel):
    mysql_server: str = Field(alias="MySQLServer")
    mysql_database: str = Field(alias="MySQLDatabase")
    mysql_username: str = Field(alias="MySQLUsername")
    mysql_password: str = Field(alias="MySQLPassword")
    api_auth_key: str = Field(alias="APIAuthKey")
    steam_api_auth_key: str = Field(alias="SteamAPIAuthKey")

def _config_path():
    return Path(__file__).resolve().parent.parent / "instance" / "config.json"

@lru_cache
def get_settings():
    with _config_path().open(encoding="utf-8") as config_file:
        raw_config = json.load(config_file)

    return Settings.model_validate(raw_config)
