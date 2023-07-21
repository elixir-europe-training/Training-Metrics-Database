# Data migration scripts

This directory contains several queries to extract data from the old TMD database
and a Python script to run said queries and convert the results into a useful format.

## Setup

It's completely separate from the main application and has its own dependencies.
Install them like so (and make sure you deactivate your previous venv beforehand):

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

You also need access to the old TMD database. This can be the live database
or a copy created using the Drupal "Backup and Migrate" functionality.
Go to `/admin/config/system/backup_migrate`, download a dump of the full
database and run the downloaded script on a newly created local database.

Create a SQLAlchemy connection string for the target database.
Example for a local database (don't forget the `charset=utf8mb4`):

```
mysql+pymysql://user:pass@localhost/tmd?charset=utf8mb4
```

## Usage

With the virtualenv activated, run the `extract_from_db.py` script with the
database connection string as the first argument, like so:

```sh
./extract_from_db.sh 'mysql+pymysql://user:pass@localhost/tmd?charset=utf8mb4'
```

The script will connect to the database, extract data using the scripts in the
`queries` directory and dump the results in the `out` directory in several
formats. The `.raw.json` files contain the raw query outputs, while the
`.json` and `.csv` files are more similar to the new data model.

Note that they're not an exact match, so some additional processing may be
required.

Currently, this directory does not include scripts to insert data
into the new database.
