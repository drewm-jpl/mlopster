from datetime import datetime

from airflow.operators.bash_operator import BashOperator

from airflow import DAG

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "start_date": datetime(2021, 1, 1),
}

dag = DAG("hello_world", default_args=default_args, schedule_interval=None)

t1 = BashOperator(
    task_id="say_hello",
    bash_command='echo "Hello World from Airflow!"',
    dag=dag,
)
