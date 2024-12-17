"""honeybee-openstudio translation commands."""
import sys
import logging
import click

from ladybug.commandutil import process_content_to_output
from honeybee.model import Model

_logger = logging.getLogger(__name__)


@click.group(help='Commands for translating between Honeybee and OpenStudio.')
def translate():
    pass


@translate.command('model-to-osm')
@click.argument('model-file', type=click.Path(
    exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.option(
    '--output-file', '-o', help='Optional OSM file path to output the OSM string '
    'of the translation. By default this will be printed to stdout.',
    type=click.File('w'), default='-', show_default=True)
def model_to_osm_cli(model_file, output_file):
    """Translate a Honeybee Model to an OSM file.

    \b
    Args:
        model_file: Full path to a Honeybee Model file (HBJSON or HBpkl).
    """
    try:
        model_to_osm(model_file, output_file)
    except Exception as e:
        _logger.exception(f'Model translation failed:\n{e}')
        sys.exit(1)
    else:
        sys.exit(0)


def model_to_osm(model_file, output_file=None):
    """Translate a Honeybee Model to an OSM file.

    Args:
        model_file: Full path to a Honeybee Model file (HBJSON or HBpkl).
        output_file: Optional OSM file path to output the OSM string of the
            translation. If None, the string will be returned from this function.
    """
    model = Model.from_file(model_file)
    os_model = model.to.openstudio(model)
    return process_content_to_output(str(os_model), output_file)
