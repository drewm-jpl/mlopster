import logging

import boto3

# import botocore.config
import sagemaker
from airflow.operators.python import PythonOperator

# from airflow.providers.amazon.aws.operators.sagemaker import SageMakerModelOperator
from airflow.providers.amazon.aws.sensors.sagemaker import SageMakerEndpointSensor
from airflow.utils.dates import days_ago
from sagemaker.huggingface import HuggingFaceModel

from airflow import DAG

logger = logging.getLogger(__name__)


# class CustomSageMakerSession(sagemaker.Session):
#     def __init__(self, endpoint_url=None, region_name="us-east-1", **kwargs):
#         self.endpoint_url = endpoint_url
#         self.region_name = region_name
#         super().__init__(**kwargs)

#     def _initialize(
#         self,
#         boto_session,
#         sagemaker_client,
#         sagemaker_runtime_client,
#         sagemaker_featurestore_runtime_client,
#         sagemaker_metrics_client,
#         sagemaker_config: dict = None,
#     ):
#         self.boto_session = (
#             boto_session
#             or boto3.DEFAULT_SESSION
#             or boto3.Session(
#                 aws_access_key_id="mock_access_key",
#                 aws_secret_access_key="mock_secret_key",
#                 region_name=self.region_name,
#             )
#         )

#         self._region_name = self.boto_session.region_name
#         if self._region_name is None:
#             raise ValueError("Must setup local AWS configuration with a region supported by SageMaker.")

#         botocore_config = botocore.config.Config(user_agent_extra="CustomSageMakerSession")

#         self.sagemaker_client = sagemaker_client or self.boto_session.client(
#             "sagemaker", config=botocore_config, endpoint_url=self.endpoint_url
#         )

#         self.sagemaker_runtime_client = sagemaker_runtime_client or self.boto_session.client(
#             "runtime.sagemaker", config=botocore_config, endpoint_url=self.endpoint_url
#         )

#         self.sagemaker_featurestore_runtime_client = (
#             sagemaker_featurestore_runtime_client
#             or self.boto_session.client(
#                 "sagemaker-featurestore-runtime", config=botocore_config, endpoint_url=self.endpoint_url
#             )
#         )

#         self.sagemaker_metrics_client = sagemaker_metrics_client or self.boto_session.client(
#             "sagemaker-metrics", config=botocore_config, endpoint_url=self.endpoint_url
#         )

#         self.s3_client = self.boto_session.client(
#             "s3", region_name=self._region_name, endpoint_url=self.endpoint_url
#         )
#         self.s3_resource = self.boto_session.resource(
#             "s3", region_name=self._region_name, endpoint_url=self.endpoint_url
#         )

#         self.lambda_client = self.boto_session.client(
#             "lambda", region_name=self._region_name, endpoint_url=self.endpoint_url
#         )

#         self.local_mode = False

#         if sagemaker_config:
#             self.sagemaker_config = sagemaker_config
#         else:
#             self.sagemaker_config = {}

#         self._default_bucket_name_override = self.sagemaker_config.get("default_bucket", None)
#         self.default_bucket_prefix = self.sagemaker_config.get("default_bucket_prefix", None)


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
    endpoint_url = "http://localhost.localstack.cloud:4566"

    # sagemaker_session = sagemaker.local.LocalSession(
    #     boto_session=boto3.Session(
    #         region_name="us-east-1",
    #         aws_access_key_id="mock_access_key",
    #         aws_secret_access_key="mock_secret_key",
    #     ),
    #     default_bucket="srl-dev-idps-drewm-sagemaker-1",
    #     s3_endpoint_url=endpoint_url,
    # )
    # sagemaker_session = CustomSageMakerSession(
    #     endpoint_url=endpoint_url,
    #     default_bucket="srl-dev-idps-drewm-sagemaker-1",
    #     boto_session=boto3.Session(
    #         region_name="us-east-1",
    #         aws_access_key_id="mock_access_key",
    #         aws_secret_access_key="mock_secret_key",
    #     ),
    #     sagemaker_client=boto3.client(
    #         "sagemaker",
    #         endpoint_url=endpoint_url,
    #         region_name="us-east-1",
    #         aws_access_key_id="mock_access_key",
    #         aws_secret_access_key="mock_secret_key",
    #     ),
    #     sagemaker_featurestore_runtime_client=boto3.client(
    #         "sagemaker-featurestore-runtime",
    #         endpoint_url=endpoint_url,
    #         region_name="us-east-1",
    #         aws_access_key_id="mock_access_key",
    #         aws_secret_access_key="mock_secret_key",
    #     ),
    #     sagemaker_metrics_client=boto3.client(
    #         "sagemaker-metrics",
    #         endpoint_url=endpoint_url,
    #         region_name="us-east-1",
    #         aws_access_key_id="mock_access_key",
    #         aws_secret_access_key="mock_secret_key",
    #     ),
    # )
    boto_session = boto3.Session(
        region_name="us-east-1",
        aws_access_key_id="mock_access_key",
        aws_secret_access_key="mock_secret_key",
    )
    sagemaker_session = sagemaker.Session(
        default_bucket="srl-dev-idps-drewm-sagemaker-1",
        boto_session=boto_session,
        sagemaker_client=boto_session.client("sagemaker", endpoint_url=endpoint_url),
        sagemaker_featurestore_runtime_client=boto_session.client(
            "sagemaker-featurestore-runtime", endpoint_url=endpoint_url
        ),
        sagemaker_metrics_client=boto_session.client("sagemaker-metrics", endpoint_url=endpoint_url),
        s3_client=boto_session.client("s3", endpoint_url=endpoint_url),
        s3_resource=boto_session.resource("s3", endpoint_url=endpoint_url),
        resource_groups_client=boto_session.client("resource-groups", endpoint_url=endpoint_url),
        resource_group_tagging_client=boto_session.client(
            "resourcegroupstaggingapi", endpoint_url=endpoint_url
        ),
        iam_client=boto_session.client("iam", endpoint_url=endpoint_url),
        sts_client=boto_session.client("sts", endpoint_url=endpoint_url),
        cloudwatch_client=boto_session.client("logs", endpoint_url=endpoint_url),
        athena_client=boto_session.client("athena", endpoint_url=endpoint_url),
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
