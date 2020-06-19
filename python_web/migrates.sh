set -x
export PYTHONPATH=.
cd alembic
mkdir versions 
alembic init alembic
alembic revision --autogenerate -m 'message'
alembic upgrade head

# alter table post convert to character set utf8;