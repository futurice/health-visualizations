from __future__ import print_function

import math
import sys

import sqlalchemy as sa
from sqlalchemy import Column, Integer, Text, Index, String, and_, func
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
def query_builder(session, Table1, Table2, condition1, condition2):
    return session.query(Table1.post_id)\
        .join(Table2, Table1.post_id == Table2.post_id)\
        .filter(and_(condition1, condition2))\
        .subquery()

def get_count(q):
    count_q = q.statement.with_only_columns([func.count()]).order_by(None)
    print(str(count_q.compile(dialect=postgresql.dialect())), file=sys.stderr)
    count = q.session.execute(count_q).scalar()
    return count

class Post(db.Model):
    __tablename__ = 'posts'

    # Change all primary IDs to BigInteger
    id = Column(Integer, primary_key=True)
    original = Column(Text, unique=False)
    lemmatized = Column(Text, unique=False)

    @staticmethod
    def find_page_count(db_session, res1, res2):
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
        sq = query_builder(db_session, Table1, Table2, condition1, condition2)
        all_posts_query = (
            db_session
                .query(Post.original)
                .join(sq, sq.c.post_id == Post.id)
        )
        page_count = math.ceil(get_count(all_posts_query) / PAGE_SIZE)
        return page_count

    @staticmethod
    def find_related_quotes(db_session, res1, res2, page):
        page = int(page)
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

        sq = query_builder(db_session, Table1, Table2, condition1, condition2)
        all_posts_query = (
            db_session
            .query(Post.original)
            .join(sq, sq.c.post_id == Post.id)
        )
        page_count = int(math.ceil(get_count(all_posts_query) / PAGE_SIZE))
        paginated_posts = (
            all_posts_query
            .offset((page - 1) * PAGE_SIZE)
            .limit(PAGE_SIZE)
            )
        #print_query(posts)
        return paginated_posts.all(), page_count

    @staticmethod
    def find_dosage_quotes(db_session, drug_name, dosage, page):
        page = int(page)
        drug = Drug.find_drug(db_session, drug_name)
        bridge_q = (
            db_session
            .query(Bridge_Dosage_Quote)
            .filter(and_(Bridge_Dosage_Quote.drug_id == drug.id,
                         Bridge_Dosage_Quote.dosage_mg == dosage))
        )
        page_count = int(math.ceil(get_count(bridge_q) / PAGE_SIZE))

        bridges = (
            bridge_q
                .offset((page - 1) * PAGE_SIZE)
                .limit(PAGE_SIZE)
                .all()
        )
        post_ids = [bridge.post_id for bridge in bridges]
        post_originals = db_session.query(Post.original).filter(Post.id.in_(post_ids))
        return [x for x in post_originals]  # query to list

class Drug(db.Model):
    __tablename__ = 'drugs'
    id = Column(Integer, primary_key=True)
    name = Column(Text, unique=True)
    data = Column(JSONB)

    @staticmethod
    def find_drug(db_session, search_term):
        return db_session.query(Drug).join(Search_Term, Search_Term.drug_id == Drug.id).filter(Search_Term.name == search_term).one()

class Symptom(db.Model):
    __tablename__ = 'symptoms'
    id = Column(Integer, primary_key=True)
    name = Column(Text, unique=True)
    data = Column(JSONB)

    @staticmethod
    def find_symptom(db_session, search_term):
        return db_session.query(Symptom).join(Search_Term, Search_Term.symptom_id == Symptom.id).filter(Search_Term.name == search_term).one()

class Search_Term(db.Model):
    __tablename__ = 'search_terms'
    id = Column(Integer, primary_key=True)
    name = Column(String(64), nullable=False, unique=True)
    drug_id = Column(Integer, ForeignKey('drugs.id'), nullable=True)
    symptom_id = Column(Integer, ForeignKey('symptoms.id'), nullable=True)

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

    id = Column(Integer, primary_key=True)
    post_id = Column(Integer, ForeignKey('posts.id'))
    drug_id = Column(Integer, ForeignKey('drugs.id'))
    dosage_mg = Column(Integer)

    ref_post = relationship(Post, backref="bridge_dosage_quotes")
    ref_drug = relationship(Drug, backref="bridge_dosage_quotes")

# class Bridge_Count_Related(db.Model):
#     __tablename__ = 'bridge_count_related'

#     id = Column(Integer, primary_key=True)
#     #drug1
#     #drug2
#     #symptom1
#     #symptom2

#     "d548s942"
#     count = Column(Integer)


class Bridge_Drug_Post(db.Model):
    __tablename__ = 'bridge_drug_posts'

    id = Column(Integer, primary_key=True)
    post_id = Column(Integer, ForeignKey('posts.id'))
    drug_id = Column(Integer, ForeignKey('drugs.id'))

    ref_post = relationship(Post, backref="bridge_drug_posts")
    ref_drug = relationship(Drug, backref="bridge_drug_posts")


class Bridge_Symptom_Post(db.Model):
    __tablename__ = 'bridge_symptom_posts'

    id = Column(Integer, primary_key=True)
    post_id = Column(Integer, ForeignKey('posts.id'))
    symptom_id = Column(Integer, ForeignKey('symptoms.id'))

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
    if confirm or raw_input("Create indexes? For performance reasons it should be done AFTER tables have been populated. Enter y/n: ") == "y":
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
    if raw_input("Drop previous database schema and all data from " + PSQL_DB + "? Enter y/n: ") == "y":
        db.drop_all()
    # Create / update schema
    db.create_all()


if __name__ == "__main__":
    initialize_db()
    create_indexes()
