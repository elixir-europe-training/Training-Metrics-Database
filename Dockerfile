FROM python:3.11-alpine3.18

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /code
COPY utils/requirements.txt /code/
RUN pip install -r requirements.txt
COPY . /code/
