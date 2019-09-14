# Lääketutka backend

This repository contains the backend for [Lääketutka](https://www.laaketutka.fi). You also need the [frontend](https://github.com/futurice/health-visualizations-front).

### Prerequisites

See [related repository](https://github.com/futurice/laaketutka-prereqs) for how to produce the following files:

* `data.json`
* `drugs_stemmed.txt`
* `symptoms_three_ways.txt`

### Set up

* Python 2
* flask
* sqlalchemy
* [Heroku command line tools](https://devcenter.heroku.com/articles/heroku-cli)
* Postgres DB
    * Set env variables `$PSQL_USERNAME`, `$PSQL_PASSWORD` and `$PSQL_DB`

### Prepare the database

Create and populate the database with `associations.py`.

See [instructions](UPDATE_DB.md) for updating the production database.

### Local development

```bash
sudo apt-get install python-psycopg2
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
