[![Open in Gitpod](https://gitpod.io/button/open-in-gitpod.svg)](https://gitpod.io/#https://github.com/elixir-europe-training/Training-Metrics-Database/)

# TMD - a new version of the Training Metrics Database

This is the new Training Metrics Database of the [ELIXIR Training Platform](https://elixir-europe.org/platforms/training).

The Training Metrics Database was developed in an effort to streamline data collection, storage, and visualisation for the Quality and Impact Subtask of the ELIXIR Training Platform, which aims to:

- Describe the **audience demographic** being reached by ELIXIR-badged training events,
- Assess the **quality** of ELIXIR-badged training events directly after they have taken place,
- Evaluate the longer term **impact** that ELIXIR-badged training events have had on the work of training participants.

In an effort to achieve the above aims, the subtask, in collaboration with the [ELIXIR Training Coordinators](https://elixir-europe.org/platforms/training/how-organised), has compiled a set of core metrics for measuring audience demographics and training quality, in the short term, and training impact, in the longer term. Both sets of metrics are collected via feedback survey. In some cases, the demographic information is collected via registration form. These metrics were developed out of those already collected by ELIXIR training providers as well as from discussions with stakeholders and external training providers.

The most up to date documentation is available in [Wiki](https://github.com/elixir-europe-training/Training-Metrics-Database/wiki).

## Getting started
Make sure to create instances of the following files:
- `env/django.env`
- `env/metabase.env`
- `env/postgres.env`

The necessary parameters are covered in the respective `env/*.default` files.

### Running with development Docker
Make sure to set `DJANGO_PRODUCTION=0` in `env/django.env`.

```shell
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

Seed the database with test data:

```shell
docker compose exec tmd-dj python manage.py load_data
```

### Running with production Docker 

```shell
docker compose up --build
```

Seed the database with production data:

```shell
docker compose up --build
# We do it this way in order to avoid having the seed data mounted in the production environment
docker compose run --volume "/$(pwd)/raw-tmd-data:/opt/tmd/app/raw-tmd-data:ro" --entrypoint "python manage.py load_data" tmd-dj
```

### Running local validation checks

```shell
pre-commit run -a
```
