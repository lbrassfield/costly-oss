"""GitHub Actions connector.

Pulls CI/CD workflow run costs from GitHub Actions API.
Credentials: token (Personal Access Token with repo + actions scope).
"""

from datetime import datetime, timedelta

import httpx

from app.models.platform import UnifiedCost, CostCategory
from app.services.connectors.base import BaseConnector

# GitHub Actions pricing per minute (as of 2026)
RUNNER_PRICING = {
    "ubuntu": 0.008,     # $0.008/min for Linux
    "windows": 0.016,    # $0.016/min for Windows
    "macos": 0.08,       # $0.08/min for macOS
}


class GitHubConnector(BaseConnector):
    platform = "github"

    def __init__(self, credentials: dict):
        super().__init__(credentials)
        self.token = credentials["token"]
        self.org = credentials.get("org", "")
        self.repos = credentials.get("repos", [])  # Optional: specific repos
        self.base_url = "https://api.github.com"

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def test_connection(self) -> dict:
        try:
            resp = httpx.get(
                f"{self.base_url}/user",
                headers=self._headers(),
                timeout=10,
            )
            if resp.status_code == 200:
                return {"success": True, "message": "GitHub connection successful"}
            return {"success": False, "message": f"HTTP {resp.status_code}: {resp.text[:200]}"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def fetch_costs(self, days: int = 30) -> list[UnifiedCost]:
        """Fetch GitHub Actions usage.

        For org accounts: uses billing API.
        For personal/repos: aggregates workflow run durations.
        """
        costs = []

        # Try org billing API first
        if self.org:
            try:
                costs = self._fetch_org_billing(days)
                if costs:
                    return costs
            except Exception:
                pass

        # Fallback: aggregate from workflow runs
        try:
            repos = self._get_repos()
            for repo in repos:
                repo_costs = self._fetch_repo_actions(repo, days)
                costs.extend(repo_costs)
        except Exception:
            pass

        return costs

    def _fetch_org_billing(self, days: int) -> list[UnifiedCost]:
        """Fetch from GitHub org billing API."""
        resp = httpx.get(
            f"{self.base_url}/orgs/{self.org}/settings/billing/actions",
            headers=self._headers(),
            timeout=15,
        )
        if resp.status_code != 200:
            return []

        data = resp.json()
        total_minutes = data.get("total_minutes_used", 0)
        included_minutes = data.get("included_minutes", 0)
        paid_minutes = max(0, total_minutes - included_minutes)

        # Break down by OS
        breakdown = data.get("minutes_used_breakdown", {})
        costs = []
        today = datetime.utcnow().strftime("%Y-%m-%d")

        for os_type, minutes in breakdown.items():
            if minutes == 0:
                continue
            rate = RUNNER_PRICING.get(os_type.lower().split("_")[0], 0.008)
            cost = round(minutes * rate, 4)

            costs.append(UnifiedCost(
                date=today,
                platform="github",
                service=f"github_actions_{os_type.lower()}",
                resource=self.org,
                category=CostCategory.ci_cd,
                cost_usd=cost,
                usage_quantity=minutes,
                usage_unit="minutes",
                metadata={
                    "os": os_type,
                    "total_minutes": total_minutes,
                    "included_minutes": included_minutes,
                    "paid_minutes": paid_minutes,
                },
            ))

        return costs

    def _fetch_repo_actions(self, repo: str, days: int) -> list[UnifiedCost]:
        """Fetch workflow runs for a single repo and calculate costs."""
        end = datetime.utcnow()
        start = end - timedelta(days=days)

        resp = httpx.get(
            f"{self.base_url}/repos/{repo}/actions/runs",
            headers=self._headers(),
            params={
                "created": f">={start.strftime('%Y-%m-%d')}",
                "status": "completed",
                "per_page": 100,
            },
            timeout=15,
        )

        if resp.status_code != 200:
            return []

        data = resp.json()
        runs = data.get("workflow_runs", [])

        # Aggregate by day + workflow
        daily = {}
        for run in runs:
            created = run.get("created_at", "")
            date = created[:10]
            workflow_name = run.get("name", "unknown")
            run_id = run.get("id")

            # Get timing for this run
            timing = self._get_run_timing(repo, run_id)
            duration_ms = timing.get("run_duration_ms", 0)
            duration_min = duration_ms / 60000

            key = f"{date}|{workflow_name}"
            if key not in daily:
                daily[key] = {"date": date, "workflow": workflow_name, "minutes": 0, "runs": 0}
            daily[key]["minutes"] += duration_min
            daily[key]["runs"] += 1

        costs = []
        for entry in daily.values():
            minutes = entry["minutes"]
            cost = round(minutes * RUNNER_PRICING["ubuntu"], 4)  # default to Linux pricing

            if cost == 0 and minutes == 0:
                continue

            costs.append(UnifiedCost(
                date=entry["date"],
                platform="github",
                service="github_actions",
                resource=f"{repo}/{entry['workflow']}",
                category=CostCategory.ci_cd,
                cost_usd=cost,
                usage_quantity=round(minutes, 2),
                usage_unit="minutes",
                metadata={
                    "repo": repo,
                    "workflow": entry["workflow"],
                    "runs": entry["runs"],
                },
            ))

        return costs

    def _get_repos(self) -> list[str]:
        """Get repos to track — either specified or all org repos."""
        if self.repos:
            return self.repos

        if self.org:
            resp = httpx.get(
                f"{self.base_url}/orgs/{self.org}/repos",
                headers=self._headers(),
                params={"per_page": 100, "sort": "pushed"},
                timeout=15,
            )
            if resp.status_code == 200:
                return [r["full_name"] for r in resp.json()]

        # Personal repos
        resp = httpx.get(
            f"{self.base_url}/user/repos",
            headers=self._headers(),
            params={"per_page": 50, "sort": "pushed"},
            timeout=15,
        )
        if resp.status_code == 200:
            return [r["full_name"] for r in resp.json()]

        return []

    def _get_run_timing(self, repo: str, run_id: int) -> dict:
        """Get timing for a workflow run."""
        resp = httpx.get(
            f"{self.base_url}/repos/{repo}/actions/runs/{run_id}/timing",
            headers=self._headers(),
            timeout=10,
        )
        if resp.status_code != 200:
            return {}
        return resp.json()
