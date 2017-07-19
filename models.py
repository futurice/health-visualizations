
import json  
import sqlalchemy  
from sqlalchemy import Column, Integer, Text  
from sqlalchemy.dialects.postgresql import JSON, JSONB
from sqlalchemy.ext.declarative import declarative_base  
from sqlalchemy.orm import sessionmaker
import os 

PSQL_USERNAME = os.environ['PSQL_USERNAME']
PSQL_DB = os.environ['PSQL_DB']
connection_string = 'postgresql://' + PSQL_USERNAME + ':' + PSQL_USERNAME + '@localhost:5432/' + PSQL_DB
db = sqlalchemy.create_engine(connection_string)  
engine = db.connect()  
meta = sqlalchemy.MetaData(engine)  

def get_session():    
    SessionFactory = sessionmaker(engine) 
    session = SessionFactory()
    return session

Base = declarative_base()  

class Drug(Base):
    __tablename__ = 'drugs'
    id = Column(Integer, primary_key=True)
    name = Column(Text, unique=True)
    data = Column(JSONB)

if __name__ == "__main__":
    Base.metadata.create_all(engine)
