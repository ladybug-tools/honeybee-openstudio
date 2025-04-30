# coding=utf-8
"""Test the translators for geometry from OpenStudio."""
import os

from ladybug_geometry.geometry3d import Point3D, Vector3D, Mesh3D
from honeybee.model import Model
from honeybee.room import Room
from honeybee.face import Face
from honeybee.aperture import Aperture
from honeybee.door import Door
from honeybee.shade import Shade
from honeybee.shademesh import ShadeMesh
from honeybee_energy.hvac.idealair import IdealAirSystem
from honeybee_energy.lib.programtypes import office_program

from honeybee_openstudio.openstudio import OSModel
from honeybee_openstudio.writer import model_to_openstudio, room_to_openstudio
from honeybee_openstudio.reader import shades_from_openstudio, door_from_openstudio, \
    aperture_from_openstudio, face_from_openstudio, room_from_openstudio, \
    model_from_openstudio, model_from_osm_file, model_from_idf_file, \
    model_from_gbxml_file


def test_shade_reader():
    """Test the basic functionality of the Shade reader."""
    os_model = OSModel()
    rect_verts_1 = [[0, 0, 3], [1, 0, 3], [1, 1, 3], [0, 1, 3]]
    rect_verts_2 = [[0, 0, 0], [1, 0, 0], [1, 0, 3], [0, 0, 3]]
    shade_1 = Shade.from_vertices('overhang1', rect_verts_1)
    shade_2 = Shade.from_vertices('overhang2', rect_verts_2)
    shade_model = Model('Test_Model', orphaned_shades=[shade_1, shade_2])

    os_model = model_to_openstudio(shade_model, os_model)
    for os_shading_group in os_model.getShadingSurfaceGroups():
        shades = shades_from_openstudio(os_shading_group)
        assert len(shades) == 2
        assert 3.999 < sum(s.area for s in shades) < 4.001


def test_door_reader():
    """Test the basic functionality of the Door reader."""
    os_model = OSModel()
    vertices_parent_wall = [[0, 0, 0], [0, 10, 0], [0, 10, 3], [0, 0, 3]]
    vertices_wall = [[0, 1, 0.1], [0, 2, 0.1], [0, 2, 2.8], [0, 1, 2.8]]
    vertices_parent_roof = [[10, 0, 3], [10, 10, 3], [0, 10, 3], [0, 0, 3]]
    vertices_roof = [[4, 3, 3], [4, 4, 3], [3, 4, 3], [3, 3, 3]]

    wf = Face.from_vertices('wall_face', vertices_parent_wall)
    wd = Door.from_vertices('wall_door', vertices_wall)
    wf.add_door(wd)
    rf = Face.from_vertices('roof_face', vertices_parent_roof)
    rd = Door.from_vertices('roof_door', vertices_roof)
    rf.add_door(rd)
    room = Room('Test_Room_1', [wf, rf])

    room_to_openstudio(room, os_model)
    for os_door in os_model.getSubSurfaces():
        door = door_from_openstudio(os_door)
        assert isinstance(door, Door)
        assert not door.is_glass


def test_aperture_reader():
    """Test the basic functionality of the Aperture reader."""
    os_model = OSModel()
    vertices_parent_wall = [[0, 0, 0], [0, 10, 0], [0, 10, 3], [0, 0, 3]]
    vertices_wall = [[0, 1, 1], [0, 3, 1], [0, 3, 2.5], [0, 1, 2.5]]
    vertices_parent_roof = [[10, 0, 3], [10, 10, 3], [0, 10, 3], [0, 0, 3]]
    vertices_roof = [[4, 1, 3], [4, 4, 3], [1, 4, 3], [1, 1, 3]]

    wf = Face.from_vertices('wall_face', vertices_parent_wall)
    wa = Aperture.from_vertices('wall_window', vertices_wall)
    wf.add_aperture(wa)
    rf = Face.from_vertices('roof_face', vertices_parent_roof)
    ra = Aperture.from_vertices('roof_window', vertices_roof)
    rf.add_aperture(ra)
    room = Room('Test_Room_1', [wf, rf])

    room_to_openstudio(room, os_model)
    for os_ap in os_model.getSubSurfaces():
        ap = aperture_from_openstudio(os_ap)
        assert isinstance(ap, Aperture)
        assert not ap.is_operable


def test_face_reader():
    """Test the basic functionality of the Face OpenStudio reader."""
    os_model = OSModel()
    wall_pts = [[0, 0, 0], [10, 0, 0], [10, 0, 10], [0, 0, 10]]
    roof_pts = [[0, 0, 3], [10, 0, 3], [10, 10, 3], [0, 10, 3]]
    floor_pts = [[0, 0, 0], [0, 10, 0], [10, 10, 0], [10, 0, 0]]

    wall_face = Face.from_vertices('wall_face', wall_pts)
    roof_face = Face.from_vertices('roof_face', roof_pts)
    floor_face = Face.from_vertices('floor_face', floor_pts)
    room = Room('Test_Room_1', [wall_face, roof_face, floor_face])

    room_to_openstudio(room, os_model)
    for os_face in os_model.getSurfaces():
        face = face_from_openstudio(os_face)
        assert isinstance(face, Face)


def test_room_reader():
    """Test the basic functionality of the Room OpenStudio reader."""
    os_model = OSModel()
    room = Room.from_box('Tiny_House', 15, 30, 10)
    south_face = room[3]
    south_face.apertures_by_ratio(0.4, 0.01)
    south_face.apertures[0].overhang(0.5, indoor=False)
    south_face.apertures[0].overhang(0.5, indoor=True)
    south_face.apertures[0].move_shades(Vector3D(0, 0, -0.5))

    os_room = room_to_openstudio(room, os_model)
    rebuilt_room = room_from_openstudio(os_room)

    assert room.identifier == rebuilt_room.identifier
    assert room.floor_area == rebuilt_room.floor_area
    assert room.volume == rebuilt_room.volume
    assert room.exposed_area == rebuilt_room.exposed_area
    assert room.multiplier == rebuilt_room.multiplier
    assert room.zone == rebuilt_room.zone
    assert room.story == rebuilt_room.story
    assert room.exclude_floor_area == rebuilt_room.exclude_floor_area


def test_model_reader():
    """Test the basic functionality of the Model OpenStudio reader."""
    room = Room.from_box('Tiny_House_Zone', 5, 10, 3)
    south_face = room[3]
    south_face.apertures_by_ratio(0.4, 0.01)
    south_face.apertures[0].overhang(0.5, indoor=False)
    south_face.apertures[0].overhang(0.5, indoor=True)
    south_face.apertures[0].move_shades(Vector3D(0, 0, -0.5))
    pts = (Point3D(0, 0, 4), Point3D(0, 2, 4), Point3D(2, 2, 4),
           Point3D(2, 0, 4), Point3D(4, 0, 4))
    mesh = Mesh3D(pts, [(0, 1, 2, 3), (2, 3, 4)])
    awning_1 = ShadeMesh('Awning_1', mesh)
    room.properties.energy.program_type = office_program
    room.properties.energy.add_default_ideal_air()

    model = Model('Tiny_House', [room], shade_meshes=[awning_1])

    os_model = model_to_openstudio(model)
    rebuilt_model = model_from_openstudio(os_model)
    assert isinstance(rebuilt_model, Model)
    rebuilt_room = rebuilt_model.rooms[0]
    assert rebuilt_room.properties.energy.program_type.identifier == \
        office_program.identifier
    assert rebuilt_room.properties.energy.people.people_per_area == \
        office_program.people.people_per_area
    assert rebuilt_room.properties.energy.lighting.watts_per_area == \
        office_program.lighting.watts_per_area
    assert rebuilt_room.properties.energy.electric_equipment.watts_per_area == \
        office_program.electric_equipment.watts_per_area
    assert rebuilt_room.properties.energy.gas_equipment is None
    assert rebuilt_room.properties.energy.infiltration.flow_per_exterior_area == \
        office_program.infiltration.flow_per_exterior_area
    assert rebuilt_room.properties.energy.ventilation.flow_per_person == \
        office_program.ventilation.flow_per_person
    assert rebuilt_room.properties.energy.ventilation.flow_per_area == \
        office_program.ventilation.flow_per_area
    assert rebuilt_room.properties.energy.setpoint.heating_setpoint == \
        office_program.setpoint.heating_setpoint
    assert rebuilt_room.properties.energy.setpoint.cooling_setpoint == \
        office_program.setpoint.cooling_setpoint
    assert isinstance(rebuilt_room.properties.energy.hvac, IdealAirSystem)

    rebuilt_model = model_from_openstudio(os_model, reset_properties=True)
    assert isinstance(rebuilt_model, Model)
    rebuilt_room = rebuilt_model.rooms[0]
    assert rebuilt_room.properties.energy.program_type.identifier == 'Plenum'
    assert rebuilt_room.properties.energy.hvac is None


def test_model_from_osm_file():
    """Test the translation of a Model with programs, constructions and HVAC from OSM."""
    standard_test = 'assets/large_revit_sample.osm'
    standard_test = os.path.join(os.path.dirname(__file__), standard_test)
    model = model_from_osm_file(standard_test, print_warnings=True)
    assert isinstance(model, Model)
    assert len(model.rooms) == 102


def test_model_from_idf_file():
    """Test the translation from IDF to a Honeybee Model."""
    standard_test = 'assets/large_revit_sample.idf'
    standard_test = os.path.join(os.path.dirname(__file__), standard_test)
    model = model_from_idf_file(standard_test, print_warnings=True)
    assert isinstance(model, Model)
    assert len(model.rooms) == 102


def test_model_from_gbxml_file():
    """Test the translation from gbXML to a Honeybee Model."""
    standard_test = 'assets/large_revit_sample.xml'
    standard_test = os.path.join(os.path.dirname(__file__), standard_test)
    model = model_from_gbxml_file(standard_test, print_warnings=True)
    assert isinstance(model, Model)
    assert len(model.rooms) == 102
