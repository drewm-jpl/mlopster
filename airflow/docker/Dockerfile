FROM apache/airflow:2.9.3-python3.11
RUN apt update && apt install git -y
COPY requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt
