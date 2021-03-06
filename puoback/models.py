from __future__ import print_function

import math
import sys
import os

import sqlalchemy as sa
from sqlalchemy import Column, Integer, Text, Index, String, and_, func, BigInteger
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import JSON, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, aliased, query
from sqlalchemy import Table, Column, Integer, ForeignKey
from sqlalchemy.orm import relationship

from puoback import db

# Page size for sample quotes
PAGE_SIZE = 20


# For debugging, prints raw SQL query produced by SQLAlchemy
def print_query(q):
    print(str(q.statement.compile(dialect=postgresql.dialect())), file=sys.stderr)


# Helper method for Post.find_related_quotes()
def query_builder(session, res1, res2):
    if Drug == type(res1):
        Table1 = Bridge_Drug_Post
        condition1 = Table1.drug_id == res1.id
    else:
        Table1 = Bridge_Symptom_Post
        condition1 = Table1.symptom_id == res1.id
    if Drug == type(res2):
        Table2 = aliased(Bridge_Drug_Post)
        condition2 = Table2.drug_id == res2.id
    else:
        Table2 = aliased(Bridge_Symptom_Post)
        condition2 = Table2.symptom_id == res2.id
    return session.query(Table1.post_id)\
        .join(Table2, Table1.post_id == Table2.post_id)\
        .filter(and_(condition1, condition2))

class Post(db.Model):
    __tablename__ = 'posts'

    id = Column(BigInteger, primary_key=True)
    url = Column(Text, unique=False)
    original = Column(Text, unique=False)
    lemmatized = Column(Text, unique=False)

    @staticmethod
    def get_page_count(query):
        count_q = query.statement.with_only_columns([func.count()]).order_by(None)
        # print(str(count_q.compile(dialect=postgresql.dialect())), file=sys.stderr)
        total_count = query.session.execute(count_q).scalar()
        page_count = int(math.ceil(1.0 * total_count / PAGE_SIZE))
        return page_count

    @staticmethod
    def get_page_posts(query, page):
        return (
            query
                .offset((int(page) - 1) * PAGE_SIZE)
                .limit(PAGE_SIZE)
        )

    @staticmethod
    def find_page_count(db_session, res1, res2):
        return Post.get_page_count(query_builder(db_session, res1, res2))

    @staticmethod
    def find_keyword_quotes(db_session, res, page):
        if Drug == type(res):
            Table = Bridge_Drug_Post
            condition = Table.drug_id == res.id
        else:
            Table = Bridge_Symptom_Post
            condition = Table.symptom_id == res.id

        q = db_session.query(Table.post_id).filter(condition)
        page_count = Post.get_page_count(q)
        sq = Post.get_page_posts(q, page).subquery()
        page_posts = (
            db_session
                .query(Post.url, Post.original)
                .join(sq, sq.c.post_id == Post.id)
                .all()
        )
        return page_posts, page_count


    @staticmethod
    def find_related_quotes(db_session, res1, res2, page):
        q = query_builder(db_session, res1, res2)
        page_count = Post.get_page_count(q)
        sq = Post.get_page_posts(q, page).subquery()
        page_posts = (
            db_session
            .query(Post.url, Post.original)
            .join(sq, sq.c.post_id == Post.id)
            .all()
        )
        #print_query(page_posts)
        return page_posts, page_count

    @staticmethod
    def find_dosage_quotes(db_session, drug_name, dosage, page):
        drug = Drug.find_drug(db_session, drug_name)
        bridge_q = (
            db_session
            .query(Post.url, Post.original)
            .join(Bridge_Dosage_Quote, Post.id == Bridge_Dosage_Quote.post_id)
            .filter(and_(Bridge_Dosage_Quote.drug_id == drug.id,
                         Bridge_Dosage_Quote.dosage_mg == dosage))
        )
        return Post.get_page_posts(bridge_q, page).all(), Post.get_page_count(bridge_q)

class Drug(db.Model):
    __tablename__ = 'drugs'
    id = Column(BigInteger, primary_key=True)
    name = Column(Text, unique=True)
    data = Column(JSONB)

    @staticmethod
    def find_drug(db_session, search_term):
        return db_session.query(Drug).join(Search_Term, Search_Term.drug_id == Drug.id).filter(Search_Term.name == search_term).one()

class Symptom(db.Model):
    __tablename__ = 'symptoms'
    id = Column(BigInteger, primary_key=True)
    name = Column(Text, unique=True)
    data = Column(JSONB)

    @staticmethod
    def find_symptom(db_session, search_term):
        return db_session.query(Symptom).join(Search_Term, Search_Term.symptom_id == Symptom.id).filter(Search_Term.name == search_term).one()

class Search_Term(db.Model):
    __tablename__ = 'search_terms'
    id = Column(BigInteger, primary_key=True)
    name = Column(String(64), nullable=False, unique=True)
    drug_id = Column(BigInteger, ForeignKey('drugs.id'), nullable=True)
    symptom_id = Column(BigInteger, ForeignKey('symptoms.id'), nullable=True)

    ref_drug = relationship(Drug, backref="search_terms")
    ref_symptom = relationship(Symptom, backref="search_terms")

    @staticmethod
    def find_drug_or_symptom(db_session, search_term):
        res = db_session.query(Search_Term).filter(Search_Term.name == search_term).one()
        if res.drug_id is not None:
            return db_session.query(Drug).filter(Drug.id == res.drug_id).one()
        else:
            return db_session.query(Symptom).filter(Symptom.id == res.symptom_id).one()

class Bridge_Dosage_Quote(db.Model):
    __tablename__ = 'bridge_dosage_quotes'

    id = Column(BigInteger, primary_key=True)
    post_id = Column(BigInteger, ForeignKey('posts.id'))
    drug_id = Column(BigInteger, ForeignKey('drugs.id'))
    dosage_mg = Column(BigInteger)

    ref_post = relationship(Post, backref="bridge_dosage_quotes")
    ref_drug = relationship(Drug, backref="bridge_dosage_quotes")

class Bridge_Drug_Post(db.Model):
    __tablename__ = 'bridge_drug_posts'

    id = Column(BigInteger, primary_key=True)
    post_id = Column(BigInteger, ForeignKey('posts.id'))
    drug_id = Column(BigInteger, ForeignKey('drugs.id'))

    ref_post = relationship(Post, backref="bridge_drug_posts")
    ref_drug = relationship(Drug, backref="bridge_drug_posts")


class Bridge_Symptom_Post(db.Model):
    __tablename__ = 'bridge_symptom_posts'

    id = Column(BigInteger, primary_key=True)
    post_id = Column(BigInteger, ForeignKey('posts.id'))
    symptom_id = Column(BigInteger, ForeignKey('symptoms.id'))

    ref_post = relationship(Post, backref="bridge_symptom_posts")
    ref_symptom = relationship(Symptom, backref="bridge_symptom_posts")


def create_index(index_name, table_field):
    try:
        idx = Index(index_name, table_field)
        idx.create(bind=db.engine)
        print('Creating index', index_name)
    except:
        print('Skipping ', index_name)
        pass


def create_indexes(confirm=False):
    # Create indexes if they don't exist
    if confirm or input("Create indexes? For performance reasons it should be done AFTER tables have been populated. Enter y/n: ") == "y":
        create_index('posts_idx', Post.id)
        create_index('bridge_drug_post_id_idx', Bridge_Drug_Post.id)
        create_index('bridge_drug_post_post_id_idx', Bridge_Drug_Post.post_id)
        create_index('bridge_drug_post_drug_id_idx', Bridge_Drug_Post.drug_id)
        create_index('bridge_symptom_post_id_idx', Bridge_Symptom_Post.id)
        create_index('bridge_symptom_post_post_id_idx', Bridge_Symptom_Post.post_id)
        create_index('bridge_symptom_post_symptom_id_idx', Bridge_Symptom_Post.symptom_id)
        create_index('search_terms_index', Search_Term.name)
        create_index('search_terms_index_drug_id', Search_Term.drug_id)
        create_index('search_terms_index_symptom_id', Search_Term.symptom_id)


def initialize_db():
    PSQL_DB = os.environ['PSQL_DB']
    if input("Drop previous database schema and all data from " + PSQL_DB + "? Enter y/n: ") == "y":
        db.drop_all()
    # Create / update schema
    db.create_all()
