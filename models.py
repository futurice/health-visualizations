
import json  
import sqlalchemy  
from sqlalchemy import Column, Integer, Text, Index
from sqlalchemy.dialects.postgresql import JSON, JSONB
from sqlalchemy.ext.declarative import declarative_base  
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Table, Column, Integer, ForeignKey
from sqlalchemy.orm import relationship

import os 

PSQL_USERNAME = os.environ['PSQL_USERNAME']

try: # added new env variable. try-except is here temporarily so that this commit doesn't break anything.
    PSQL_PASSWORD = os.environ['PSQL_PASSWORD']
except:
    PSQL_PASSWORD = PSQL_USERNAME

PSQL_DB = os.environ['PSQL_DB']

connection_string = 'postgresql://' + PSQL_USERNAME + ':' + PSQL_PASSWORD + '@localhost:5432/' + PSQL_DB
db = sqlalchemy.create_engine(connection_string)  
engine = db.connect()  
meta = sqlalchemy.MetaData(engine)

def get_db ():
    return db

def get_session():
    # This should be called only once! Persistence problems otherwise.
    # TODO: make into singleton?
    SessionFactory = sessionmaker(engine) 
    session = SessionFactory()
    return session

Base = declarative_base()


class Post(Base):
    __tablename__ = 'posts'

    id = Column(Integer, primary_key=True)
    original = Column(Text, unique=False)
    lemmatized = Column(Text, unique=False)

class Drug(Base):
    __tablename__ = 'drugs'
    id = Column(Integer, primary_key=True)
    name = Column(Text, unique=True)
    data = Column(JSONB)

class Symptom(Base):
    __tablename__ = 'symptoms'
    id = Column(Integer, primary_key=True)
    name = Column(Text, unique=True)
    data = Column(JSONB)

class Bridge_Dosage_Quote(Base):
    __tablename__ = 'bridge_dosage_quotes'

    id = Column(Integer, primary_key=True)
    post_id = Column(Integer, ForeignKey('posts.id'))
    drug_id = Column(Integer, ForeignKey('drugs.id'))
    dosage_mg = Column(Integer)

    ref_post = relationship(Post, backref="bridge_dosage_quotes")
    ref_drug = relationship(Drug, backref="bridge_dosage_quotes")

class Bridge_Drug_Post(Base):
    __tablename__ = 'bridge_drug_posts'

    id = Column(Integer, primary_key=True)
    post_id = Column(Integer, ForeignKey('posts.id'))
    drug_id = Column(Integer, ForeignKey('drugs.id'))

    ref_post = relationship(Post, backref="bridge_drug_posts")
    ref_drug = relationship(Drug, backref="bridge_drug_posts")


class Bridge_Symptom_Post(Base):
    __tablename__ = 'bridge_symptom_posts'

    id = Column(Integer, primary_key=True)
    post_id = Column(Integer, ForeignKey('posts.id'))
    symptom_id = Column(Integer, ForeignKey('symptoms.id'))

    ref_post = relationship(Post, backref="bridge_symptom_posts")
    ref_symptom = relationship(Symptom, backref="bridge_symptom_posts")



if __name__ == "__main__":
    if raw_input("Drop previous database schema and all data from " + PSQL_DB + "? Enter y/n: ") == "y":
        meta.reflect()
        meta.drop_all()
    else:
        print "Ok, we can try to insert new tables, but existing tables won't be touched."
        if raw_input("Add indexes? Enter y/n: ") == "y":
            idx1 = Index('bridge_drug_post_id_idx', Bridge_Drug_Post.id)
            idx2 = Index('bridge_drug_post_post_id_idx', Bridge_Drug_Post.post_id)
            idx3 = Index('bridge_drug_post_drug_id_idx', Bridge_Drug_Post.drug_id)
            idx4 = Index('bridge_symptom_post_id_idx', Bridge_Symptom_Post.id)
            idx5 = Index('bridge_symptom_post_post_id_idx', Bridge_Symptom_Post.post_id)
            idx6 = Index('bridge_symptom_post_symptom_id_idx', Bridge_Symptom_Post.symptom_id)
            idx1.create(bind=engine)
            idx2.create(bind=engine)
            idx3.create(bind=engine)
            idx4.create(bind=engine)
            idx5.create(bind=engine)
            idx6.create(bind=engine)

    Base.metadata.create_all(engine)
