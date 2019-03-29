FROM python:2.7-alpine

WORKDIR /app

RUN apk update && apk add --no-cache \
  py-psycopg2 \
  postgresql-dev \
  #py2-gevent \
  uwsgi-gevent \
  py2-greenlet

COPY . ./
RUN pip install -r requirements.txt

#ENTRYPOINT ["gunicorn", "--config gunicorn_config.py", "wsgi:app"]
