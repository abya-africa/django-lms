#!/bin/bash
python manage.py tailwind start
python manage.py makemigrations
python manage.py migrate
python manage.py runserver  0.0.0.0:8001
