FROM python:3.12

RUN pip install --upgrade pip

RUN apt update && apt install -y gcc  
RUN pip install scapy nats-py scikit-learn scipy

WORKDIR /code/tcp-options-processor