from __future__ import print_function

import sys

from flask import jsonify
from sqlalchemy.orm.exc import NoResultFound

from puoback import app, cache, db
from puoback.services import db_session
from puoback.models import Post, Search_Term, Drug, Symptom

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
        posts = Post.find_dosage_quotes(session, drug, dosage, page)
        posts = [x[0] for x in posts]
        page_count = 7
        combined = {"page_count": page_count, "posts": posts}
        return jsonify(combined), 200, CONTENT_TYPE

def find_search_term(session, key):
    return Search_Term.find_drug_or_symptom(session, key)


@app.route("/pagecount/<key1>/<key2>")
def page_count(key1, key2):
    with db_session(db) as session:
        try:
            print('*************** No cache hit for /pagecount/' + key1 + "/" + key2, file=sys.stderr)
            res1 = find_search_term(session, key1)
            res2 = find_search_term(session, key2)
            page_count = Post.find_page_count(session, res1, res2)
            return jsonify(page_count), 200, CONTENT_TYPE
        except NoResultFound:
            return 'Not found', 404, CONTENT_TYPE


@app.route("/related_quotes/<key1>/<key2>/page/<page>")
@cache.cached()
def related_quotes(key1, key2, page):
    with db_session(db) as session:
        try:
            print('*************** No cache hit for /related_quotes/' + key1 + "/" + key2 + "/page/" + page, file=sys.stderr)
            res1 = find_search_term(session, key1)
            res2 = find_search_term(session, key2)
            posts, page_count = Post.find_related_quotes(session, res1, res2, page)
            posts = [x[0] for x in posts]
            combined = { "page_count":page_count, "posts":posts }
            return jsonify(combined), 200, CONTENT_TYPE
        except NoResultFound:
            return 'Not found', 404, CONTENT_TYPE

@app.route("/search/<term>")
@cache.cached()
def show_drug_or_symptom(term):
    with db_session(db) as session:
        try:
            res = find_search_term(session, term)
            return jsonify(res.data), 200, CONTENT_TYPE
        except NoResultFound:
            return 'Not found', 404, CONTENT_TYPE

@app.route("/drugs/<drug>")
@cache.cached()
def show_drug(drug):
    with db_session(db) as session:
        try:
            d = Drug.find_drug(session, drug)
            return jsonify(d.data), 200, CONTENT_TYPE
        except NoResultFound:
            return 'Not found', 404, CONTENT_TYPE

@app.route("/symptoms")
@cache.cached()
def symptoms():
    with db_session(db) as session:
        try:
            symptoms = session.query(Symptom).all()
            return jsonify([s.name for s in symptoms]), 200, CONTENT_TYPE
        except NoResultFound:
            return 'Not found', 404, CONTENT_TYPE

@app.route("/symptoms/<symptom>")
@cache.cached()
def show_symptom(symptom):
    with db_session(db) as session:
        try:
            s = Symptom.find_symptom(session, symptom)
            return jsonify(s.data), 200, CONTENT_TYPE
        except NoResultFound:
            return 'Not found', 404, CONTENT_TYPE


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
