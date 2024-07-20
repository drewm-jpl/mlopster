import os
from datetime import datetime, timedelta

import tensorflow as tf
import tensorflow_hub as hub
from airflow.operators.python import PythonOperator
from airflow.providers.amazon.aws.hooks.s3 import S3Hook
from airflow.providers.amazon.aws.operators.sagemaker import (
    SageMakerEndpointConfigOperator,
    SageMakerEndpointOperator,
    SageMakerModelOperator,
)
from airflow.providers.amazon.aws.sensors.sagemaker import SageMakerEndpointSensor

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
    "sagemaker_mnist_model_endpoint",
    default_args=default_args,
    description="Deploy a prebuilt MNIST model to SageMaker",
    schedule_interval=None,  # Manually triggerable
    start_date=datetime(2021, 1, 1),
    tags=["sagemaker", "mnist"],
)

s3_bucket = "srl-dev-idps-drewm-airflow-logs-1"
s3_prefix = "prebuilt/mnist-model/"
model_save_path = "mnist_model/1"


# Task to download and save the prebuilt MNIST model
def download_and_save_model():
    model_url = "https://tfhub.dev/google/tf2-preview/mobilenet_v2/feature_vector/4"
    model = tf.keras.Sequential([hub.KerasLayer(model_url, input_shape=(224, 224, 3))])
    model.save(model_save_path, save_format="tf")


download_model_task = PythonOperator(
    task_id="download_prebuilt_mnist_model",
    python_callable=download_and_save_model,
    dag=dag,
)


# Task to upload the model to S3
def upload_directory_to_s3():
    s3_hook = S3Hook()
    for root, _, files in os.walk(model_save_path):
        for file in files:
            local_path = os.path.join(root, file)
            relative_path = os.path.relpath(local_path, model_save_path)
            s3_path = os.path.join(s3_prefix, relative_path)

            s3_hook.load_file(filename=local_path, key=s3_path, bucket_name=s3_bucket, replace=True)
            print(f"Uploaded {local_path} to s3://{s3_bucket}/{s3_path}")


upload_model_task = PythonOperator(
    task_id="upload_model_to_s3",
    python_callable=upload_directory_to_s3,
    dag=dag,
)

# Define SageMaker model
model_name = "prebuilt-mnist-model"
model_data_url = f"s3://{s3_bucket}/{s3_prefix}"

sagemaker_model = {
    "ModelName": model_name,
    "PrimaryContainer": {
        "Image": "382416733822.dkr.ecr.us-east-1.amazonaws.com/sagemaker-tensorflow:2.3.0-cpu-py37-ubuntu18.04",
        "ModelDataUrl": model_data_url,
    },
    "ExecutionRoleArn": "arn:aws:iam::your-account-id:role/service-role/AmazonSageMaker-ExecutionRole-20200101T000001",
}

create_model_task = SageMakerModelOperator(
    task_id="create_sagemaker_model",
    config=sagemaker_model,
    aws_conn_id="aws_default",
    wait_for_completion=True,
    dag=dag,
)

# Define SageMaker endpoint configuration
endpoint_config_name = "mnist-endpoint-config"
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
    wait_for_completion=True,
    dag=dag,
)

# Create SageMaker endpoint
endpoint_name = "mnist-endpoint"
sagemaker_endpoint = {
    "EndpointName": endpoint_name,
    "EndpointConfigName": endpoint_config_name,
}

create_endpoint_task = SageMakerEndpointOperator(
    task_id="create_sagemaker_endpoint",
    config=sagemaker_endpoint,
    aws_conn_id="aws_default",
    wait_for_completion=False,  # We'll use a sensor to wait
    dag=dag,
)

# Wait for endpoint to be in service
wait_for_endpoint_task = SageMakerEndpointSensor(
    task_id="wait_for_endpoint",
    endpoint_name=endpoint_name,
    aws_conn_id="aws_default",
    dag=dag,
)

# Task dependencies
(
    download_model_task
    >> upload_model_task
    >> create_model_task
    >> create_endpoint_config_task
    >> create_endpoint_task
    >> wait_for_endpoint_task
)
