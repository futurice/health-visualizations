#!/bin/bash

if [ -z "$DATABASE_URL" ]; then
    echo "Set the database URL first: export DATABASE_URL=..."
    exit 1
fi

#docker run --rm -it -p 8000:8000 -e "DATABASE_URL=$DATABASE_URL" health-visualizations /bin/bash
docker run --rm -it -p 8000:8000 -e "DATABASE_URL=$DATABASE_URL" health-visualizations
