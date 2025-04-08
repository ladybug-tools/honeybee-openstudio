# coding=utf-8
"""Test the translators for HeatCool HVAC systems to OpenStudio."""
import os

from ladybug_geometry.geometry3d import Point3D
from honeybee.model import Model
from honeybee.room import Room
from honeybee_energy.hvac.heatcool.baseboard import Baseboard
from honeybee_energy.hvac.heatcool.evapcool import EvaporativeCooler
from honeybee_energy.hvac.heatcool.fcu import FCU
from honeybee_energy.hvac.heatcool.gasunit import GasUnitHeater
from honeybee_energy.hvac.heatcool.residential import Residential
from honeybee_energy.hvac.heatcool.vrf import VRF
from honeybee_energy.hvac.heatcool.windowac import WindowAC
from honeybee_energy.hvac.heatcool.wshp import WSHP
from honeybee_energy.hvac.heatcool.radiant import Radiant
from honeybee_energy.lib.programtypes import office_program

from honeybee_openstudio.openstudio import os_vector_len, OSModel
from honeybee_openstudio.writer import model_to_openstudio
from honeybee_openstudio.simulation import assign_epw_to_model


def test_baseboard():
    """Test the translation of a model with a Baseboard system."""
    first_floor = Room.from_box('First_Floor', 10, 10, 3, origin=Point3D(0, 0, 0))
    second_floor = Room.from_box('Second_Floor', 10, 10, 3, origin=Point3D(0, 0, 3))
    first_floor.properties.energy.program_type = office_program
    second_floor.properties.energy.program_type = office_program
    Room.solve_adjacency([first_floor, second_floor], 0.01)

    hvac_sys = Baseboard('Test Baseboard System')
    hvac_sys.equipment_type = 'ElectricBaseboard'
    hvac_sys.vintage = 'ASHRAE_2019'

    first_floor.properties.energy.hvac = hvac_sys
    second_floor.properties.energy.hvac = hvac_sys

    model = Model('Test_Bldg', [first_floor, second_floor])

    os_model = model_to_openstudio(model)

    air_loops = os_model.getAirLoopHVACs()
    plant_loops = os_model.getPlantLoops()
    assert os_vector_len(air_loops) == 0
    assert os_vector_len(plant_loops) == 0


def test_evaporative_cooler():
    """Test the translation of a model with a EvaporativeCooler system."""
    first_floor = Room.from_box('First_Floor', 10, 10, 3, origin=Point3D(0, 0, 0))
    second_floor = Room.from_box('Second_Floor', 10, 10, 3, origin=Point3D(0, 0, 3))
    first_floor.properties.energy.program_type = office_program
    second_floor.properties.energy.program_type = office_program
    Room.solve_adjacency([first_floor, second_floor], 0.01)

    hvac_sys = EvaporativeCooler('Test EvaporativeCooler System')
    hvac_sys.equipment_type = 'EvapCoolers_BoilerBaseboard'
    hvac_sys.vintage = 'ASHRAE_2019'

    first_floor.properties.energy.hvac = hvac_sys
    second_floor.properties.energy.hvac = hvac_sys

    model = Model('Test_Bldg', [first_floor, second_floor])

    os_model = model_to_openstudio(model)

    air_loops = os_model.getAirLoopHVACs()
    plant_loops = os_model.getPlantLoops()
    assert os_vector_len(air_loops) == 2
    assert os_vector_len(plant_loops) == 1


def test_fcu():
    """Test the translation of a model with a FCU system."""
    first_floor = Room.from_box('First_Floor', 10, 10, 3, origin=Point3D(0, 0, 0))
    second_floor = Room.from_box('Second_Floor', 10, 10, 3, origin=Point3D(0, 0, 3))
    first_floor.properties.energy.program_type = office_program
    second_floor.properties.energy.program_type = office_program
    Room.solve_adjacency([first_floor, second_floor], 0.01)

    hvac_sys = FCU('Test FCU System')
    hvac_sys.equipment_type = 'FCU_DCW_DHW'
    hvac_sys.vintage = 'ASHRAE_2019'

    first_floor.properties.energy.hvac = hvac_sys
    second_floor.properties.energy.hvac = hvac_sys

    model = Model('Test_Bldg', [first_floor, second_floor])

    os_model = model_to_openstudio(model)

    air_loops = os_model.getAirLoopHVACs()
    plant_loops = os_model.getPlantLoops()
    assert os_vector_len(air_loops) == 0
    assert os_vector_len(plant_loops) == 2


def test_gas_unit_heater():
    """Test the translation of a model with a GasUnitHeater system."""
    first_floor = Room.from_box('First_Floor', 10, 10, 3, origin=Point3D(0, 0, 0))
    second_floor = Room.from_box('Second_Floor', 10, 10, 3, origin=Point3D(0, 0, 3))
    first_floor.properties.energy.program_type = office_program
    second_floor.properties.energy.program_type = office_program
    Room.solve_adjacency([first_floor, second_floor], 0.01)

    hvac_sys = GasUnitHeater('Test Gas Unit Heater System')
    hvac_sys.equipment_type = 'GasHeaters'
    hvac_sys.vintage = 'ASHRAE_2019'

    first_floor.properties.energy.hvac = hvac_sys
    second_floor.properties.energy.hvac = hvac_sys

    model = Model('Test_Bldg', [first_floor, second_floor])

    os_model = model_to_openstudio(model)

    air_loops = os_model.getAirLoopHVACs()
    plant_loops = os_model.getPlantLoops()
    assert os_vector_len(air_loops) == 0
    assert os_vector_len(plant_loops) == 0


def test_hvac_residential():
    """Test the translation of a model with a Residential AC system."""
    first_floor = Room.from_box('First_Floor', 10, 10, 3, origin=Point3D(0, 0, 0))
    second_floor = Room.from_box('Second_Floor', 10, 10, 3, origin=Point3D(0, 0, 3))
    first_floor.properties.energy.program_type = office_program
    second_floor.properties.energy.program_type = office_program
    Room.solve_adjacency([first_floor, second_floor], 0.01)

    hvac_sys = Residential('Test Residential AC System')
    hvac_sys.equipment_type = 'ResidentialAC_ResidentialFurnace'

    first_floor.properties.energy.hvac = hvac_sys
    second_floor.properties.energy.hvac = hvac_sys

    model = Model('Test_Bldg', [first_floor, second_floor])

    os_model = model_to_openstudio(model)

    air_loops = os_model.getAirLoopHVACs()
    plant_loops = os_model.getPlantLoops()
    assert os_vector_len(air_loops) == 2
    assert os_vector_len(plant_loops) == 0


def test_vrf():
    """Test the translation of a model with a VRF system."""
    first_floor = Room.from_box('First_Floor', 10, 10, 3, origin=Point3D(0, 0, 0))
    second_floor = Room.from_box('Second_Floor', 10, 10, 3, origin=Point3D(0, 0, 3))
    first_floor.properties.energy.program_type = office_program
    second_floor.properties.energy.program_type = office_program
    Room.solve_adjacency([first_floor, second_floor], 0.01)

    hvac_sys = VRF('Test VRF System')
    hvac_sys.vintage = 'ASHRAE_2019'

    first_floor.properties.energy.hvac = hvac_sys
    second_floor.properties.energy.hvac = hvac_sys

    model = Model('Test_Bldg', [first_floor, second_floor])

    os_model = model_to_openstudio(model)

    air_loops = os_model.getAirLoopHVACs()
    plant_loops = os_model.getPlantLoops()
    vrfs = os_model.getAirConditionerVariableRefrigerantFlows()
    assert os_vector_len(air_loops) == 0
    assert os_vector_len(plant_loops) == 0
    assert os_vector_len(vrfs) == 1


def test_window_ac():
    """Test the translation of a model with a WindowAC system."""
    first_floor = Room.from_box('First_Floor', 10, 10, 3, origin=Point3D(0, 0, 0))
    second_floor = Room.from_box('Second_Floor', 10, 10, 3, origin=Point3D(0, 0, 3))
    first_floor.properties.energy.program_type = office_program
    second_floor.properties.energy.program_type = office_program
    Room.solve_adjacency([first_floor, second_floor], 0.01)

    hvac_sys = WindowAC('Test Window AC System')
    hvac_sys.equipment_type = 'WindowAC_BoilerBaseboard'
    hvac_sys.vintage = 'ASHRAE_2019'

    first_floor.properties.energy.hvac = hvac_sys
    second_floor.properties.energy.hvac = hvac_sys

    model = Model('Test_Bldg', [first_floor, second_floor])

    os_model = model_to_openstudio(model)

    air_loops = os_model.getAirLoopHVACs()
    plant_loops = os_model.getPlantLoops()
    assert os_vector_len(air_loops) == 0
    assert os_vector_len(plant_loops) == 1

    from honeybee.config import folders
    osm = os.path.join(folders.default_simulation_folder, 'in.osm')
    os_model.save(osm, overwrite=True)


def test_wshp():
    """Test the translation of a model with a WSHP system."""
    first_floor = Room.from_box('First_Floor', 10, 10, 3, origin=Point3D(0, 0, 0))
    second_floor = Room.from_box('Second_Floor', 10, 10, 3, origin=Point3D(0, 0, 3))
    first_floor.properties.energy.program_type = office_program
    second_floor.properties.energy.program_type = office_program
    Room.solve_adjacency([first_floor, second_floor], 0.01)

    hvac_sys = WSHP('Test WSHP System')
    hvac_sys.equipment_type = 'WSHP_CoolingTower_Boiler'
    hvac_sys.vintage = 'ASHRAE_2019'

    first_floor.properties.energy.hvac = hvac_sys
    second_floor.properties.energy.hvac = hvac_sys

    model = Model('Test_Bldg', [first_floor, second_floor])

    os_model = model_to_openstudio(model)

    air_loops = os_model.getAirLoopHVACs()
    plant_loops = os_model.getPlantLoops()
    assert os_vector_len(air_loops) == 0
    assert os_vector_len(plant_loops) == 1


def test_low_temp_radiant_slab():
    """Test the translation of a model with a Radiant system."""
    first_floor = Room.from_box('First_Floor', 10, 10, 3, origin=Point3D(0, 0, 0))
    second_floor = Room.from_box('Second_Floor', 10, 10, 3, origin=Point3D(0, 0, 3))
    first_floor.properties.energy.program_type = office_program
    second_floor.properties.energy.program_type = office_program
    Room.solve_adjacency([first_floor, second_floor], 0.01)

    hvac_sys = Radiant('Test Radiant Ceiling Slab System')
    hvac_sys.vintage = 'ASHRAE_2019'
    hvac_sys.equipment_type = 'Radiant_Chiller_ASHP'
    hvac_sys.radiant_type = 'Ceiling'

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
    assert os_vector_len(air_loops) == 0
    assert os_vector_len(plant_loops) == 3
    assert os_vector_len(rad_heats) == 2


def test_low_temp_radiant_hardwood_floor():
    """Test the translation of a model with a Radiant Panel with DOAS system."""
    first_floor = Room.from_box('First_Floor', 10, 10, 3, origin=Point3D(0, 0, 0))
    second_floor = Room.from_box('Second_Floor', 10, 10, 3, origin=Point3D(0, 0, 3))
    first_floor.properties.energy.program_type = office_program
    second_floor.properties.energy.program_type = office_program
    Room.solve_adjacency([first_floor, second_floor], 0.01)

    hvac_sys = Radiant('Test Radiant Hardwood Floor')
    hvac_sys.vintage = 'ASHRAE_2019'
    hvac_sys.equipment_type = 'Radiant_ACChiller_ASHP'
    hvac_sys.radiant_type = 'FloorWithHardwood'

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
    assert os_vector_len(air_loops) == 0
    assert os_vector_len(plant_loops) == 2
    assert os_vector_len(rad_heats) == 2
