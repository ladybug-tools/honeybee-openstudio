
from ladybug_geometry.geometry3d import Point3D
from honeybee.model import Model
from honeybee.room import Room
from honeybee_energy.hvac.allair.vav import VAV
from honeybee_energy.lib.programtypes import office_program

from honeybee_openstudio.writer import model_to_openstudio


def test_hvac_vav():
    """Test the translation of a model with a VAV system."""
    first_floor = Room.from_box('First_Floor', 10, 10, 3, origin=Point3D(0, 0, 0))
    second_floor = Room.from_box('Second_Floor', 10, 10, 3, origin=Point3D(0, 0, 3))
    first_floor.properties.energy.program_type = office_program
    second_floor.properties.energy.program_type = office_program
    Room.solve_adjacency([first_floor, second_floor], 0.01)

    hvac_sys = VAV('High Efficiency HVAC System')
    hvac_sys.vintage = 'ASHRAE_2010'
    hvac_sys.economizer_type = 'DifferentialDryBulb'
    hvac_sys.sensible_heat_recovery = 0.8
    hvac_sys.latent_heat_recovery = 0.65

    first_floor.properties.energy.hvac = hvac_sys
    second_floor.properties.energy.hvac = hvac_sys

    model = Model('Test_Bldg', [first_floor, second_floor])

    os_model = model_to_openstudio(model)

    import os
    from honeybee.config import folders
    osm = os.path.join(folders.default_simulation_folder, 'in.osm')
    os_model.save(osm, overwrite=True)
