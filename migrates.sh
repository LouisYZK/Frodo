set -x
export PYTHONPATH=.
alembic init alembic
alembic revision --autogenerate -m 'message'
alembic upgrade head

# alter table post convert to character set utf8;