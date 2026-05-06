#!/usr/bin/env bash
# exit on error
set -o errexit

# Install dependencies
pip install -r requirements.txt

# Create migrations for voidauth (just in case)
python manage.py makemigrations voidauth

# Run migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --no-input
