set -x
alembic revision --autogenerate -m 'message'
alembic upgrade head