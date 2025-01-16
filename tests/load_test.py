# coding=utf-8
"""Test the translators for loads to OpenStudio."""
from ladybug.dt import Time
from honeybee.room import Room
from honeybee_energy.load.people import People
from honeybee_energy.load.lighting import Lighting
from honeybee_energy.load.equipment import ElectricEquipment, GasEquipment
from honeybee_energy.load.process import Process
from honeybee_energy.load.hotwater import ServiceHotWater
from honeybee_energy.load.infiltration import Infiltration
from honeybee_energy.load.ventilation import Ventilation
from honeybee_energy.load.setpoint import Setpoint
from honeybee_energy.schedule.day import ScheduleDay
from honeybee_energy.schedule.rule import ScheduleRule
from honeybee_energy.schedule.ruleset import ScheduleRuleset
import honeybee_energy.lib.scheduletypelimits as schedule_types
from honeybee_energy.lib.programtypes import office_program

from honeybee_openstudio.openstudio import OSModel
from honeybee_openstudio.schedule import schedule_to_openstudio
from honeybee_openstudio.load import people_to_openstudio, lighting_to_openstudio, \
    electric_equipment_to_openstudio, gas_equipment_to_openstudio, \
    process_to_openstudio, hot_water_to_openstudio, \
    infiltration_to_openstudio, ventilation_to_openstudio, \
    setpoint_to_openstudio_thermostat, setpoint_to_openstudio_humidistat


def test_people_to_openstudio():
    """Test the translation of People to OpenStudio."""
    os_model = OSModel()
    os_model.setDayofWeekforStartDay('Sunday')  # this avoids lots of warnings
    weekday_office = ScheduleDay('Weekday Office Occupancy', [0, 1, 0],
                                 [Time(0, 0), Time(9, 0), Time(17, 0)])
    saturday_office = ScheduleDay('Saturday Office Occupancy', [0, 0.25, 0],
                                  [Time(0, 0), Time(9, 0), Time(17, 0)])
    weekend_rule = ScheduleRule(saturday_office)
    weekend_rule.apply_weekend = True
    occ_schedule = ScheduleRuleset('Office Occupancy', weekday_office,
                                   [weekend_rule], schedule_types.fractional)
    people = People('Open Office Zone People', 0.05, occ_schedule)

    schedule_to_openstudio(occ_schedule, os_model)

    os_people = people_to_openstudio(people, os_model)
    assert str(os_people.name()) == 'Open Office Zone People'
    os_people_str = str(os_people)
    assert os_people_str.startswith('OS:People,')


def test_lighting_to_openstudio():
    """Test the translation of Lighting to OpenStudio."""
    os_model = OSModel()
    os_model.setDayofWeekforStartDay('Sunday')  # this avoids lots of warnings
    weekday_office = ScheduleDay('Weekday Office Lighting', [0, 1, 0],
                                 [Time(0, 0), Time(9, 0), Time(17, 0)])
    saturday_office = ScheduleDay('Saturday Office Lighting', [0, 0.25, 0],
                                  [Time(0, 0), Time(9, 0), Time(17, 0)])
    weekend_rule = ScheduleRule(saturday_office)
    weekend_rule.apply_weekend = True
    schedule = ScheduleRuleset('Office Lighting', weekday_office,
                               [weekend_rule], schedule_types.fractional)
    lighting = Lighting('Open Office Zone Lighting', 10, schedule)

    schedule_to_openstudio(schedule, os_model)

    os_lighting = lighting_to_openstudio(lighting, os_model)
    assert str(os_lighting.name()) == 'Open Office Zone Lighting'
    os_lighting_str = str(os_lighting)
    assert os_lighting_str.startswith('OS:Lights,')


def test_electric_equipment_to_openstudio():
    """Test the translation of ElectricEquipment to OpenStudio."""
    os_model = OSModel()
    os_model.setDayofWeekforStartDay('Sunday')  # this avoids lots of warnings
    weekday_office = ScheduleDay('Weekday Office Equip', [0, 1, 0],
                                 [Time(0, 0), Time(9, 0), Time(17, 0)])
    saturday_office = ScheduleDay('Saturday Office Equip', [0, 0.25, 0],
                                  [Time(0, 0), Time(9, 0), Time(17, 0)])
    weekend_rule = ScheduleRule(saturday_office)
    weekend_rule.apply_weekend = True
    schedule = ScheduleRuleset('Office Equip', weekday_office,
                               [weekend_rule], schedule_types.fractional)
    equipment = ElectricEquipment('Open Office Zone Equip', 10, schedule)

    schedule_to_openstudio(schedule, os_model)

    os_equipment = electric_equipment_to_openstudio(equipment, os_model)
    assert str(os_equipment.name()) == 'Open Office Zone Equip'
    os_equipment_str = str(os_equipment)
    assert os_equipment_str.startswith('OS:ElectricEquipment,')


def test_gas_equipment_to_openstudio():
    """Test the translation of GasEquipment to OpenStudio."""
    os_model = OSModel()
    os_model.setDayofWeekforStartDay('Sunday')  # this avoids lots of warnings
    simple_office = ScheduleDay('Simple Weekday', [0, 1, 0],
                                [Time(0, 0), Time(9, 0), Time(17, 0)])
    schedule = ScheduleRuleset('Kitchen Equip', simple_office,
                               None, schedule_types.fractional)
    equipment = GasEquipment('Kitchen Stove Equip', 8, schedule)

    schedule_to_openstudio(schedule, os_model)

    os_equipment = gas_equipment_to_openstudio(equipment, os_model)
    assert str(os_equipment.name()) == 'Kitchen Stove Equip'
    os_equipment_str = str(os_equipment)
    assert os_equipment_str.startswith('OS:GasEquipment,')


def test_process_to_openstudio():
    """Test the translation of Process to OpenStudio."""
    os_model = OSModel()
    os_model.setDayofWeekforStartDay('Sunday')  # this avoids lots of warnings
    fireplace = Process('Wood Burning Fireplace', 300,
                        office_program.people.occupancy_schedule, 'OtherFuel1')

    schedule_to_openstudio(office_program.people.occupancy_schedule, os_model)

    os_equipment = process_to_openstudio(fireplace, os_model)
    assert str(os_equipment.name()) == 'Wood Burning Fireplace'
    os_equipment_str = str(os_equipment)
    assert os_equipment_str.startswith('OS:OtherEquipment,')


def test_hot_water_to_openstudio():
    """Test the translation of ServiceHotWater to OpenStudio."""
    os_model = OSModel()
    os_model.setDayofWeekforStartDay('Sunday')  # this avoids lots of warnings
    room = Room.from_box('Office_Restroom', 5, 10, 3)
    simple_office = ScheduleDay('Simple Weekday', [0, 1, 0],
                                [Time(0, 0), Time(9, 0), Time(17, 0)])
    schedule = ScheduleRuleset('Office Water Use', simple_office,
                               None, schedule_types.fractional)
    shw = ServiceHotWater.from_watts_per_area('Office Hot Water', 10, schedule)

    schedule_to_openstudio(schedule, os_model)

    os_water_equip = hot_water_to_openstudio(shw, room, os_model)
    assert 'Office Hot Water' in str(os_water_equip.name())
    os_equipment_str = str(os_water_equip)
    assert os_equipment_str.startswith('OS:WaterUse:Equipment,')


def test_infiltration_to_openstudio():
    """Test the translation of Infiltration to OpenStudio."""
    os_model = OSModel()
    os_model.setDayofWeekforStartDay('Sunday')  # this avoids lots of warnings
    simple_lobby = ScheduleDay('Simple Weekday', [0, 1, 0],
                               [Time(0, 0), Time(9, 0), Time(17, 0)])
    schedule = ScheduleRuleset('Lobby Infiltration Schedule', simple_lobby,
                               None, schedule_types.fractional)
    infiltration = Infiltration('Lobby Infiltration', 0.0003, schedule)

    schedule_to_openstudio(schedule, os_model)

    os_infiltration = infiltration_to_openstudio(infiltration, os_model)
    assert str(os_infiltration.name()) == 'Lobby Infiltration'
    os_infiltration_str = str(os_infiltration)
    assert os_infiltration_str.startswith('OS:SpaceInfiltration:DesignFlowRate,')


def test_ventilation_to_openstudio():
    """Test the translation of Ventilation to OpenStudio."""
    os_model = OSModel()
    os_model.setDayofWeekforStartDay('Sunday')  # this avoids lots of warnings
    simple_office = ScheduleDay('Simple Weekday', [0, 1, 0],
                                [Time(0, 0), Time(9, 0), Time(17, 0)])
    schedule = ScheduleRuleset('Office Ventilation Schedule', simple_office,
                               None, schedule_types.fractional)
    ventilation = Ventilation('Office Ventilation', 0.0025, 0.0006, 0, 0, schedule)

    schedule_to_openstudio(schedule, os_model)

    os_ventilation = ventilation_to_openstudio(ventilation, os_model)
    assert str(os_ventilation.name()) == 'Office Ventilation'
    os_ventilation_str = str(os_ventilation)
    assert os_ventilation_str.startswith('OS:DesignSpecification:OutdoorAir,')


def test_setpoint_to_openstudio():
    """Test the translation of Setpoint to OpenStudio."""
    os_model = OSModel()
    os_model.setDayofWeekforStartDay('Sunday')  # this avoids lots of warnings
    heat_setpt = ScheduleRuleset.from_constant_value(
        'Office Heating', 21, schedule_types.temperature)
    cool_setpt = ScheduleRuleset.from_constant_value(
        'Office Cooling', 24, schedule_types.temperature)
    setpoint = Setpoint('Office Setpoint', heat_setpt, cool_setpt)

    schedule_to_openstudio(heat_setpt, os_model)
    schedule_to_openstudio(cool_setpt, os_model)

    os_setpoint = setpoint_to_openstudio_thermostat(setpoint, os_model)
    assert str(os_setpoint.name()) == 'Office Setpoint'
    os_setpoint_str = str(os_setpoint)
    assert os_setpoint_str.startswith('OS:ThermostatSetpoint:DualSetpoint,')


def test_setpoint_to_openstudio_humidity():
    """Test the translation of Setpoint with humidity setpoints to OpenStudio."""
    os_model = OSModel()
    os_model.setDayofWeekforStartDay('Sunday')  # this avoids lots of warnings
    simple_heat = ScheduleDay('Simple Weekday HtgSetp', [18, 21, 18],
                              [Time(0, 0), Time(9, 0), Time(17, 0)])
    simple_cool = ScheduleDay('Simple Weekday ClgSetp', [28, 24, 28],
                              [Time(0, 0), Time(9, 0), Time(17, 0)])
    heat_setpt = ScheduleRuleset('Office Heating', simple_heat,
                                 None, schedule_types.temperature)
    cool_setpt = ScheduleRuleset('Office Cooling', simple_cool,
                                 None, schedule_types.temperature)
    humid_setpt = ScheduleRuleset.from_constant_value(
        'Office Humid', 30, schedule_types.humidity)
    dehumid_setpt = ScheduleRuleset.from_constant_value(
        'Office Dehumid', 60, schedule_types.humidity)
    setpoint = Setpoint('Office Setpoint', heat_setpt, cool_setpt,
                        humid_setpt, dehumid_setpt)

    schedule_to_openstudio(heat_setpt, os_model)
    schedule_to_openstudio(cool_setpt, os_model)
    schedule_to_openstudio(humid_setpt, os_model)
    schedule_to_openstudio(dehumid_setpt, os_model)

    os_setpoint = setpoint_to_openstudio_thermostat(setpoint, os_model)
    assert str(os_setpoint.name()) == 'Office Setpoint'
    os_setpoint_str = str(os_setpoint)
    assert os_setpoint_str.startswith('OS:ThermostatSetpoint:DualSetpoint,')

    os_humidistat = setpoint_to_openstudio_humidistat(setpoint, os_model)
    assert str(os_humidistat.name()) == 'Office Setpoint'
    os_humidistat_str = str(os_humidistat)
    assert os_humidistat_str.startswith('OS:ZoneControl:Humidistat,')
