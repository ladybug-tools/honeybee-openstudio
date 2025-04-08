
from ladybug_geometry.geometry3d import Point3D
from honeybee.model import Model
from honeybee.room import Room
from honeybee_energy.hvac.allair.ptac import PTAC
from honeybee_energy.hvac.allair.psz import PSZ
from honeybee_energy.hvac.allair.pvav import PVAV
from honeybee_energy.hvac.allair.vav import VAV
from honeybee_energy.hvac.allair.furnace import ForcedAirFurnace
from honeybee_energy.hvac.doas.fcu import FCUwithDOAS
from honeybee_energy.hvac.doas.vrf import VRFwithDOAS
from honeybee_energy.hvac.doas.wshp import WSHPwithDOAS
from honeybee_energy.hvac.doas.radiant import RadiantwithDOAS
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
    """Test the translation of a model with a VAV system."""
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
    """Test the translation of a model with a VAV system."""
    first_floor = Room.from_box('First_Floor', 10, 10, 3, origin=Point3D(0, 0, 0))
    second_floor = Room.from_box('Second_Floor', 10, 10, 3, origin=Point3D(0, 0, 3))
    first_floor.properties.energy.program_type = office_program
    second_floor.properties.energy.program_type = office_program
    Room.solve_adjacency([first_floor, second_floor], 0.01)

    hvac_sys = hvac_sys = PSZ('Test System')
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
    """Test the translation of a model with a VAV system."""
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
    """Test the translation of a model with a VAV system."""
    first_floor = Room.from_box('First_Floor', 10, 10, 3, origin=Point3D(0, 0, 0))
    second_floor = Room.from_box('Second_Floor', 10, 10, 3, origin=Point3D(0, 0, 3))
    first_floor.properties.energy.program_type = office_program
    second_floor.properties.energy.program_type = office_program
    Room.solve_adjacency([first_floor, second_floor], 0.01)

    hvac_sys = ForcedAirFurnace('High Efficiency HVAC System')
    hvac_sys.equipment_type = 'Furnace'

    first_floor.properties.energy.hvac = hvac_sys
    second_floor.properties.energy.hvac = hvac_sys

    model = Model('Test_Bldg', [first_floor, second_floor])

    os_model = model_to_openstudio(model)

    air_loops = os_model.getAirLoopHVACs()
    plant_loops = os_model.getPlantLoops()
    assert os_vector_len(air_loops) == 2
    assert os_vector_len(plant_loops) == 0

    import os
    from honeybee.config import folders
    osm = os.path.join(folders.default_simulation_folder, 'in.osm')
    os_model.save(osm, overwrite=True)
