import contextvars

aio_databases = contextvars.ContextVar('databases')
redis_var = contextvars.ContextVar('redis')