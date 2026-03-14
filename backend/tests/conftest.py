"""Shared test fixtures for Costly backend tests."""

import pytest
from datetime import datetime, timedelta


@pytest.fixture
def sample_dates():
    """Generate a list of date strings for the last 7 days."""
    today = datetime.utcnow().date()
    return [(today - timedelta(days=i)).isoformat() for i in range(6, -1, -1)]


@pytest.fixture
def aws_credentials():
    return {
        "aws_access_key_id": "AKIAIOSFODNN7EXAMPLE",
        "aws_secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        "region": "us-east-1",
    }


@pytest.fixture
def openai_credentials():
    return {"api_key": "sk-test-key-123", "org_id": "org-test-123"}


@pytest.fixture
def anthropic_credentials():
    return {"api_key": "sk-ant-admin-test-key-123"}


@pytest.fixture
def dbt_cloud_credentials():
    return {"api_token": "dbtc_test_token", "account_id": "12345"}


@pytest.fixture
def fivetran_credentials():
    return {"api_key": "fivetran_key", "api_secret": "fivetran_secret"}


@pytest.fixture
def bigquery_credentials():
    return {
        "project_id": "test-project",
        "service_account_json": '{"type":"service_account","client_email":"test@test.iam.gserviceaccount.com","private_key":"fake"}',
    }


@pytest.fixture
def databricks_credentials():
    return {
        "account_id": "test-account",
        "access_token": "dapi_test_token",
        "workspace_url": "https://test.cloud.databricks.com",
    }


@pytest.fixture
def github_credentials():
    return {"token": "ghp_test_token", "org": "test-org"}


@pytest.fixture
def gitlab_credentials():
    return {"token": "glpat-test-token", "instance_url": "https://gitlab.com"}


@pytest.fixture
def airbyte_credentials():
    return {"api_token": "airbyte_test_token"}


@pytest.fixture
def monte_carlo_credentials():
    return {"api_key_id": "mc_key_id", "api_token": "mc_token"}


@pytest.fixture
def looker_credentials():
    return {
        "client_id": "looker_client",
        "client_secret": "looker_secret",
        "instance_url": "https://test.looker.com",
    }


@pytest.fixture
def tableau_credentials():
    return {
        "server_url": "https://test.tableau.com",
        "token_name": "test_token",
        "token_secret": "test_secret",
        "site_id": "test_site",
    }


@pytest.fixture
def omni_credentials():
    return {"api_key": "omni_key", "instance_url": "https://test.omni.co"}


@pytest.fixture
def gemini_credentials():
    return {"api_key": "gemini_test_key"}
