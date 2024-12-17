"""honeybee-openstudio commands which will be added to the honeybee cli"""
import click
from honeybee.cli import main


@click.group(help='honeybee openstudio commands.')
@click.version_option()
def openstudio():
    pass


# add openstudio sub-commands
main.add_command(openstudio)
