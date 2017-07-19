from flask import Flask, jsonify, json, request
from models import Drug, Symptom
from sqlalchemy.ext.declarative import declarative_base  
from sqlalchemy.orm import sessionmaker
import sqlalchemy
from sqlalchemy import Integer
from sqlalchemy.exc import IntegrityError
from models import get_session

app = Flask(__name__)

CONTENT_TYPE = {'ContentType': 'application/json' }

@app.route("/drugs")
def drugs():
    drugs = get_session().query(Drug).all()
    return jsonify([d.name for d in drugs]), 200, { 'ContentType': 'application/json' } 

@app.route("/drugs/<drug>")
def show(drug):
    uu = get_session().query(Drug).filter(Drug.name == drug).one()
    return jsonify(uu.data), 200, CONTENT_TYPE

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