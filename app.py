connection_string = 'postgresql://craj:craj@localhost:5432/datavis'

from flask import Flask, jsonify
from models import Drug
from sqlalchemy.ext.declarative import declarative_base  
from sqlalchemy.orm import sessionmaker
import sqlalchemy
from sqlalchemy import Integer

app = Flask(__name__)

db = sqlalchemy.create_engine(connection_string)  
engine = db.connect()  
meta = sqlalchemy.MetaData(engine)  

SessionFactory = sessionmaker(engine) 
session = SessionFactory()  

@app.route("/drugs")
def drugs():
    drugs = session.query(Drug).all()
    return jsonify([d.name for d in drugs])

@app.route("/drugs/<drug>")
def show(drug):
    uu = session.query(Drug).filter(Drug.name == drug).one()
    return jsonify(uu.data)

# Resource e.g drugs, symptoms
@app.route("/most_common/<resource>")
def common(resource):
    if resource == "drugs":
        return(jsonify(session.query(Drug).order_by(
                Drug.data[('count')].cast(Integer)).all()
            ))