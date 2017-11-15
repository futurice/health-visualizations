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
* sudo apt-get install python-psycopg2
* pip install -r requirements.txt
* [Heroku CLI](https://devcenter.heroku.com/articles/heroku-cli)
* Postgres DB
    * Set env variables `$PSQL_USERNAME`, `$PSQL_PASSWORD` and `$PSQL_DB`

### Use

* Create and populate the database with `associations.py`
* Run backend server locally with `heroku local`
    * http://localhost:5000/drugs
* Push to staging server before pushing to production
* See [instructions](UPDATE_DB.md) for updating the production database
