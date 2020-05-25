import click
import asyncio
from models.user import create_user

def run_async(coro):
    asyncio.run(coro)

@click.group()
def cli():
    ...

async def _adduser(**kwargs):
    try:
        user = await create_user(**kwargs)
    except Exception as e:
        print(e)
        click.echo(str(e))
    else:
        click.echo(f'User {user.name} created!!! ID: {user.id}')

@cli.command()
@click.option('--name', required=True, prompt=True)
@click.option('--email', required=False, default=None, prompt=True)
@click.option('--password', required=True, prompt=True, hide_input=True,
              confirmation_prompt=True)
def adduser(name, email, password):
    run_async(_adduser(name=name, password=password, email=email))

if __name__ == '__main__':
    cli()