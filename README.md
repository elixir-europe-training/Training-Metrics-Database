# Tango - the new version of the Training Metrics Database

The readme file for Tango, the new Training Metrics Database of the [ELIXIR Training Platform](https://elixir-europe.org/platforms/training).

The Training Metrics Database was developed in an effort to streamline data collection, storage, and visualisation for the Quality and Impact Subtask of the [ELIXIR Training Platform](https://elixir-europe.org/platforms/training), which aims to:

- Describe the **audience demographic** being reached by ELIXIR-badged training events,
- Assess the **quality** of ELIXIR-badged training events directly after they have taken place,
- Evaluate the longer term **impact** that ELIXIR-badged training events have had on the work of training participants.

In an effort to achieve the above aims, the subtask, in collaboration with the [ELIXIR Training Coordinators](https://elixir-europe.org/platforms/training/how-organised), has compiled a set of core metrics for measuring audience demographics and training quality, in the short term, and training impact, in the longer term. Both sets of metrics are collected via feedback survey. In some cases, the demographic information is collected via registration form. These metrics were developed out of those already collected by ELIXIR training providers as well as from discussions with stakeholders and external training providers.

The most up to date documentation is available in [Wiki](https://github.com/elixir-europe-training/ELIXIR-TrP-Training-Metrics-Database-Tango/wiki).

## Getting started

### Running with Docker

```shell
docker compose up
```

In order to load thee example data:

```shell
docker compose exec tango python manage.py load_data
```

### Running local validation checks

```shell
pre-commit run -a
```
