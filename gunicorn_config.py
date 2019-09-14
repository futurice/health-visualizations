import gevent.monkey
import psycogreen.gevent
import os

# Enable gevent for PSQL
gevent.monkey.patch_all()
psycogreen.gevent.patch_psycopg()


def port():
    return os.environ.get('PORT') or '8000'


# ### Gunicorn settings BEGIN
bind = [':' + port()]
loglevel = 'warning'
worker_class = 'gevent'
# ### Gunicorn settings END
