from datetime import timedelta

from airflow.providers.amazon.aws.operators.sagemaker import (
    SageMakerEndpointConfigOperator,
    SageMakerEndpointOperator,
    SageMakerModelOperator,
)
from airflow.providers.amazon.aws.sensors.sagemaker import SageMakerEndpointSensor
from airflow.utils.dates import days_ago

from airflow import DAG

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

dag = DAG(
    "sagemaker_sklearn_model_endpoint",
    default_args=default_args,
    description="Deploy an sklearn model to SageMaker",
    schedule_interval=None,  # Manually triggerable
    start_date=days_ago(1),
    tags=["sagemaker", "sklearn"],
)

# Define the region
region_name = "us-east-1"

# Define SageMaker model
model_name = "sklearn-model"
s3_model_path = (
    "s3://srl-dev-idps-drewm-mlflow-artifacts-1/1/55dc066efd4447b28baca4d60494b625/artifacts/sklearn-model/"
)
image_uri = "683313688378.dkr.ecr.us-east-1.amazonaws.com/sagemaker-scikit-learn:0.23-1-cpu-py3"

sagemaker_model = {
    "ModelName": model_name,
    "PrimaryContainer": {
        "Image": image_uri,
        "ModelDataUrl": s3_model_path,
    },
    "ExecutionRoleArn": "arn:aws:iam::your-account-id:role/service-role/AmazonSageMaker-ExecutionRole-20200101T000001",
}

create_model_task = SageMakerModelOperator(
    task_id="create_sagemaker_model",
    config=sagemaker_model,
    aws_conn_id="aws_default",
    dag=dag,
)

# Define SageMaker endpoint configuration
endpoint_config_name = "sklearn-endpoint-config"
sagemaker_endpoint_config = {
    "EndpointConfigName": endpoint_config_name,
    "ProductionVariants": [
        {
            "VariantName": "AllTraffic",
            "ModelName": model_name,
            "InitialInstanceCount": 1,
            "InstanceType": "ml.m4.xlarge",
            "InitialVariantWeight": 1,
        }
    ],
}

create_endpoint_config_task = SageMakerEndpointConfigOperator(
    task_id="create_sagemaker_endpoint_config",
    config=sagemaker_endpoint_config,
    aws_conn_id="aws_default",
    dag=dag,
)

# Create SageMaker endpoint
endpoint_name = "sklearn-endpoint"
sagemaker_endpoint = {
    "EndpointName": endpoint_name,
    "EndpointConfigName": endpoint_config_name,
}

create_endpoint_task = SageMakerEndpointOperator(
    task_id="create_sagemaker_endpoint",
    config=sagemaker_endpoint,
    aws_conn_id="aws_default",
    region_name=region_name,  # Explicitly set the region
    wait_for_completion=False,  # We'll use a sensor to wait
    dag=dag,
)

# Wait for endpoint to be in service
wait_for_endpoint_task = SageMakerEndpointSensor(
    task_id="wait_for_endpoint",
    endpoint_name=endpoint_name,
    aws_conn_id="aws_default",
    region_name=region_name,  # Explicitly set the region
    dag=dag,
)

# Task dependencies
create_model_task >> create_endpoint_config_task >> create_endpoint_task >> wait_for_endpoint_task
