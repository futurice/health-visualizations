#!/bin/bash

#docker run --rm -e "DATABASE_URL=todo-fill" health-visualizations
#docker run --rm -it -p 8000:8000 -e "DATABASE_URL=todo-fill" health-visualizations /bin/bash
docker run --rm -it -p 8000:8000 -e "DATABASE_URL=todo-fill" health-visualizations
