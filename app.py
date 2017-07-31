from flask import Flask, jsonify, json, request
from models import Drug, Symptom
from sqlalchemy.ext.declarative import declarative_base  
from sqlalchemy.orm import sessionmaker
import sqlalchemy
from sqlalchemy import Integer, and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import aliased
from sqlalchemy.orm.exc import NoResultFound
from models import get_session, Bridge_Symptom_Post, Bridge_Drug_Post, Bridge_Dosage_Quote, Post
from flask_cors import CORS, cross_origin
from flask_caching import Cache

app = Flask(__name__)
#app.config['JSON_AS_ASCII'] = False
CORS(app)
cache = Cache(app,config={'CACHE_TYPE': 'simple'})

CONTENT_TYPE = {'ContentType': 'application/json; charset=unicode'}

# TODO allow searching for drugs/symptoms with any name in the bucket

@app.route("/drugs")
@cache.cached()
def drugs():
    drugs = get_session().query(Drug).all()
    return jsonify([d.name for d in drugs]), 200, CONTENT_TYPE

@app.route("/dosage_quotes/<drug>/<dosage>")
def dosage_quotes(drug, dosage):
    db_session = get_session()
    drug_id = db_session.query(Drug).filter(Drug.name == drug).one().id
    bridges = db_session.query(Bridge_Dosage_Quote).filter(and_(Bridge_Dosage_Quote.drug_id == drug_id,
                                                                Bridge_Dosage_Quote.dosage_mg == dosage))
    post_ids = [bridge.post_id for bridge in bridges]
    posts = db_session.query(Post).filter(Post.id.in_(post_ids))
    post_originals = [post.original for post in posts]
    return jsonify(post_originals), 200, CONTENT_TYPE

def query_builder(session, Table1, Table2, condition1, condition2):
    return session.query(Table1.post_id)\
        .join(Table2, Table1.post_id == Table2.post_id)\
        .filter(and_(condition1, condition2))\
        .subquery()

@app.route("/related_quotes/<type1>/<key1>/<type2>/<key2>")
def related_quotes(type1, key1, type2, key2):
    db_session = get_session()

    # Query db for requested drugs/symptoms
    try:
        if type1 == "drug":
            res1 = db_session.query(Drug).filter(Drug.name == key1).one()
        else:
            res1 = db_session.query(Symptom).filter(Symptom.name == key1).one()
        if type2 == "drug":
            res2 = db_session.query(Drug).filter(Drug.name == key2).one()
        else:
            res2 = db_session.query(Symptom).filter(Symptom.name == key2).one()
    except NoResultFound:
        return 'Not found', 404, CONTENT_TYPE

    # Query db for related posts
    if type1 == "drug":
        Table1 = Bridge_Drug_Post
        condition1 = Table1.drug_id == res1.id
    else:
        Table1 = Bridge_Symptom_Post
        condition1 = Table1.symptom_id == res1.id
    if type2 == "drug":
        Table2 = aliased(Bridge_Drug_Post)
        condition2 = Table2.drug_id == res2.id
    else:
        Table2 = aliased(Bridge_Symptom_Post)
        condition2 = Table2.symptom_id == res2.id
    sq = query_builder(db_session, Table1, Table2, condition1, condition2)
    posts = db_session.query(Post.original).join(sq, sq.c.post_id == Post.id)

    posts = [str(x).decode('utf-8') for x in posts]
    return jsonify(posts), 200, CONTENT_TYPE

@app.route("/search/<term>")
def show_drug_or_symptom(term):
    try:
        res = get_session().query(Drug).filter(Drug.name == term).one()
        return jsonify(res[0].data), 200, CONTENT_TYPE
    except NoResultFound:
        return show_symptom(term)

@app.route("/drugs/<drug>")
def show_drug(drug):
    try:
        res = get_session().query(Drug).filter(Drug.name == drug).one()
        return jsonify(res.data), 200, CONTENT_TYPE
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
        res = get_session().query(Symptom).filter(Symptom.name == symptom).one()
        return jsonify(res.data), 200, CONTENT_TYPE
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