FROM python:2.7

RUN useradd -m appuser

WORKDIR /app

COPY . ./
RUN pip install -r requirements.txt

EXPOSE 8000
USER appuser
ENTRYPOINT ["gunicorn", "--config", "gunicorn_config.py", "wsgi:app"]
