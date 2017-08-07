import functools
from contextlib import contextmanager


@contextmanager
def db_session(db):
    try:
        yield db.session
        db.session.commit()
    except:
        db.session.rollback()
        raise
    finally:
        db.session.close()
