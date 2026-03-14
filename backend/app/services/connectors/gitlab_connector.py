"""GitLab CI connector.

Pulls CI/CD pipeline costs from GitLab API.
Credentials: token (Personal/Project Access Token with read_api scope)
             + instance_url (defaults to gitlab.com).
"""

from datetime import datetime, timedelta

import httpx

from app.models.platform import UnifiedCost, CostCategory
from app.services.connectors.base import BaseConnector

# GitLab CI/CD pricing per minute (SaaS)
RUNNER_PRICING = {
    "linux": 0.008,       # shared runners
    "windows": 0.016,
    "macos": 0.08,
    "saas-linux-small-amd64": 0.008,
    "saas-linux-medium-amd64": 0.016,
    "saas-linux-large-amd64": 0.032,
}


class GitLabConnector(BaseConnector):
    platform = "gitlab"

    def __init__(self, credentials: dict):
        super().__init__(credentials)
        self.token = credentials["token"]
        self.instance_url = credentials.get("instance_url", "https://gitlab.com").rstrip("/")
        self.group_id = credentials.get("group_id")
        self.project_ids = credentials.get("project_ids", [])

    def _headers(self) -> dict:
        return {"PRIVATE-TOKEN": self.token}

    def test_connection(self) -> dict:
        try:
            resp = httpx.get(
                f"{self.instance_url}/api/v4/user",
                headers=self._headers(),
                timeout=10,
            )
            if resp.status_code == 200:
                return {"success": True, "message": "GitLab connection successful"}
            return {"success": False, "message": f"HTTP {resp.status_code}: {resp.text[:200]}"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def fetch_costs(self, days: int = 30) -> list[UnifiedCost]:
        """Fetch GitLab CI pipeline usage."""
        costs = []

        projects = self._get_projects()
        end = datetime.utcnow()
        start = end - timedelta(days=days)

        for project in projects:
            project_id = project.get("id")
            project_name = project.get("path_with_namespace", str(project_id))

            try:
                pipelines = self._get_pipelines(project_id, start)
            except Exception:
                continue

            # Aggregate by day
            daily = {}
            for pipeline in pipelines:
                created = pipeline.get("created_at", "")
                date = created[:10]
                duration = pipeline.get("duration", 0) or 0  # seconds

                if date not in daily:
                    daily[date] = {"minutes": 0, "pipelines": 0}
                daily[date]["minutes"] += duration / 60
                daily[date]["pipelines"] += 1

            for date, stats in daily.items():
                minutes = stats["minutes"]
                cost = round(minutes * RUNNER_PRICING["linux"], 4)

                if cost == 0 and minutes == 0:
                    continue

                costs.append(UnifiedCost(
                    date=date,
                    platform="gitlab",
                    service="gitlab_ci",
                    resource=project_name,
                    category=CostCategory.ci_cd,
                    cost_usd=cost,
                    usage_quantity=round(minutes, 2),
                    usage_unit="minutes",
                    metadata={
                        "project": project_name,
                        "pipelines": stats["pipelines"],
                    },
                ))

        return costs

    def _get_projects(self) -> list[dict]:
        """Get projects to track."""
        if self.project_ids:
            projects = []
            for pid in self.project_ids:
                resp = httpx.get(
                    f"{self.instance_url}/api/v4/projects/{pid}",
                    headers=self._headers(),
                    timeout=10,
                )
                if resp.status_code == 200:
                    projects.append(resp.json())
            return projects

        if self.group_id:
            resp = httpx.get(
                f"{self.instance_url}/api/v4/groups/{self.group_id}/projects",
                headers=self._headers(),
                params={"per_page": 100, "order_by": "last_activity_at"},
                timeout=15,
            )
            if resp.status_code == 200:
                return resp.json()

        # User's projects
        resp = httpx.get(
            f"{self.instance_url}/api/v4/projects",
            headers=self._headers(),
            params={"membership": True, "per_page": 50, "order_by": "last_activity_at"},
            timeout=15,
        )
        if resp.status_code == 200:
            return resp.json()
        return []

    def _get_pipelines(self, project_id: int, since: datetime) -> list[dict]:
        """Get completed pipelines for a project."""
        resp = httpx.get(
            f"{self.instance_url}/api/v4/projects/{project_id}/pipelines",
            headers=self._headers(),
            params={
                "status": "success",
                "updated_after": since.strftime("%Y-%m-%dT00:00:00Z"),
                "per_page": 100,
                "order_by": "updated_at",
            },
            timeout=15,
        )
        if resp.status_code != 200:
            return []
        return resp.json()
