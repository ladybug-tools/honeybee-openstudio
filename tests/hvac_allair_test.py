# coding=utf-8
"""Test the translators for All-Air HVAC systems to OpenStudio."""
from ladybug_geometry.geometry3d import Point3D
from honeybee.model import Model
from honeybee.room import Room
from honeybee_energy.hvac.allair.ptac import PTAC
from honeybee_energy.hvac.allair.psz import PSZ
from honeybee_energy.hvac.allair.pvav import PVAV
from honeybee_energy.hvac.allair.vav import VAV
from honeybee_energy.hvac.allair.furnace import ForcedAirFurnace
from honeybee_energy.lib.programtypes import office_program

from honeybee_openstudio.openstudio import os_vector_len
from honeybee_openstudio.writer import model_to_openstudio


def test_hvac_vav():
    """Test the translation of a model with a VAV system."""
    first_floor = Room.from_box('First_Floor', 10, 10, 3, origin=Point3D(0, 0, 0))
    second_floor = Room.from_box('Second_Floor', 10, 10, 3, origin=Point3D(0, 0, 3))
    first_floor.properties.energy.program_type = office_program
    second_floor.properties.energy.program_type = office_program
    Room.solve_adjacency([first_floor, second_floor], 0.01)

    hvac_sys = VAV('High Efficiency VAV System')
    hvac_sys.vintage = 'ASHRAE_2019'
    hvac_sys.economizer_type = 'DifferentialDryBulb'
    hvac_sys.sensible_heat_recovery = 0.5
    hvac_sys.latent_heat_recovery = 0

    first_floor.properties.energy.hvac = hvac_sys
    second_floor.properties.energy.hvac = hvac_sys

    model = Model('Test_Bldg', [first_floor, second_floor])

    os_model = model_to_openstudio(model)

    air_loops = os_model.getAirLoopHVACs()
    plant_loops = os_model.getPlantLoops()
    assert os_vector_len(air_loops) == 1
    assert os_vector_len(plant_loops) == 3


def test_hvac_pvav():
    """Test the translation of a model with a PVAV system."""
    first_floor = Room.from_box('First_Floor', 10, 10, 3, origin=Point3D(0, 0, 0))
    second_floor = Room.from_box('Second_Floor', 10, 10, 3, origin=Point3D(0, 0, 3))
    first_floor.properties.energy.program_type = office_program
    second_floor.properties.energy.program_type = office_program
    Room.solve_adjacency([first_floor, second_floor], 0.01)

    hvac_sys = PVAV('High Efficiency PVAV System')
    hvac_sys.equipment_type = 'PVAV_ASHP'
    hvac_sys.vintage = 'ASHRAE_2019'
    hvac_sys.economizer_type = 'DifferentialDryBulb'
    hvac_sys.sensible_heat_recovery = 0.5
    hvac_sys.latent_heat_recovery = 0

    first_floor.properties.energy.hvac = hvac_sys
    second_floor.properties.energy.hvac = hvac_sys

    model = Model('Test_Bldg', [first_floor, second_floor])

    os_model = model_to_openstudio(model)

    air_loops = os_model.getAirLoopHVACs()
    plant_loops = os_model.getPlantLoops()
    assert os_vector_len(air_loops) == 1
    assert os_vector_len(plant_loops) == 1


def test_hvac_psz():
    """Test the translation of a model with a PSZ system."""
    first_floor = Room.from_box('First_Floor', 10, 10, 3, origin=Point3D(0, 0, 0))
    second_floor = Room.from_box('Second_Floor', 10, 10, 3, origin=Point3D(0, 0, 3))
    first_floor.properties.energy.program_type = office_program
    second_floor.properties.energy.program_type = office_program
    Room.solve_adjacency([first_floor, second_floor], 0.01)

    hvac_sys = hvac_sys = PSZ('Test PSZAC System')
    hvac_sys.equipment_type = 'PSZAC_ElectricBaseboard'

    first_floor.properties.energy.hvac = hvac_sys
    second_floor.properties.energy.hvac = hvac_sys

    model = Model('Test_Bldg', [first_floor, second_floor])

    os_model = model_to_openstudio(model)

    air_loops = os_model.getAirLoopHVACs()
    plant_loops = os_model.getPlantLoops()
    assert os_vector_len(air_loops) == 2
    assert os_vector_len(plant_loops) == 0


def test_hvac_ptac():
    """Test the translation of a model with a PTAC system."""
    first_floor = Room.from_box('First_Floor', 10, 10, 3, origin=Point3D(0, 0, 0))
    second_floor = Room.from_box('Second_Floor', 10, 10, 3, origin=Point3D(0, 0, 3))
    first_floor.properties.energy.program_type = office_program
    second_floor.properties.energy.program_type = office_program
    Room.solve_adjacency([first_floor, second_floor], 0.01)

    hvac_sys = hvac_sys = PTAC('Test Packaged AC')
    hvac_sys.equipment_type = 'PTAC_ElectricBaseboard'
    first_floor.properties.energy.hvac = hvac_sys
    second_floor.properties.energy.hvac = hvac_sys

    model = Model('Test_Bldg', [first_floor, second_floor])

    os_model = model_to_openstudio(model)

    ptacs = os_model.getZoneHVACPackagedTerminalAirConditioners()
    assert os_vector_len(ptacs) == 2

    hvac_sys = hvac_sys = PTAC('Test Packaged Heat Pump')
    hvac_sys.equipment_type = 'PTHP'
    first_floor.properties.energy.hvac = hvac_sys
    second_floor.properties.energy.hvac = hvac_sys

    os_model = model_to_openstudio(model)

    ptacs = os_model.getZoneHVACPackagedTerminalHeatPumps()
    assert os_vector_len(ptacs) == 2


def test_hvac_furnace():
    """Test the translation of a model with a Furnace system."""
    first_floor = Room.from_box('First_Floor', 10, 10, 3, origin=Point3D(0, 0, 0))
    second_floor = Room.from_box('Second_Floor', 10, 10, 3, origin=Point3D(0, 0, 3))
    first_floor.properties.energy.program_type = office_program
    second_floor.properties.energy.program_type = office_program
    Room.solve_adjacency([first_floor, second_floor], 0.01)

    hvac_sys = ForcedAirFurnace('Test Furnace System')
    hvac_sys.equipment_type = 'Furnace'

    first_floor.properties.energy.hvac = hvac_sys
    second_floor.properties.energy.hvac = hvac_sys

    model = Model('Test_Bldg', [first_floor, second_floor])

    os_model = model_to_openstudio(model)

    air_loops = os_model.getAirLoopHVACs()
    plant_loops = os_model.getPlantLoops()
    assert os_vector_len(air_loops) == 2
    assert os_vector_len(plant_loops) == 0
