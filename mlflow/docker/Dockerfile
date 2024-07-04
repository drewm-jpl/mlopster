FROM ghcr.io/mlflow/mlflow:v2.14.1
RUN apt-get -y update && \
    apt-get -y install python3-dev build-essential pkg-config && \
    pip install --upgrade pip
COPY requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt
CMD ["bash"]
