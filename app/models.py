from typing import Optional
from sqlmodel import Field, SQLModel
from datetime import datetime

class ProxyNode(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    url: str  # Upstream URL, e.g., "https://registry-1.docker.io"
    registry_type: str = Field(default="dockerhub") # dockerhub, ghcr, gcr, quay, k8s, other
    route_prefix: Optional[str] = Field(default=None, index=True) # e.g., "ghcr", "gcr", "k8s"
    enabled: bool = True
    latency: float = Field(default=9999.0) # In ms
    last_check: Optional[datetime] = None
    is_default: bool = False
    username: Optional[str] = Field(default=None)
    password: Optional[str] = Field(default=None)
    failure_reason: Optional[str] = Field(default=None)

class TrafficStats(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    date: str = Field(index=True) # YYYY-MM-DD
    download_bytes: int = Field(default=0)
    upload_bytes: int = Field(default=0)
    request_count: int = Field(default=0)

class PullHistory(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    request_time: datetime = Field(default_factory=datetime.utcnow)
    image: str
    tag: str
    client_ip: str
