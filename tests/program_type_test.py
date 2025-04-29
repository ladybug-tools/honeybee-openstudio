# coding=utf-8
"""Test the translators for ConstructionSets to OpenStudio."""
from honeybee_energy.lib.programtypes import office_program
import honeybee_energy.lib.scheduletypelimits as schedule_types

from honeybee_openstudio.openstudio import OSModel
from honeybee_openstudio.schedule import schedule_to_openstudio, \
    schedule_type_limits_to_openstudio, extract_all_schedules
from honeybee_openstudio.programtype import program_type_to_openstudio, \
    program_type_from_openstudio


def test_program_type_to_openstudio():
    """Test the translation of ProgramType to OpenStudio."""
    os_model = OSModel()
    os_model.setDayofWeekforStartDay('Sunday')  # this avoids lots of warnings

    for schedule in office_program.schedules_unique:
        schedule_to_openstudio(schedule, os_model)

    os_space_type = program_type_to_openstudio(office_program, os_model)
    assert str(os_space_type.name()) == 'Generic Office Program'
    os_space_type_str = str(os_space_type)
    assert os_space_type_str.startswith('OS:SpaceType,')


def test_program_type_from_openstudio():
    """Test the translation of ProgramType from OpenStudio."""
    os_model = OSModel()
    os_model.setDayofWeekforStartDay('Sunday')  # this avoids lots of warnings
    schedule_type_limits_to_openstudio(schedule_types.fractional, os_model)
    for schedule in office_program.schedules_unique:
        schedule_to_openstudio(schedule, os_model)
    os_space_type = program_type_to_openstudio(office_program, os_model)

    schedules = extract_all_schedules(os_model)
    rebuilt_program = program_type_from_openstudio(os_space_type, schedules)

    ppld = office_program.people.people_per_area
    assert ppld - 0.001 < rebuilt_program.people.people_per_area < ppld + 0.001
    assert office_program.people.occupancy_schedule.identifier == \
        rebuilt_program.people.occupancy_schedule.identifier

    lpd = office_program.lighting.watts_per_area
    assert lpd - 0.001 < rebuilt_program.lighting.watts_per_area < lpd + 0.001
    assert office_program.lighting.schedule.identifier == \
        rebuilt_program.lighting.schedule.identifier

    epd = office_program.electric_equipment.watts_per_area
    assert epd - 0.001 < rebuilt_program.electric_equipment.watts_per_area < epd + 0.001
    assert office_program.electric_equipment.schedule.identifier == \
        rebuilt_program.electric_equipment.schedule.identifier

    fd = office_program.infiltration.flow_per_exterior_area
    assert fd - 0.001 < rebuilt_program.infiltration.flow_per_exterior_area < fd + 0.001
    assert office_program.infiltration.schedule.identifier == \
        rebuilt_program.infiltration.schedule.identifier

    fpp = office_program.ventilation.flow_per_person
    fpa = office_program.ventilation.flow_per_area
    assert fpp - 0.00001 < rebuilt_program.ventilation.flow_per_person < fpp + 0.00001
    assert fpa - 0.00001 < rebuilt_program.ventilation.flow_per_area < fpa + 0.00001
