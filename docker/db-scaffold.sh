#!/bin/sh

export ALIGULAC_EXPOSE_DB_PORT=5432
export PGPASSWORD=aligulac

# Delete existing database
sudo rm -rf data/*

# Spin up the database
docker compose up -d db

# Let django do all the migrations it needs for apps that are only of use to the
# legacy server. We will handle the schema ourselves for the other apps.
docker compose run --rm legacy python3 manage.py migrate admin
docker compose run --rm legacy python3 manage.py migrate auth
docker compose run --rm legacy python3 manage.py migrate sessions
docker compose run --rm legacy python3 manage.py migrate tastypie

# Apply the migrations from the other schemas. This brings the database to a
# point where it's compatible with the legacy data dump.
uv --directory ../backend run alembic upgrade e732a2e373c3

# Import data from the legacy server
psql -h localhost -p 5432 -d aligulac -U aligulac -f data.sql -w -v ON_ERROR_STOP=1

# Apply migrations after the legacy point
uv --directory ../backend run alembic upgrade head

# Take the database down again
docker compose down
