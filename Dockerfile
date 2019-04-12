FROM python:2.7

WORKDIR /app

COPY . ./
RUN pip install -r requirements.txt

EXPOSE 8000
ENTRYPOINT ["gunicorn", "--bind", "0.0.0.0:8000", "--config", "gunicorn_config.py", "wsgi:app"]
