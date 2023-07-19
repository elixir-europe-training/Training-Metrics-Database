# ELIXIR-TrP-Tango

For the Training Metrics Database (TMD) of the [ELIXIR Training Platform](https://elixir-europe.org/platforms/training).

## Getting started

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
