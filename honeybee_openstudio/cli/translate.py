"""honeybee-openstudio translation commands."""
import sys
import logging
import click
import os
import time

import openstudio

from ladybug.commandutil import process_content_to_output
from honeybee.model import Model
from honeybee.config import folders

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
        start = time.time()
        model_to_osm(model_file, output_file)
        end = time.time()
        print('Runtime {} Minutes'.format(float(end - start) / 60))
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
    print('Writing OSM to file')
    t_start = time.time()
    if output_file is not None and 'stdout' not in str(output_file):
        output_file = output_file.name \
            if not isinstance(output_file, str) else output_file
        os_model.save(output_file, overwrite=True)
        t_end = time.time()
        print('OSM written - time {}'.format(t_end - t_start))
    else:
        output = process_content_to_output(str(os_model), output_file)
        t_end = time.time()
        print('OSM written - time {}'.format(t_end - t_start))
        return output


@translate.command('osm-to-idf')
@click.argument('osm-file', type=click.Path(
    exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.option(
    '--output-file', '-o', help='Optional IDF file path to output the IDF string '
    'of the translation. By default this will be printed to stdout.',
    type=click.File('w'), default='-', show_default=True)
def osm_to_idf_cli(osm_file, output_file):
    """Translate a OSM file to an IDF file.

    \b
    Args:
        osm_file: Full path to a OpenStudio Model file (OSM).
    """
    try:
        start = time.time()
        osm_to_idf(osm_file, output_file)
        end = time.time()
        print('Runtime {} Minutes'.format(float(end - start) / 60))
    except Exception as e:
        _logger.exception(f'Model translation failed:\n{e}')
        sys.exit(1)
    else:
        sys.exit(0)


def osm_to_idf(osm_file, output_file=None):
    """Translate a Honeybee Model to an OSM file.

    Args:
        osm_file: Full path to an OpenStudio Model file (OSM).
        output_file: Optional IDF file path to output the IDF string of the
            translation. If None, the string will be returned from this function.
    """
    # load the model object from the OSM file
    print('Loading Model from OSM')
    l_start = time.time()
    exist_os_model = openstudio.model.Model.load(osm_file)
    if exist_os_model.is_initialized():
        os_model = exist_os_model.get()
    else:
        raise ValueError(
            'The file at "{}" does not appear to be an OpenStudio model.'.format(
                osm_file
            ))
    l_end = time.time()
    print('Model loaded from OSM - time {}'.format(l_end - l_start))

    # translate the OpenStudio model to an IDF file
    print('Translating OSM to IDF')
    t_start = time.time()
    idf_translator = openstudio.energyplus.ForwardTranslator()
    workspace = idf_translator.translateModel(os_model)
    t_end = time.time()
    print('Translation complete - time {}'.format(t_end - t_start))

    # write the IDF file
    print('Writing IDF to file')
    w_start = time.time()
    if output_file is None:
        idf = os.path.join(folders.default_simulation_folder, 'temp_translate', 'in.idf')
    elif not isinstance(output_file, str):
        idf = output_file.name
    workspace.save(idf, overwrite=True)
    w_end = time.time()
    print('IDF written - time {}'.format(w_end - w_start))


@translate.command('append-to-osm')
@click.argument('osm-file', type=click.Path(
    exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.argument('model-file', type=click.Path(
    exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.option(
    '--output-file', '-o', help='Optional OSM file path to output the OSM string '
    'of the translation. By default this will be printed to stdout.',
    type=click.File('w'), default='-', show_default=True)
def append_to_osm_cli(osm_file, model_file, output_file):
    """Append a Honeybee Model to a OSM file.

    \b
    Args:
        osm_file: Full path to a OpenStudio Model file (OSM).
        model_file: Full path to a Honeybee Model file (HBJSON or HBpkl).
    """
    try:
        start = time.time()
        append_to_osm(osm_file, model_file, output_file)
        end = time.time()
        print('Runtime {} Minutes'.format(float(end - start) / 60))
    except Exception as e:
        _logger.exception(f'Model appending failed:\n{e}')
        sys.exit(1)
    else:
        sys.exit(0)


def append_to_osm(osm_file, model_file, output_file=None):
    """Append a Honeybee Model to a OSM file.

    Args:
        osm_file: Full path to an OpenStudio Model file (OSM).
        model_file: Full path to a Honeybee Model file (HBJSON or HBpkl).
        output_file: Optional IDF file path to output the IDF string of the
            translation. If None, the string will be returned from this function.
    """
    # load the model object from the OSM file
    print('Loading Model from OSM')
    l_start = time.time()
    exist_os_model = openstudio.model.Model.load(osm_file)
    if exist_os_model.is_initialized():
        os_model = exist_os_model.get()
    else:
        raise ValueError(
            'The file at "{}" does not appear to be an OpenStudio model.'.format(
                osm_file
            ))
    l_end = time.time()
    print('Model loaded from OSM - time {}'.format(l_end - l_start))

    # load the honeybee Model object
    model = Model.from_file(model_file)

    # append the honeybee model to the OSM
    print('Appending Honeybee to OSM')
    t_start = time.time()
    os_model = model.to.openstudio(model, os_model)
    t_end = time.time()
    print('Appending complete - time {}'.format(t_end - t_start))

    # write the OSM file
    print('Writing OSM to file')
    w_start = time.time()
    if output_file is not None and 'stdout' not in str(output_file):
        output_file = output_file.name \
            if not isinstance(output_file, str) else output_file
        os_model.save(output_file, overwrite=True)
        w_end = time.time()
        print('OSM written - time {}'.format(w_end - w_start))
    else:
        output = process_content_to_output(str(os_model), output_file)
        w_end = time.time()
        print('OSM written - time {}'.format(w_end - w_start))
        return output
