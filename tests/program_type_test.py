# coding=utf-8
"""Test the translators for ConstructionSets to OpenStudio."""
from honeybee_energy.lib.programtypes import office_program

from honeybee_openstudio.openstudio import OSModel
from honeybee_openstudio.schedule import schedule_to_openstudio
from honeybee_openstudio.programtype import program_type_to_openstudio


def test_program_type_to_openstudio():
    """Test the translation of People to OpenStudio."""
    os_model = OSModel()
    os_model.setDayofWeekforStartDay('Sunday')  # this avoids lots of warnings

    for schedule in office_program.schedules_unique:
        schedule_to_openstudio(schedule, os_model)

    os_space_type = program_type_to_openstudio(office_program, os_model)
    assert str(os_space_type.name()) == 'Generic Office Program'
    os_space_type_str = str(os_space_type)
    assert os_space_type_str.startswith('OS:SpaceType,')
