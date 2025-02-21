ARG TMDDIR="/opt/tmd/app"
ARG TMDSTATICDIR="/opt/tmd/static"
ARG UID=1000
ARG GID=1000


# Base setup
FROM python:3.11-slim AS base

ARG TMDDIR
ARG TMDSTATICDIR
ARG UID
ARG GID

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV TMD_STATIC_ROOT="${TMDSTATICDIR}"

RUN apt update

RUN groupadd -g "$GID" python && useradd -u "$UID" -g "$GID" python
WORKDIR "${TMDDIR}"
COPY app/utils/requirements.txt "${TMDDIR}/"
RUN mkdir -p "${TMDSTATICDIR}"
RUN pip install -r requirements.txt


# Production setup
FROM base AS prod

ARG TMDDIR
ARG TMDSTATICDIR

ENV DJANGO_PRODUCTION=1

COPY app/metrics "${TMDDIR}/metrics"
COPY app/tmd "${TMDDIR}/tmd"
COPY app/templates "${TMDDIR}/templates"
COPY app/static "${TMDDIR}/static"
COPY app/entrypoint "${TMDDIR}/"
COPY app/manage.py "${TMDDIR}/"
RUN chmod +x "${TMDDIR}/entrypoint"

RUN python manage.py collectstatic

USER python
ENTRYPOINT ./entrypoint


# Dev setup
FROM base AS dev
COPY app/utils/dev-requirements.txt "${TMDDIR}/"
RUN pip install -r dev-requirements.txt

ENV DJANGO_PRODUCTION=0

USER python
ENTRYPOINT ./entrypoint-dev