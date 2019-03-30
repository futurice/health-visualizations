FROM python:2.7

WORKDIR /app

#RUN apt-get update && apt-get install -y \
  #python-psycopg2 \
  #postgresql-dev \
  #python-gevent \
  #uwsgi-gevent \
  #python-greenlet

COPY . ./
RUN pip install -r requirements.txt

EXPOSE 8000
ENTRYPOINT ["gunicorn", "--config", "gunicorn_config.py", "wsgi:app"]
