# Lääketutka backend

This repository contains the backend for [Lääketutka](https://www.laaketutka.fi). You also need the [frontend](https://github.com/futurice/health-visualizations-front).

### Set up

* Python 3
* flask
* sqlalchemy
* [Heroku command line tools](https://devcenter.heroku.com/articles/heroku-cli)
* Postgres DB
    * Set env variables `$PSQL_USERNAME`, `$PSQL_PASSWORD` and `$PSQL_DB`

### Populate the database

This application expects that the database is populated with the drug and
symptom statistics derived from the Suomi24 data. There are two ways to
initialize the database: if you have access to the Suomi24 data dump (only
university affiliated researchers do), you can re-generate the dataset. If you
don't have the original data, you can copy the database content from the
production database on AWS. These two ways are described below.

#### Generating the dataset from the Suomi24 dump

See [the related repository](https://github.com/futurice/laaketutka-prereqs) for how to produce the following files:

* `data.json`
* `drugs_stemmed.txt`
* `symptoms_three_ways.txt`

Create and populate the local database with `scripts/associations.py`.

#### Importing data from one DB to another

See [instructions for importing data from one DB to another](UPDATE_DB.md).

You can apply the instructions in two ways: to copy data from the local DB to
the production DB on AWS after you have computed the statistics from the
original Suomi24 data, or to copy DB content from AWS to you local DB (if you
don't have access to the original Suomi24 data).

### Local development

```bash
# Install the native dependencies. For example, on Ubuntu:
sudo apt install python3-psycopg2 libpq-dev

# Install Python dependencies
pip install -r requirements.txt -r requirements_dev.txt
```

### Run in Docker

```bash
./build_docker.sh

export DATABASE_URL=postgres://<user>:<password>@<host>/<dbname>
./run_in_docker.sh
```

Open [localhost:8000/drug](http://localhost:8000/drugs).

## Deployment

```bash
heroku login

# staging
git push heroku_staging master

# prod
git push heroku master
```
