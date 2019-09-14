from __future__ import print_function

import os

from flask import Flask
from flask_cache import Cache
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy

try:
    # Staging and production on Heroku
    PSQL_URL = os.environ['DATABASE_URL']
except:
    # Local development
    PSQL_USERNAME = os.environ['PSQL_USERNAME']
    PSQL_PASSWORD = os.environ['PSQL_PASSWORD']
    PSQL_DB = os.environ['PSQL_DB']
    # PSQL_DB = 'do8lpb57a1pia'
    PSQL_URL = 'postgresql://' + PSQL_USERNAME + ':' + PSQL_PASSWORD + '@localhost:5432/' + PSQL_DB

app = Flask('app')
app.config['SQLALCHEMY_DATABASE_URI'] = PSQL_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy()
cache = Cache(config={'CACHE_TYPE': 'simple', 'CACHE_THRESHOLD': 10000})
CORS(app)
CONTENT_TYPE = {'ContentType': 'application/json; charset=unicode'}


def create_app():
    from puoback import resources

    db.init_app(app)
    cache.init_app(app)

    return app
