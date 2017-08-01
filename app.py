from __future__ import print_function # In python 2.7
import time

import sys
from flask import Flask, jsonify, json, request
from models import Drug, Symptom
from sqlalchemy.ext.declarative import declarative_base  
from sqlalchemy.orm import sessionmaker
import sqlalchemy
from sqlalchemy import Integer, and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import aliased
from sqlalchemy.orm.exc import NoResultFound
from models import get_session, Bridge_Symptom_Post, Bridge_Drug_Post, Bridge_Dosage_Quote, Post, Search_Term
from flask_cors import CORS, cross_origin
from flask_caching import Cache

app = Flask(__name__)
#app.config['JSON_AS_ASCII'] = False
CORS(app)
cache = Cache(app,config={'CACHE_TYPE': 'simple'})

CONTENT_TYPE = {'ContentType': 'application/json; charset=unicode'}

@app.route("/drugs")
@cache.cached()
def drugs():
    drugs = get_session().query(Drug).all()
    return jsonify([d.name for d in drugs]), 200, CONTENT_TYPE

@app.route("/dosage_quotes/<drug>/<dosage>")
@cache.cached()
def dosage_quotes(drug, dosage):
    quotes = Post.find_dosage_quotes(drug, dosage)
    return jsonify(quotes), 200, CONTENT_TYPE

@app.route("/related_quotes/<key1>/<key2>")
@cache.cached()
def related_quotes(key1, key2):
    db_session = get_session()

    try:
        res1 = Search_Term.find_drug_or_symptom(db_session, key1)
        res2 = Search_Term.find_drug_or_symptom(db_session, key2)
    except NoResultFound:
        return 'Not found', 404, CONTENT_TYPE

    posts = Post.find_related_quotes(db_session, res1, res2)
    posts = [str(x).decode('utf-8') for x in posts]
    return jsonify(posts), 200, CONTENT_TYPE

@app.route("/search/<term>")
@cache.cached()
def show_drug_or_symptom(term):
    try:
        res = Search_Term.find_drug_or_symptom(get_session(), term)
        return jsonify(res.data), 200, CONTENT_TYPE
    except NoResultFound:
        return 'Not found', 404, CONTENT_TYPE

@app.route("/drugs/<drug>")
@cache.cached()
def show_drug(drug):
    try:
        d = Drug.find_drug(get_session(), drug)
        return jsonify(d.data), 200, CONTENT_TYPE
    except NoResultFound:
        return 'Not found', 404, CONTENT_TYPE

@app.route("/symptoms")
@cache.cached()
def symptoms():
    try:
        symptoms = get_session().query(Symptom).one()
        return jsonify([s.name for s in symptoms]), 200, CONTENT_TYPE
    except NoResultFound:
        return 'Not found', 404, CONTENT_TYPE

@app.route("/symptoms/<symptom>")
@cache.cached()
def show_symptom(symptom):
    try:
        s = Symptom.find_symptom(get_session(), symptom)
        return jsonify(s.data), 200, CONTENT_TYPE
    except NoResultFound:
        return 'Not found', 404, CONTENT_TYPE

# Resource e.g drugs, symptoms
@app.route("/most_common/<resource>")
@cache.cached()
def common(resource):
    if resource == "drugs":
        query = get_session().query(Drug).order_by(Drug.data['postCount'].desc())
        results = [(drug.name, drug.data['postCount']) for drug in query.all()]
        return jsonify(results), 200, CONTENT_TYPE 
    elif resource == "symptoms":
        query = get_session().query(Symptom).order_by(Symptom.data['postCount'].desc())
        results = [(symptom.name, symptom.data['postCount']) for symptom in query.all()]
        return jsonify(results), 200, CONTENT_TYPE