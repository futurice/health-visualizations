
import json  
import sqlalchemy  
from sqlalchemy import Column, Integer, Text  
from sqlalchemy.dialects.postgresql import JSON, JSONB
from sqlalchemy.ext.declarative import declarative_base  
from sqlalchemy.orm import sessionmaker

connection_string = 'postgresql://craj:craj@localhost:5432/datavis'


def get_session():
    db = sqlalchemy.create_engine(connection_string)  
    engine = db.connect()  
    meta = sqlalchemy.MetaData(engine)  

    SessionFactory = sessionmaker(engine) 
    session = SessionFactory()
    return session


Base = declarative_base()  

class Drug(Base):  
    __tablename__ = 'drugs'
    id = Column(Integer, primary_key=True)
    name = Column(Text, unique=True)
    data = Column(JSON)

if __name__ == "__main__":
    db = sqlalchemy.create_engine(connection_string)  
    engine = db.connect()  
    meta = sqlalchemy.MetaData(engine)  

    Base.metadata.create_all(engine)
