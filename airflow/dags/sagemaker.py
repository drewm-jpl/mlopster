import logging

import boto3
import sagemaker
from airflow.operators.python import PythonOperator

# from airflow.providers.amazon.aws.operators.sagemaker import SageMakerModelOperator
from airflow.providers.amazon.aws.sensors.sagemaker import SageMakerEndpointSensor
from airflow.utils.dates import days_ago
from sagemaker.huggingface import HuggingFaceModel

from airflow import DAG

logger = logging.getLogger(__name__)


default_args = {"owner": "airflow"}

dag = DAG(
    "huggingface_sagemaker_model_endpoint",
    default_args=default_args,
    description="Deploy a Hugging Face model to SageMaker",
    schedule_interval=None,  # Manually triggerable
    start_date=days_ago(1),
    tags=["sagemaker", "huggingface"],
)


# Function to get the execution role
def get_execution_role():
    try:
        role = sagemaker.get_execution_role()
    except ValueError:
        iam = boto3.client(
            "iam",
            endpoint_url="http://localhost.localstack.cloud:4566",
            region_name="us-east-1",
            aws_access_key_id="mock_access_key",
            aws_secret_access_key="mock_secret_key",
        )
        role = iam.get_role(RoleName="sagemaker_execution_role")["Role"]["Arn"]
    return role


# Function to deploy the Hugging Face model
def deploy_huggingface_model():
    logger.info("a")
    role = get_execution_role()
    logger.info("b")
    # Hub Model configuration. https://huggingface.co/models
    hub = {"HF_MODEL_ID": "drewmee/sklearn-model", "HF_TASK": "undefined"}
    logger.info("c")
    sagemaker_session = sagemaker.Session(
        default_bucket="srl-dev-idps-drewm-sagemaker-1",
        boto_session=boto3.Session(
            region_name="us-east-1",
            aws_access_key_id="mock_access_key",
            aws_secret_access_key="mock_secret_key",
        ),
        sagemaker_client=boto3.client(
            "sagemaker",
            endpoint_url="http://localhost.localstack.cloud:4566",
            region_name="us-east-1",
            aws_access_key_id="mock_access_key",
            aws_secret_access_key="mock_secret_key",
        ),
        sagemaker_featurestore_runtime_client=boto3.client(
            "sagemaker-featurestore-runtime",
            endpoint_url="http://localhost.localstack.cloud:4566",
            region_name="us-east-1",
            aws_access_key_id="mock_access_key",
            aws_secret_access_key="mock_secret_key",
        ),
        sagemaker_metrics_client=boto3.client(
            "sagemaker-metrics",
            endpoint_url="http://localhost.localstack.cloud:4566",
            region_name="us-east-1",
            aws_access_key_id="mock_access_key",
            aws_secret_access_key="mock_secret_key",
        ),
    )
    logger.info("d")
    # Create Hugging Face Model Class
    huggingface_model = HuggingFaceModel(
        transformers_version="4.37.0",
        pytorch_version="2.1.0",
        py_version="py310",
        env=hub,
        sagemaker_session=sagemaker_session,
        role=role,
    )
    logger.info("e")
    # Deploy model to SageMaker Inference
    predictor = huggingface_model.deploy(
        initial_instance_count=1, instance_type="ml.m5.xlarge"  # number of instances  # ec2 instance type
    )
    logger.info("f")
    return predictor.endpoint_name


# Task to deploy the Hugging Face model
deploy_model_task = PythonOperator(
    task_id="deploy_huggingface_model",
    python_callable=deploy_huggingface_model,
    dag=dag,
)

# Wait for endpoint to be in service
wait_for_endpoint_task = SageMakerEndpointSensor(
    task_id="wait_for_endpoint",
    endpoint_name="{{ task_instance.xcom_pull(task_ids='deploy_huggingface_model') }}",
    dag=dag,
)

# Task dependencies
deploy_model_task >> wait_for_endpoint_task
