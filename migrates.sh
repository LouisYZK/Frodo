set -x
alembic revision --autogenerate -m 'message'
alembic upgrade head

# alter table post convert to character set utf8;