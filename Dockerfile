FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /code
COPY utils/requirements.txt /code/
RUN apt update && apt install -y gcc libpq-dev
RUN pip install -r requirements.txt
COPY . /code/
RUN chmod +x /code/entrypoint
