# Lääketutka backend

This repository contains the backend for [Lääketutka](https://www.laaketutka.fi). You also need the [frontend](https://github.com/futurice/health-visualizations-front).

### Prerequisites

See [related repository](https://github.com/futurice/laaketutka-prereqs) for how to produce the following files:

* `data.json`
* `drugs_stemmed.txt`
* `symptoms_three_ways.txt`

### Set up

* Python 2
* flask
* sqlalchemy
* [Azure commend line tools](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli?view=azure-cli-latest)
* Postgres DB
    * Set env variables `$PSQL_USERNAME`, `$PSQL_PASSWORD` and `$PSQL_DB`

### Prepare the database

Create and populate the database with `associations.py`.

See [instructions](UPDATE_DB.md) for updating the production database.

### Local development

```bash
sudo apt-get install python-psycopg2
pip install -r requirements.txt -r requirements_dev.txt
```

### Run in Docker

```bash
./build_docker.sh

export DATABASE_URL=postgres://<user>:<password>@<host>/<dbname>
./run_in_docker.sh
```

Open [localhost:8000/drug](http://localhost:8000/drugs).

## Deployment

```bash
az login
az acr login --name laaketutka

./build_docker.sh

# staging
docker tag health-visualizations laaketutka.azurecr.io/health-visualizations:staging
docker push laaketutka.azurecr.io/health-visualizations:staging

# prod
docker tag health-visualizations laaketutka.azurecr.io/health-visualizations
docker push laaketutka.azurecr.io/health-visualizations
```

See [AzureDeployInstructions.md](AzureDeployInstructions.md) for more information.