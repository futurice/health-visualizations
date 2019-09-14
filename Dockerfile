FROM python:2.7

WORKDIR /app

COPY . ./
RUN pip install -r requirements.txt

EXPOSE 8000
ENTRYPOINT ["gunicorn", "--config", "gunicorn_config.py", "wsgi:app"]
