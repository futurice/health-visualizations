#import gevent.monkey
#import psycogreen.gevent

# Enable gevent for PSQL
#gevent.monkey.patch_all()
#psycogreen.gevent.patch_psycopg()

# ### Gunicorn settings BEGIN
bind = [':5000']
loglevel = 'warning'
worker_class = 'sync'
# ### Gunicorn settings END
