# coding=utf-8
"""Test the translators for SHW Systems to OpenStudio."""
from ladybug.dt import Time
from honeybee.model import Model
from honeybee.room import Room
from honeybee_energy.shw import SHWSystem
from honeybee_energy.load.hotwater import ServiceHotWater
from honeybee_energy.schedule.day import ScheduleDay
from honeybee_energy.schedule.ruleset import ScheduleRuleset
import honeybee_energy.lib.scheduletypelimits as schedule_types

from honeybee_openstudio.openstudio import os_vector_len
from honeybee_openstudio.writer import model_to_openstudio


def test_model_default_shw():
    """Test the translation of the default district heating system to OpenStudio."""
    room = Room.from_box('Office_Restroom', 5, 10, 3)
    simple_office = ScheduleDay('Simple Weekday', [0, 1, 0],
                                [Time(0, 0), Time(9, 0), Time(17, 0)])
    schedule = ScheduleRuleset('Office Water Use', simple_office,
                               None, schedule_types.fractional)
    shw_load = ServiceHotWater.from_watts_per_area('Office Hot Water', 10, schedule)
    room.properties.energy.service_hot_water = shw_load
    model = Model('Test_Office', [room])

    os_model = model_to_openstudio(model)
    shw_loops = os_model.getPlantLoops()
    water_heaters = os_model.getWaterHeaterMixeds()
    assert os_vector_len(shw_loops) == 1
    assert os_vector_len(water_heaters) == 1


def test_model_gas_shw():
    """Test the translation of a Gas_WaterHeater system to OpenStudio."""
    room = Room.from_box('Office_Restroom', 5, 10, 3)
    simple_office = ScheduleDay('Simple Weekday', [0, 1, 0],
                                [Time(0, 0), Time(9, 0), Time(17, 0)])
    schedule = ScheduleRuleset('Office Water Use', simple_office,
                               None, schedule_types.fractional)
    shw_load = ServiceHotWater.from_watts_per_area('Office Hot Water', 10, schedule)
    room.properties.energy.service_hot_water = shw_load
    shw_system = SHWSystem('Restroom Water Heater', 'Gas_WaterHeater')
    room.properties.energy.shw = shw_system
    model = Model('Test_Office', [room])

    os_model = model_to_openstudio(model)
    shw_loops = os_model.getPlantLoops()
    water_heaters = os_model.getWaterHeaterMixeds()
    assert os_vector_len(shw_loops) == 1
    assert os_vector_len(water_heaters) == 1


def test_model_electric_tankless_shw():
    """Test the translation of a Electric_TanklessHeater system to OpenStudio."""
    room = Room.from_box('Office_Restroom', 5, 10, 3)
    simple_office = ScheduleDay('Simple Weekday', [0, 1, 0],
                                [Time(0, 0), Time(9, 0), Time(17, 0)])
    schedule = ScheduleRuleset('Office Water Use', simple_office,
                               None, schedule_types.fractional)
    shw_load = ServiceHotWater.from_watts_per_area('Office Hot Water', 10, schedule)
    room.properties.energy.service_hot_water = shw_load
    shw_system = SHWSystem('Restroom Water Heater', 'Electric_TanklessHeater')
    room.properties.energy.shw = shw_system
    model = Model('Test_Office', [room])

    os_model = model_to_openstudio(model)
    shw_loops = os_model.getPlantLoops()
    water_heaters = os_model.getWaterHeaterMixeds()
    assert os_vector_len(shw_loops) == 1
    assert os_vector_len(water_heaters) == 1


def test_model_heat_pump_shw():
    """Test the translation of a HeatPump_WaterHeater system to OpenStudio."""
    room = Room.from_box('Office_Restroom', 5, 10, 3)
    simple_office = ScheduleDay('Simple Weekday', [0, 1, 0],
                                [Time(0, 0), Time(9, 0), Time(17, 0)])
    schedule = ScheduleRuleset('Office Water Use', simple_office,
                               None, schedule_types.fractional)
    shw_load = ServiceHotWater.from_watts_per_area('Office Hot Water', 10, schedule)
    room.properties.energy.service_hot_water = shw_load
    shw_system = SHWSystem('Restroom Water Heater', 'HeatPump_WaterHeater',
                           ambient_condition=room.identifier)
    room.properties.energy.shw = shw_system
    model = Model('Test_Office', [room])

    os_model = model_to_openstudio(model)
    shw_loops = os_model.getPlantLoops()
    water_heaters = os_model.getWaterHeaterMixeds()
    heat_pumps = os_model.getWaterHeaterHeatPumps()
    assert os_vector_len(shw_loops) == 1
    assert os_vector_len(water_heaters) == 1
    assert os_vector_len(heat_pumps) == 1
