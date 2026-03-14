from abc import ABC, abstractmethod
from app.models.platform import UnifiedCost


class BaseConnector(ABC):
    """Base class for all platform connectors."""

    platform: str  # e.g. "aws", "anthropic", "dbt_cloud"

    def __init__(self, credentials: dict):
        self.credentials = credentials

    @abstractmethod
    def fetch_costs(self, days: int = 30) -> list[UnifiedCost]:
        """Fetch cost records for the given period. Returns normalized UnifiedCost records."""
        ...

    @abstractmethod
    def test_connection(self) -> dict:
        """Test that the credentials are valid. Returns {"success": bool, "message": str}."""
        ...
