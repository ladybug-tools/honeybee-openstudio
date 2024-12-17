"""Test the CLI commands"""
import os
from click.testing import CliRunner

from honeybee_openstudio.cli.translate import model_to_osm_cli


def test_model_to_osm_cli():
    """Test the translation of a Model to OSM."""
    runner = CliRunner()
    input_hb_model = './tests/assets/2023_rac_advanced_sample_project.hbjson'
    out_file = './tests/assets/2023_rac_advanced_sample_project.osm'

    in_args = [input_hb_model, '--output-file', out_file]
    result = runner.invoke(model_to_osm_cli, in_args)

    assert result.exit_code == 0
    assert os.path.isfile(out_file)
    os.remove(out_file)
