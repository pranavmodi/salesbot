web: gunicorn --bind 0.0.0.0:$PORT run:app --timeout 120 --workers 2
release: alembic upgrade head