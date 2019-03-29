#!/bin/bash

#docker run --rm -e "DATABASE_URL=todo-fill" health-visualizations
docker run --rm -it -e "DATABASE_URL=todo-fill" health-visualizations /bin/sh
