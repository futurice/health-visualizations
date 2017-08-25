# Nettipuoskari backend

This repository contains the backend for [Nettipuoskari](https://www.nettipuoskari.fi).

### Prerequisites

See [related repository](https://github.com/futurice/how-to-get-healthy) for how to produce the following files:

* `data.json`
* `drugs_stemmed.txt`
* `symptoms_three_ways.txt`

### Set up

* Python 2
* flask
* sqlalchemy
* sudo apt-get install python-psycopg2
* pip install psycopg2
* pip install flask-cache
* [Heroku CLI](https://devcenter.heroku.com/articles/heroku-cli)
* Postgres DB
    * Set env variables `$PSQL_USERNAME`, `$PSQL_PASSWORD` and `$PSQL_DB`

### Use

* Create and populate the database with `associations.py`
* Run backend server locally with `heroku local`
* Push to staging server before pushing to production
* See [instructions](UPDATE_DB.md) for updating the production database