# ELIXIR-TrP-Tango

For the Tango, new Training Metrics Database of the [ELIXIR Training Platform](https://elixir-europe.org/platforms/training).

## Getting started

### Running with Docker

```shell
docker compose up
```

### Installation

```shell
python3 -m venv .venv
source .venv/bin/activate
pip3 install -r utils/requirements.txt
pip3 install -r utils/dev-requirements.txt
```

### Running local development server

```shell
source .venv/bin/activate
python3 manage.py migrate
python3 manage.py runserver
```

### Running local validation checks

```shell
pre-commit run -a
```

## Production

### Environment

The following settings need to be defined in the environment

```
DJANGO_PRODUCTION           # Set to 1 only in production
DJANGO_SECRET_KEY           # A random string of characters - e.g. 3i%9&+g@dux1+bj)d&g=isgtza29tohv$)9zpp8$lg=x6-=bcr
DJANGO_POSTGRESQL_DBNAME    # Name of database
DJANGO_POSTGRESQL_USER
DJANGO_POSTGRESQL_PASSWORD
DJANGO_POSTGRESQL_HOST      # Hostname or IP address
DJANGO_POSTGRESQL_PORT      # Typically 5432
```
