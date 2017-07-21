# Health Visualizations (Suomi24 data)

## Development

Prequisites

* Python 2
* flask
* sqlalchemy
* sudo apt-get install python-psycopg2
* pip install psycopg2
* Postgres DB
    * Set `$PSQL_USERNAME` and `$PSQL_DB`

Instructions

* Run `models.py` to create tables and `associations.py` to populate them. 
* Start server with `FLASK_APP=app.py FLASK_DEBUG=1 flask run` for development.

TODO `requirements.txt`
