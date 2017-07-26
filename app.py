from flask import Flask, jsonify, json, request
from models import Drug, Symptom
from sqlalchemy.ext.declarative import declarative_base  
from sqlalchemy.orm import sessionmaker
import sqlalchemy
from sqlalchemy import Integer, and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import aliased
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

@app.route("/related_quotes/<type1>/<key1>/<type2>/<key2>")
def related_quotes(type1, key1, type2, key2):
    db_session = get_session()

    # Query db for requested drugs/symptoms, place into variables spec1, spec2
    if type1 == "drug":
        res1 = db_session.query(Drug).filter(Drug.name == key1).all()
    else:
        res1 = db_session.query(Symptom).filter(Symptom.name == key1).all()
    if type2 == "drug":
        res2 = db_session.query(Drug).filter(Drug.name == key2).all()
    else:
        res2 = db_session.query(Symptom).filter(Symptom.name == key2).all()
    if len(res1) == 0 or len(res2) == 0:
        return 'Not found', 404, CONTENT_TYPE
    spec1 = res1[0]
    spec2 = res2[0]

    # Query db for related posts
    if type1 == "drug" and type2 == "drug":
        bridge_alias = aliased(Bridge_Drug_Post)
        sq = db_session.query(Bridge_Drug_Post.post_id).join(bridge_alias, Bridge_Drug_Post.post_id == bridge_alias.post_id).filter(and_(Bridge_Drug_Post.drug_id == spec1.id, bridge_alias.drug_id == spec2.id)).subquery()
        posts = db_session.query(Post.original).join(sq, sq.c.post_id == Post.id)
    elif type1 == "drug" and type2 == "symptom":
        sq = db_session.query(Bridge_Drug_Post.post_id).join(Bridge_Symptom_Post, Bridge_Drug_Post.post_id == Bridge_Symptom_Post.post_id).filter(and_(Bridge_Drug_Post.drug_id == spec1.id, Bridge_Symptom_Post.symptom_id == spec2.id)).subquery()
        posts = db_session.query(Post.original).join(sq, sq.c.post_id == Post.id)
    elif type1 == "symptom" and type2 == "drug":
        sq = db_session.query(Bridge_Drug_Post.post_id).join(Bridge_Symptom_Post, Bridge_Drug_Post.post_id == Bridge_Symptom_Post.post_id).filter(and_(Bridge_Drug_Post.drug_id == spec2.id, Bridge_Symptom_Post.symptom_id == spec1.id)).subquery()
        posts = db_session.query(Post.original).join(sq, sq.c.post_id == Post.id)
    elif type1 == "symptom" and type2 == "symptom":
        bridge_alias = aliased(Bridge_Symptom_Post)
        sq = db_session.query(Bridge_Symptom_Post.post_id).join(bridge_alias, Bridge_Symptom_Post.post_id == bridge_alias.post_id).filter(and_(Bridge_Symptom_Post.symptom_id == spec1.id, bridge_alias.symptom_id == spec2.id)).subquery()
        posts = db_session.query(Post.original).join(sq, sq.c.post_id == Post.id)

    posts = [str(x).decode('utf-8') for x in posts]
    print type(posts[0])
    return jsonify(posts), 200, CONTENT_TYPE

@app.route("/search/<term>")
def show_drug_or_symptom(term):
    res = get_session().query(Drug).filter(Drug.name == term).all()
    if len(res) == 0:
        return show_symptom(term)
    return jsonify(res[0].data), 200, CONTENT_TYPE

@app.route("/drugs/<drug>")
def show_drug(drug):
    res = get_session().query(Drug).filter(Drug.name == drug).all()
    return jsonify(res[0].data), 200, CONTENT_TYPE

@app.route("/symptoms")
@cache.cached()
def symptoms():
    symptoms = get_session().query(Symptom).all()
    return jsonify([s.name for s in symptoms]), 200, CONTENT_TYPE

@app.route("/symptoms/<symptom>")
@cache.cached()
def show_symptom(symptom):
    res = get_session().query(Symptom).filter(Symptom.name == symptom).one()
    return jsonify(res.data), 200, CONTENT_TYPE

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

'''
@app.route("/upload", methods=["POST"])
def upload():
    if request.method == 'POST':
        content = request.json
        name = content["name"]
        data = content["data"]

        d = Drug(name=name, data=data)
        session = get_session()
        session.add(d)
        
        try:
            session.commit()
            return ("success", 200)
        except IntegrityError:
            return ("already exists", 400)
'''