from datetime import timedelta

import boto3
import sagemaker
from airflow.operators.python import PythonOperator

# from airflow.providers.amazon.aws.operators.sagemaker import SageMakerModelOperator
from airflow.providers.amazon.aws.sensors.sagemaker import SageMakerEndpointSensor
from airflow.utils.dates import days_ago
from sagemaker.huggingface import HuggingFaceModel

from airflow import DAG

AWS_CONN_ID = "aws"  # test

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

dag = DAG(
    "huggingface_sagemaker_model_endpoint",
    default_args=default_args,
    description="Deploy a Hugging Face model to SageMaker",
    schedule_interval=None,  # Manually triggerable
    start_date=days_ago(1),
    tags=["sagemaker", "huggingface"],
)


# Function to get the execution role
# def get_execution_role():
#     try:
#         role = sagemaker.get_execution_role()
#     except ValueError:
#         iam = boto3.client(
#             "iam",
#             endpoint_url="http://localhost.localstack.cloud:4566",
#             region_name="us-east-1",
#             aws_access_key_id="mock_access_key",
#             aws_secret_access_key="mock_secret_key",
#         )
#         role = iam.get_role(RoleName="sagemaker_execution_role")["Role"]["Arn"]
#     return role


# Function to deploy the Hugging Face model
def deploy_huggingface_model():
    # role = get_execution_role()

    # Hub Model configuration. https://huggingface.co/models
    hub = {"HF_MODEL_ID": "drewmee/sklearn-model", "HF_TASK": "undefined"}

    sagemaker_session = sagemaker.Session(
        boto3.Session(
            endpoint_url="http://localhost.localstack.cloud:4566",
            region_name="us-east-1",
            aws_access_key_id="mock_access_key",
            aws_secret_access_key="mock_secret_key",
        )
    )

    # Create Hugging Face Model Class
    huggingface_model = HuggingFaceModel(
        transformers_version="4.37.0",
        pytorch_version="2.1.0",
        py_version="py310",
        env=hub,
        sagemaker_session=sagemaker_session,
        # role=role,
    )

    # Deploy model to SageMaker Inference
    predictor = huggingface_model.deploy(
        initial_instance_count=1, instance_type="ml.m5.xlarge"  # number of instances  # ec2 instance type
    )

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
    aws_conn_id=AWS_CONN_ID,
    dag=dag,
)

# Task dependencies
deploy_model_task >> wait_for_endpoint_task
