from flask import Flask, jsonify, json, request
from models import Drug
from sqlalchemy.ext.declarative import declarative_base  
from sqlalchemy.orm import sessionmaker
import sqlalchemy
from sqlalchemy import Integer
from sqlalchemy.exc import IntegrityError
from models import get_session

app = Flask(__name__)

session = get_session()

@app.route("/drugs")
def drugs():
    drugs = session.query(Drug).all()
    return jsonify([d.name for d in drugs]), 200, { 'ContentType': 'application/json' } 

@app.route("/drugs/<drug>")
def show(drug):
    uu = session.query(Drug).filter(Drug.name == drug).one()
    return jsonify(uu.data), 200, {'ContentType': 'application/json' } 

# Resource e.g drugs, symptoms
@app.route("/most_common/<resource>")
def common(resource):
    if resource == "drugs":
        return(jsonify(session.query(Drug).order_by(
                Drug.data[('count')].cast(Integer)).all()
            )), 200, {'ContentType': 'application/json' } 

@app.route("/upload", methods=["POST"])
def upload():
    if request.method == 'POST':
        content = request.json
        name = content["name"]
        data = content["data"]

        d = Drug(name=name, data=data)
        session.add(d)
        
        try:
            session.commit()
            return ("success", 200)
        except IntegrityError:
            return ("already exists", 400)