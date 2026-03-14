from pydantic import BaseModel
from typing import Optional


class SnowflakeConnectionCreate(BaseModel):
    connection_name: str
    account: str
    username: str
    auth_type: str
    password: Optional[str] = None
    private_key: Optional[str] = None
    private_key_passphrase: Optional[str] = None
    warehouse: str
    database: str = "SNOWFLAKE"
    schema_name: str = "ACCOUNT_USAGE"
    role: str = "ACCOUNTADMIN"
