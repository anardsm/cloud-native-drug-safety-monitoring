FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && \
    apt-get install -y netcat-openbsd && \
    apt-get clean

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./app ./app
COPY wait-for-db.sh .
COPY main.py .
COPY openapi ./openapi
CMD ["./wait-for-db.sh"]
