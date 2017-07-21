
import json  
import sqlalchemy  
from sqlalchemy import Column, Integer, Text  
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

def get_session():    
    SessionFactory = sessionmaker(engine) 
    session = SessionFactory()
    return session

Base = declarative_base()


bridge_dosage_quotes = Table('bridge_dosage_quotes', Base.metadata,
                          Column('post_id', Integer, ForeignKey('posts.id')),
                          Column('drug_id', Integer, ForeignKey('drugs.id')),
                          Column('dosage_mg', Integer))

bridge_drug_posts = Table('bridge_drug_posts', Base.metadata,
                          Column('post_id', Integer, ForeignKey('posts.id')),
                          Column('drug_id', Integer, ForeignKey('drugs.id')))

bridge_symptom_posts = Table('bridge_symptom_posts', Base.metadata,
                          Column('post_id', Integer, ForeignKey('posts.id')),
                          Column('symptom_id', Integer, ForeignKey('symptoms.id')))

class Post(Base):
    __tablename__ = 'posts'
    id = Column(Integer, primary_key=True)
    original = Column(Text, unique=False)
    lemmatized = Column(Text, unique=False)
    ref_dosages = relationship("Drug", secondary=bridge_dosage_quotes, back_populates="ref_dosages")
    ref_drug_posts = relationship("Drug", secondary=bridge_drug_posts, back_populates="ref_posts")
    ref_symptom_posts = relationship("Symptom", secondary=bridge_symptom_posts, back_populates="ref_posts")

class Drug(Base):
    __tablename__ = 'drugs'
    id = Column(Integer, primary_key=True)
    name = Column(Text, unique=True)
    data = Column(JSONB)
    ref_dosages = relationship("Post", secondary=bridge_dosage_quotes, back_populates="ref_dosages")
    ref_posts = relationship("Post", secondary=bridge_drug_posts, back_populates="ref_drug_posts")

class Symptom(Base):
    __tablename__ = 'symptoms'
    id = Column(Integer, primary_key=True)
    name = Column(Text, unique=True)
    data = Column(JSONB)
    ref_posts = relationship("Post", secondary=bridge_symptom_posts, back_populates="ref_symptom_posts")



if __name__ == "__main__":
    if raw_input("Drop previous database schema and all data from " + PSQL_DB + "? Enter y/n: ") == "y":
        meta.reflect()
        meta.drop_all()
    else:
        print "Ok, we can try to insert new tables, but existing tables won't be touched."

    Base.metadata.create_all(engine)
