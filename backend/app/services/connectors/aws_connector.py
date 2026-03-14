"""AWS Cost Explorer connector.

Pulls costs for data-platform services: S3, Redshift, MWAA (Airflow),
Glue, SQS, MSK (Kafka), Athena, EMR, Lambda, SageMaker, Bedrock, DMS,
QuickSight, Step Functions, CloudWatch, ECS, EKS, Kinesis, DynamoDB.
"""

from datetime import datetime, timedelta

import boto3

from app.models.platform import UnifiedCost, CostCategory
from app.services.connectors.base import BaseConnector

# Map AWS service names to our cost categories
SERVICE_CATEGORY_MAP = {
    # Storage
    "Amazon Simple Storage Service": CostCategory.storage,
    "Amazon DynamoDB": CostCategory.storage,
    # Compute / Warehouses
    "Amazon Redshift": CostCategory.compute,
    "Amazon Athena": CostCategory.compute,
    "Amazon EMR": CostCategory.compute,
    "AWS Lambda": CostCategory.compute,
    "Amazon Elastic Container Service": CostCategory.compute,
    "Amazon Elastic Kubernetes Service": CostCategory.compute,
    # Orchestration
    "Amazon Managed Workflows for Apache Airflow": CostCategory.orchestration,
    "AWS Step Functions": CostCategory.orchestration,
    "Amazon CloudWatch": CostCategory.orchestration,
    # Transformation
    "AWS Glue": CostCategory.transformation,
    # Ingestion
    "Amazon Kinesis": CostCategory.ingestion,
    "AWS Database Migration Service": CostCategory.ingestion,
    # Networking / Messaging
    "Amazon Simple Queue Service": CostCategory.networking,
    "Amazon Managed Streaming for Apache Kafka": CostCategory.networking,
    # AI / ML
    "Amazon Bedrock": CostCategory.ai_inference,
    "Amazon SageMaker": CostCategory.ml_training,
    # BI
    "Amazon QuickSight": CostCategory.serving,
}

# Only pull data-platform services, not all of AWS
DATA_PLATFORM_SERVICES = list(SERVICE_CATEGORY_MAP.keys())


class AWSConnector(BaseConnector):
    platform = "aws"

    def __init__(self, credentials: dict):
        super().__init__(credentials)
        self.client = boto3.client(
            "ce",
            aws_access_key_id=credentials["aws_access_key_id"],
            aws_secret_access_key=credentials["aws_secret_access_key"],
            region_name=credentials.get("region", "us-east-1"),
        )

    def test_connection(self) -> dict:
        try:
            end = datetime.utcnow().strftime("%Y-%m-%d")
            start = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
            self.client.get_cost_and_usage(
                TimePeriod={"Start": start, "End": end},
                Granularity="DAILY",
                Metrics=["UnblendedCost"],
                Filter={"Dimensions": {"Key": "SERVICE", "Values": DATA_PLATFORM_SERVICES[:1]}},
            )
            return {"success": True, "message": "AWS Cost Explorer connection successful"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def fetch_costs(self, days: int = 30) -> list[UnifiedCost]:
        end = datetime.utcnow().strftime("%Y-%m-%d")
        start = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")

        response = self.client.get_cost_and_usage(
            TimePeriod={"Start": start, "End": end},
            Granularity="DAILY",
            Metrics=["UnblendedCost", "UsageQuantity"],
            GroupBy=[
                {"Type": "DIMENSION", "Key": "SERVICE"},
            ],
            Filter={
                "Dimensions": {
                    "Key": "SERVICE",
                    "Values": DATA_PLATFORM_SERVICES,
                }
            },
        )

        costs = []
        for result in response.get("ResultsByTime", []):
            date = result["TimePeriod"]["Start"]
            for group in result.get("Groups", []):
                service_name = group["Keys"][0]
                amount = float(group["Metrics"]["UnblendedCost"]["Amount"])
                usage = float(group["Metrics"]["UsageQuantity"]["Amount"])
                usage_unit = group["Metrics"]["UsageQuantity"].get("Unit", "")

                if amount == 0:
                    continue

                # Normalize service name
                service_key = service_name.lower().replace(" ", "_")
                for prefix in ["amazon_", "aws_"]:
                    if service_key.startswith(prefix):
                        service_key = service_key[len(prefix):]

                costs.append(UnifiedCost(
                    date=date,
                    platform="aws",
                    service=f"aws_{service_key}",
                    resource=service_name,
                    category=SERVICE_CATEGORY_MAP.get(service_name, CostCategory.compute),
                    cost_usd=round(amount, 4),
                    usage_quantity=round(usage, 4),
                    usage_unit=usage_unit,
                ))

        return costs
