FROM python:2.7-alpine

WORKDIR /app

RUN apk update && apk add --no-cache py-psycopg2
RUN apk add postgresql-dev
RUN apk add py2-gevent
RUN apk add py2-greenlet

COPY . ./
RUN pip install -r requirements.txt

ENTRYPOINT ["gunicorn", "--config gunicorn_config.py", "wsgi:app"]
