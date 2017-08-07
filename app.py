from __future__ import print_function # In python 2.7
import time

import sys
from flask import Flask, jsonify
from models import Drug, Symptom
from sqlalchemy.orm.exc import NoResultFound
from models import app, db, Post, Search_Term
from services import db_session
from flask_cors import CORS
from flask_caching import Cache

CORS(app)
cache = Cache(app,config={'CACHE_TYPE': 'simple'})

CONTENT_TYPE = {'ContentType': 'application/json; charset=unicode'}

@app.route("/test")
def route_test():
    return str(__name__), 200, CONTENT_TYPE

@app.route("/drugs")
@cache.cached()
def drugs():
    with db_session(db) as session:
        drugs = session.query(Drug).all()

    return jsonify([d.name for d in drugs]), 200, CONTENT_TYPE

@app.route("/dosage_quotes/<drug>/<dosage>/page/<page>")
@cache.cached()
def dosage_quotes(drug, dosage, page):
    with db_session(db) as session:
        quotes = Post.find_dosage_quotes(session, drug, dosage, page)

    return jsonify(quotes), 200, CONTENT_TYPE

def find_search_term(session, key):
    print('LOOKING UP DB FOR ' + key, file=sys.stderr)
    return Search_Term.find_drug_or_symptom(session, key)

@app.route("/related_quotes/<key1>/<key2>/page/<page>")
@cache.cached()
def related_quotes(key1, key2, page):
    with db_session(db) as session:
        try:
            res1 = find_search_term(session, key1)
            res2 = find_search_term(session, key2)
        except NoResultFound:
            return 'Not found', 404, CONTENT_TYPE

        print('************* KEY1 CORRESPONDS TO ' + res1.name, file=sys.stderr)
        print('************* KEY2 CORRESPONDS TO ' + res2.name, file=sys.stderr)

        posts = Post.find_related_quotes(session, res1, res2, page)
        posts = [str(x).decode('utf-8') for x in posts]

    return jsonify(posts), 200, CONTENT_TYPE

@app.route("/search/<term>")
@cache.cached()
def show_drug_or_symptom(term):
    with db_session(db) as session:
        try:
            res = find_search_term(session, term)
        except NoResultFound:
            return 'Not found', 404, CONTENT_TYPE

    return jsonify(res.data), 200, CONTENT_TYPE

@app.route("/drugs/<drug>")
@cache.cached()
def show_drug(drug):
    with db_session(db) as session:
        try:
            d = Drug.find_drug(session, drug)
        except NoResultFound:
            return 'Not found', 404, CONTENT_TYPE

    return jsonify(d.data), 200, CONTENT_TYPE

@app.route("/symptoms")
@cache.cached()
def symptoms():
    with db_session(db) as session:
        try:
            symptoms = session.query(Symptom).all()
        except NoResultFound:
            return 'Not found', 404, CONTENT_TYPE

    return jsonify([s.name for s in symptoms]), 200, CONTENT_TYPE


@app.route("/symptoms/<symptom>")
@cache.cached()
def show_symptom(symptom):
    with db_session(db) as session:
        try:
            s = Symptom.find_symptom(session, symptom)
        except NoResultFound:
            return 'Not found', 404, CONTENT_TYPE

    return jsonify(s.data), 200, CONTENT_TYPE

# Resource e.g drugs, symptoms
@app.route("/most_common/<resource>")
@cache.cached()
def common(resource):
    with db_session(db) as session:
        if resource == "drugs":
            query = session.query(Drug).order_by(Drug.data['post_count'].desc())
            results = [(drug.name, drug.data['post_count']) for drug in query.all()]
        elif resource == "symptoms":
            query = session.query(Symptom).order_by(Symptom.data['post_count'].desc())
            results = [(symptom.name, symptom.data['post_count']) for symptom in query.all()]

    return jsonify(results), 200, CONTENT_TYPE
