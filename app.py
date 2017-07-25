from flask import Flask, jsonify, json, request
from models import Drug, Symptom
from sqlalchemy.ext.declarative import declarative_base  
from sqlalchemy.orm import sessionmaker
import sqlalchemy
from sqlalchemy import Integer, and_
from sqlalchemy.exc import IntegrityError
from models import get_session, Bridge_Symptom_Post, Bridge_Drug_Post, Bridge_Dosage_Quote, Post
from flask_cors import CORS, cross_origin

app = Flask(__name__)
CORS(app)

CONTENT_TYPE = {'ContentType': 'application/json' }

# TODO allow searching for drugs/symptoms with any name in the bucket

@app.route("/drugs")
def drugs():
    drugs = get_session().query(Drug).all()
    return jsonify([d.name for d in drugs]), 200, CONTENT_TYPE

@app.route("/meh")
def blah():
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

def find_spec(db_session, name):
    res = db_session.query(Drug).filter(Drug.name == name).all()
    if len(res) == 0:
        res = db_session.query(Symptom).filter(Symptom.name == name).all()
    if len(res) == 0:
        return None
    return res[0]

@app.route("/related_quotes/<type1>/<key1>/<type2>/<key2>")
def related_quotes(type1, key1, type2, key2):
    db_session = get_session()
    spec1 = find_spec(db_session, key1)
    spec2 = find_spec(db_session, key2)
    if spec2 is None or spec1 is None:
        return 'Not found', 404, CONTENT_TYPE


    '''
    if type1 == Drug:
        bridges_with_key1 = db_session.query(Bridge_Drug_Post).filter(Bridge_Drug_Post.drug_id == spec1.id).all()
    else:
        bridges_with_key1 = db_session.query(Bridge_Symptom_Post).filter(Bridge_Symptom_Post.symptom_id == spec1.id).all()
    if type2 == Drug:
        bridges_with_key2 = db_session.query(Bridge_Drug_Post).filter(Bridge_Drug_Post.drug_id == spec2.id).all()
    else:
        bridges_with_key2 = db_session.query(Bridge_Symptom_Post).filter(Bridge_Symptom_Post.symptom_id == spec2.id).all()

    post_ids_with_key1 = [bridge.post_id for bridge in bridges_with_key1]
    post_ids_with_key2 = [bridge.post_id for bridge in bridges_with_key2]
    post_ids_with_key1 = set(post_ids_with_key1)
    post_ids_with_both = [id for id in post_ids_with_key2 if id in post_ids_with_key1]
    posts = db_session.query(Post).filter(Post.id.in_(post_ids_with_both))'''

    if type1 == Drug and type2 == Drug:
        query_1 = db_session.query(Bridge_Drug_Post.post_id).filter(Bridge_Drug_Post.drug_id == spec1.id)
        query_2 = db_session.query(Bridge_Drug_Post.post_id).filter(Bridge_Drug_Post.drug_id == spec2.id)

        query_1.join(query_2.)


    post_originals = [post.original for post in posts]
    return jsonify(post_originals), 200, CONTENT_TYPE


@app.route("/drugs/<drug>")
def show_drug(drug):
    res = get_session().query(Drug).filter(Drug.name == drug).one()
    return jsonify(res.data), 200, CONTENT_TYPE

@app.route("/symptoms")
def symptoms():
    symptoms = get_session().query(Symptom).all()
    return jsonify([s.name for s in symptoms]), 200, CONTENT_TYPE

@app.route("/symptoms/<symptom>")
def show_symptom(symptom):
    res = get_session().query(Symptom).filter(Symptom.name == symptom).one()
    return jsonify(res.data), 200, CONTENT_TYPE

# Resource e.g drugs, symptoms
@app.route("/most_common/<resource>")
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