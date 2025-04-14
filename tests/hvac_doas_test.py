# coding=utf-8
"""Test the translators for DOAS HVAC systems to OpenStudio."""
import os

from ladybug_geometry.geometry3d import Point3D
from ladybug.dt import Time
from honeybee.model import Model
from honeybee.room import Room
from honeybee_energy.schedule.day import ScheduleDay
from honeybee_energy.schedule.rule import ScheduleRule
from honeybee_energy.schedule.ruleset import ScheduleRuleset
from honeybee_energy.hvac.doas.fcu import FCUwithDOAS
from honeybee_energy.hvac.doas.vrf import VRFwithDOAS
from honeybee_energy.hvac.doas.wshp import WSHPwithDOAS
from honeybee_energy.hvac.doas.radiant import RadiantwithDOAS
import honeybee_energy.lib.scheduletypelimits as schedule_types
from honeybee_energy.lib.programtypes import office_program

from honeybee_openstudio.openstudio import os_vector_len, OSModel
from honeybee_openstudio.writer import model_to_openstudio
from honeybee_openstudio.simulation import assign_epw_to_model


def test_fcu_with_doas():
    """Test the translation of a model with a FCU with DOAS system."""
    weekday_office = ScheduleDay('Weekday DOAS Availability', [0, 1, 0],
                                 [Time(0, 0), Time(9, 0), Time(17, 0)])
    weekend_office = ScheduleDay('Weekend DOAS Availability', [0])
    weekend_rule = ScheduleRule(weekend_office, apply_saturday=True, apply_sunday=True)
    doas_avail_sch = ScheduleRuleset('Office Occupancy', weekday_office,
                                     [weekend_rule], schedule_types.fractional)

    first_floor = Room.from_box('First_Floor', 10, 10, 3, origin=Point3D(0, 0, 0))
    second_floor = Room.from_box('Second_Floor', 10, 10, 3, origin=Point3D(0, 0, 3))
    first_floor.properties.energy.program_type = office_program
    second_floor.properties.energy.program_type = office_program
    Room.solve_adjacency([first_floor, second_floor], 0.01)

    hvac_sys = FCUwithDOAS('Test FCU with DOAS System')
    hvac_sys.vintage = 'ASHRAE_2019'
    hvac_sys.demand_controlled_ventilation = True
    hvac_sys.sensible_heat_recovery = 0.8
    hvac_sys.latent_heat_recovery = 0.75
    hvac_sys.doas_availability_schedule = doas_avail_sch

    first_floor.properties.energy.hvac = hvac_sys
    second_floor.properties.energy.hvac = hvac_sys

    model = Model('Test_Bldg', [first_floor, second_floor])

    os_model = model_to_openstudio(model)

    air_loops = os_model.getAirLoopHVACs()
    plant_loops = os_model.getPlantLoops()
    assert os_vector_len(air_loops) == 1
    assert os_vector_len(plant_loops) == 3


def test_vrf_with_doas():
    """Test the translation of a model with a VRF with DOAS system."""
    first_floor = Room.from_box('First_Floor', 10, 10, 3, origin=Point3D(0, 0, 0))
    second_floor = Room.from_box('Second_Floor', 10, 10, 3, origin=Point3D(0, 0, 3))
    first_floor.properties.energy.program_type = office_program
    second_floor.properties.energy.program_type = office_program
    Room.solve_adjacency([first_floor, second_floor], 0.01)

    hvac_sys = VRFwithDOAS('Test VRF with DOAS System')
    hvac_sys.vintage = 'ASHRAE_2019'
    hvac_sys.sensible_heat_recovery = 0.8
    hvac_sys.latent_heat_recovery = 0.75

    first_floor.properties.energy.hvac = hvac_sys
    second_floor.properties.energy.hvac = hvac_sys

    model = Model('Test_Bldg', [first_floor, second_floor])

    os_model = model_to_openstudio(model)

    air_loops = os_model.getAirLoopHVACs()
    plant_loops = os_model.getPlantLoops()
    vrfs = os_model.getAirConditionerVariableRefrigerantFlows()
    assert os_vector_len(air_loops) == 1
    assert os_vector_len(plant_loops) == 0
    assert os_vector_len(vrfs) == 1


def test_wshp_with_doas():
    """Test the translation of a model with a WSHP with DOAS system."""
    first_floor = Room.from_box('First_Floor', 10, 10, 3, origin=Point3D(0, 0, 0))
    second_floor = Room.from_box('Second_Floor', 10, 10, 3, origin=Point3D(0, 0, 3))
    first_floor.properties.energy.program_type = office_program
    second_floor.properties.energy.program_type = office_program
    Room.solve_adjacency([first_floor, second_floor], 0.01)

    hvac_sys = WSHPwithDOAS('Test WSHP with DOAS System')
    hvac_sys.equipment_type = 'DOAS_WSHP_FluidCooler_Boiler'
    hvac_sys.vintage = 'ASHRAE_2019'
    hvac_sys.sensible_heat_recovery = 0.8
    hvac_sys.latent_heat_recovery = 0.75

    first_floor.properties.energy.hvac = hvac_sys
    second_floor.properties.energy.hvac = hvac_sys

    model = Model('Test_Bldg', [first_floor, second_floor])

    os_model = model_to_openstudio(model)

    air_loops = os_model.getAirLoopHVACs()
    plant_loops = os_model.getPlantLoops()
    assert os_vector_len(air_loops) == 1
    assert os_vector_len(plant_loops) == 4

    hvac_sys = WSHPwithDOAS('Test GSHP with DOAS System')
    hvac_sys.equipment_type = 'DOAS_WSHP_GSHP'
    hvac_sys.vintage = 'ASHRAE_2019'
    hvac_sys.sensible_heat_recovery = 0.8
    hvac_sys.latent_heat_recovery = 0.75
    first_floor.properties.energy.hvac = hvac_sys
    second_floor.properties.energy.hvac = hvac_sys

    os_model = model_to_openstudio(model)

    air_loops = os_model.getAirLoopHVACs()
    plant_loops = os_model.getPlantLoops()
    assert os_vector_len(air_loops) == 1
    assert os_vector_len(plant_loops) == 1


def test_low_temp_radiant_slab_with_doas():
    """Test the translation of a model with a Radiant with DOAS system."""
    first_floor = Room.from_box('First_Floor', 10, 10, 3, origin=Point3D(0, 0, 0))
    second_floor = Room.from_box('Second_Floor', 10, 10, 3, origin=Point3D(0, 0, 3))
    first_floor.properties.energy.program_type = office_program
    second_floor.properties.energy.program_type = office_program
    Room.solve_adjacency([first_floor, second_floor], 0.01)

    hvac_sys = RadiantwithDOAS('Test Radiant with DOAS System')
    hvac_sys.vintage = 'ASHRAE_2019'
    hvac_sys.equipment_type = 'DOAS_Radiant_Chiller_ASHP'
    hvac_sys.radiant_type = 'Floor'
    hvac_sys.sensible_heat_recovery = 0.8
    hvac_sys.latent_heat_recovery = 0.75
    hvac_sys.demand_controlled_ventilation = True

    first_floor.properties.energy.hvac = hvac_sys
    second_floor.properties.energy.hvac = hvac_sys

    model = Model('Test_Bldg', [first_floor, second_floor])

    os_model = OSModel()
    epw_path = 'assets/chicago.epw'
    epw_path = os.path.join(os.path.dirname(__file__), epw_path)
    assign_epw_to_model(epw_path, os_model, set_climate_zone=True)
    os_model = model_to_openstudio(model, os_model)

    air_loops = os_model.getAirLoopHVACs()
    plant_loops = os_model.getPlantLoops()
    rad_heats = os_model.getCoilHeatingLowTempRadiantVarFlows()
    assert os_vector_len(air_loops) == 1
    assert os_vector_len(plant_loops) == 5
    assert os_vector_len(rad_heats) == 2


def test_low_temp_radiant_metal_panel_with_doas():
    """Test the translation of a model with a Radiant Panel with DOAS system."""
    first_floor = Room.from_box('First_Floor', 10, 10, 3, origin=Point3D(0, 0, 0))
    second_floor = Room.from_box('Second_Floor', 10, 10, 3, origin=Point3D(0, 0, 3))
    first_floor.properties.energy.program_type = office_program
    second_floor.properties.energy.program_type = office_program
    Room.solve_adjacency([first_floor, second_floor], 0.01)

    hvac_sys = RadiantwithDOAS('Test Radiant with DOAS System')
    hvac_sys.vintage = 'ASHRAE_2019'
    hvac_sys.equipment_type = 'DOAS_Radiant_ACChiller_ASHP'
    hvac_sys.radiant_type = 'CeilingMetalPanel'
    hvac_sys.sensible_heat_recovery = 0.8
    hvac_sys.latent_heat_recovery = 0.75
    hvac_sys.demand_controlled_ventilation = True

    first_floor.properties.energy.hvac = hvac_sys
    second_floor.properties.energy.hvac = hvac_sys

    model = Model('Test_Bldg', [first_floor, second_floor])

    os_model = OSModel()
    epw_path = 'assets/chicago.epw'
    epw_path = os.path.join(os.path.dirname(__file__), epw_path)
    assign_epw_to_model(epw_path, os_model, set_climate_zone=True)
    os_model = model_to_openstudio(model, os_model)

    air_loops = os_model.getAirLoopHVACs()
    plant_loops = os_model.getPlantLoops()
    rad_heats = os_model.getCoilHeatingLowTempRadiantVarFlows()
    assert os_vector_len(air_loops) == 1
    assert os_vector_len(plant_loops) == 4
    assert os_vector_len(rad_heats) == 2
