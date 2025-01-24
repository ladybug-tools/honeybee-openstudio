# coding=utf-8
"""Test the translators for geometry to OpenStudio."""
import os

from ladybug_geometry.geometry3d import Point3D, Vector3D, Mesh3D
from honeybee.model import Model
from honeybee.room import Room
from honeybee.face import Face
from honeybee.aperture import Aperture
from honeybee.door import Door
from honeybee.shade import Shade
from honeybee.shademesh import ShadeMesh

from honeybee_openstudio.openstudio import OSModel, os_vector_len
from honeybee_openstudio.writer import shade_mesh_to_openstudio, shade_to_openstudio, \
    door_to_openstudio, aperture_to_openstudio, face_to_openstudio, room_to_openstudio, \
    model_to_openstudio
from honeybee_energy.material.glazing import EnergyWindowMaterialGlazing
from honeybee_energy.material.gas import EnergyWindowMaterialGas
from honeybee_energy.construction.window import WindowConstruction
from honeybee_energy.construction.dynamic import WindowConstructionDynamic
from honeybee_energy.schedule.ruleset import ScheduleRuleset


def test_shade_writer():
    """Test the basic functionality of the Shade writer."""
    os_model = OSModel()
    rect_verts = [[0, 0, 3], [1, 0, 3], [1, 1, 3], [0, 1, 3]]
    shade = Shade.from_vertices('overhang', rect_verts)

    os_shade = shade_to_openstudio(shade, os_model)
    assert str(os_shade.name()) == 'overhang'
    os_shade_str = str(os_shade)
    assert os_shade_str.startswith('OS:ShadingSurface,')
    assert os_shade_str.endswith(
        '  0, 1, 3,                                !- X,Y,Z Vertex 1 {m}\n'
        '  0, 0, 3,                                !- X,Y,Z Vertex 2 {m}\n'
        '  1, 0, 3,                                !- X,Y,Z Vertex 3 {m}\n'
        '  1, 1, 3;                                !- X,Y,Z Vertex 4 {m}\n\n'
    )


def test_shade_mesh_writer():
    """Test the basic functionality of the ShadeMesh OpenStudio writer."""
    os_model = OSModel()
    pts = (Point3D(0, 0, 4), Point3D(0, 2, 4), Point3D(2, 2, 4),
           Point3D(2, 0, 4), Point3D(4, 0, 4))
    mesh = Mesh3D(pts, [(0, 1, 2, 3), (2, 3, 4)])
    shade = ShadeMesh('Awning_1', mesh)

    os_shades = shade_mesh_to_openstudio(shade, os_model)
    assert len(os_shades) == 2
    os_shade_str1 = str(os_shades[0])
    assert os_shade_str1.startswith('OS:ShadingSurface,')
    assert os_shade_str1.endswith(
        '  2, 2, 4,                                !- X,Y,Z Vertex 1 {m}\n'
        '  2, 0, 4,                                !- X,Y,Z Vertex 2 {m}\n'
        '  0, 0, 4,                                !- X,Y,Z Vertex 3 {m}\n'
        '  0, 2, 4;                                !- X,Y,Z Vertex 4 {m}\n\n'
    )
    os_shade_str2 = str(os_shades[1])
    assert os_shade_str2.startswith('OS:ShadingSurface,')
    assert os_shade_str2.endswith(
        '  2, 2, 4,                                !- X,Y,Z Vertex 1 {m}\n'
        '  2, 0, 4,                                !- X,Y,Z Vertex 2 {m}\n'
        '  4, 0, 4;                                !- X,Y,Z Vertex 3 {m}\n\n'
    )


def test_aperture_writer():
    """Test the basic functionality of the Aperture OpenStudio writer."""
    os_model = OSModel()
    vertices_parent_wall = [[0, 0, 0], [0, 10, 0], [0, 10, 3], [0, 0, 3]]
    vertices_wall = [[0, 1, 1], [0, 3, 1], [0, 3, 2.5], [0, 1, 2.5]]
    vertices_parent_roof = [[10, 0, 3], [10, 10, 3], [0, 10, 3], [0, 0, 3]]
    vertices_roof = [[4, 1, 3], [4, 4, 3], [1, 4, 3], [1, 1, 3]]

    wf = Face.from_vertices('wall_face', vertices_parent_wall)
    wa = Aperture.from_vertices('wall_window', vertices_wall)
    wf.add_aperture(wa)
    Room('Test_Room_1', [wf])
    os_ap = aperture_to_openstudio(wa, os_model)
    assert str(os_ap.name()) == 'wall_window'
    assert os_ap.subSurfaceType() == 'FixedWindow'
    os_ap_str = str(os_ap)
    assert os_ap_str.startswith('OS:SubSurface,')
    assert os_ap_str.endswith(
        '  0, 1, 2.5,                              !- X,Y,Z Vertex 1 {m}\n'
        '  0, 1, 1,                                !- X,Y,Z Vertex 2 {m}\n'
        '  0, 3, 1,                                !- X,Y,Z Vertex 3 {m}\n'
        '  0, 3, 2.5;                              !- X,Y,Z Vertex 4 {m}\n\n'
    )

    rf = Face.from_vertices('roof_face', vertices_parent_roof)
    ra = Aperture.from_vertices('roof_window', vertices_roof)
    rf.add_aperture(ra)
    Room('Test_Room_1', [rf])
    os_ap = aperture_to_openstudio(ra, os_model)
    assert str(os_ap.name()) == 'roof_window'
    assert os_ap.subSurfaceType() == 'Skylight'
    os_ap_str = str(os_ap)
    assert os_ap_str.startswith('OS:SubSurface,')
    assert os_ap_str.endswith(
        '  1, 4, 3,                                !- X,Y,Z Vertex 1 {m}\n'
        '  1, 1, 3,                                !- X,Y,Z Vertex 2 {m}\n'
        '  4, 1, 3,                                !- X,Y,Z Vertex 3 {m}\n'
        '  4, 4, 3;                                !- X,Y,Z Vertex 4 {m}\n\n'
    )


def test_door_writer():
    """Test the basic functionality of the Door OpenStudio writer."""
    os_model = OSModel()
    vertices_parent_wall = [[0, 0, 0], [0, 10, 0], [0, 10, 3], [0, 0, 3]]
    vertices_wall = [[0, 1, 0.1], [0, 2, 0.1], [0, 2, 2.8], [0, 1, 2.8]]
    vertices_parent_roof = [[10, 0, 3], [10, 10, 3], [0, 10, 3], [0, 0, 3]]
    vertices_roof = [[4, 3, 3], [4, 4, 3], [3, 4, 3], [3, 3, 3]]

    wf = Face.from_vertices('wall_face', vertices_parent_wall)
    wd = Door.from_vertices('wall_door', vertices_wall)
    wf.add_door(wd)
    Room('Test_Room_1', [wf])
    os_dr = door_to_openstudio(wd, os_model)
    assert str(os_dr.name()) == 'wall_door'
    assert os_dr.subSurfaceType() == 'Door'
    os_dr_str = str(os_dr)
    assert os_dr_str.startswith('OS:SubSurface,')
    assert os_dr_str.endswith(
        '  0, 1, 2.8,                              !- X,Y,Z Vertex 1 {m}\n'
        '  0, 1, 0.1,                              !- X,Y,Z Vertex 2 {m}\n'
        '  0, 2, 0.1,                              !- X,Y,Z Vertex 3 {m}\n'
        '  0, 2, 2.8;                              !- X,Y,Z Vertex 4 {m}\n\n'
    )

    rf = Face.from_vertices('roof_face', vertices_parent_roof)
    rd = Door.from_vertices('roof_door', vertices_roof)
    rf.add_door(rd)
    Room('Test_Room_1', [rf])
    os_dr = door_to_openstudio(rd, os_model)
    assert str(os_dr.name()) == 'roof_door'
    assert os_dr.subSurfaceType() == 'OverheadDoor'
    os_dr_str = str(os_dr)
    assert os_dr_str.startswith('OS:SubSurface,')
    assert os_dr_str.endswith(
        '  3, 4, 3,                                !- X,Y,Z Vertex 1 {m}\n'
        '  3, 3, 3,                                !- X,Y,Z Vertex 2 {m}\n'
        '  4, 3, 3,                                !- X,Y,Z Vertex 3 {m}\n'
        '  4, 4, 3;                                !- X,Y,Z Vertex 4 {m}\n\n'
    )


def test_face_writer():
    """Test the basic functionality of the Face OpenStudio writer."""
    os_model = OSModel()
    wall_pts = [[0, 0, 0], [10, 0, 0], [10, 0, 10], [0, 0, 10]]
    roof_pts = [[0, 0, 3], [10, 0, 3], [10, 10, 3], [0, 10, 3]]
    floor_pts = [[0, 0, 0], [0, 10, 0], [10, 10, 0], [10, 0, 0]]

    face = Face.from_vertices('wall_face', wall_pts)
    Room('Test_Room_1', [face])
    os_face = face_to_openstudio(face, os_model)
    assert str(os_face.name()) == 'wall_face'
    assert os_face.surfaceType() == 'Wall'
    assert os_face.outsideBoundaryCondition() == 'Outdoors'
    assert os_face.sunExposure() == 'SunExposed'
    assert os_face.windExposure() == 'WindExposed'
    os_face_str = str(os_face)
    assert os_face_str.startswith('OS:Surface,')
    assert os_face_str.endswith(
        '  0, 0, 10,                               !- X,Y,Z Vertex 1 {m}\n'
        '  0, 0, 0,                                !- X,Y,Z Vertex 2 {m}\n'
        '  10, 0, 0,                               !- X,Y,Z Vertex 3 {m}\n'
        '  10, 0, 10;                              !- X,Y,Z Vertex 4 {m}\n\n'
    )

    face = Face.from_vertices('roof_face', roof_pts)
    Room('Test_Room_1', [face])
    os_face = face_to_openstudio(face, os_model)
    assert str(os_face.name()) == 'roof_face'
    assert os_face.surfaceType() == 'RoofCeiling'
    assert os_face.outsideBoundaryCondition() == 'Outdoors'
    assert os_face.sunExposure() == 'SunExposed'
    assert os_face.windExposure() == 'WindExposed'
    os_face_str = str(os_face)
    assert os_face_str.startswith('OS:Surface,')
    assert os_face_str.endswith(
        '  0, 10, 3,                               !- X,Y,Z Vertex 1 {m}\n'
        '  0, 0, 3,                                !- X,Y,Z Vertex 2 {m}\n'
        '  10, 0, 3,                               !- X,Y,Z Vertex 3 {m}\n'
        '  10, 10, 3;                              !- X,Y,Z Vertex 4 {m}\n\n'
    )

    face = Face.from_vertices('floor_face', floor_pts)
    Room('Test_Room_1', [face])
    os_face = face_to_openstudio(face, os_model)
    assert str(os_face.name()) == 'floor_face'
    assert os_face.surfaceType() == 'Floor'
    assert os_face.outsideBoundaryCondition() == 'Ground'
    assert os_face.sunExposure() == 'NoSun'
    assert os_face.windExposure() == 'NoWind'
    os_face_str = str(os_face)
    assert os_face_str.startswith('OS:Surface,')
    assert os_face_str.endswith(
        '  10, 10, 0,                              !- X,Y,Z Vertex 1 {m}\n'
        '  10, 0, 0,                               !- X,Y,Z Vertex 2 {m}\n'
        '  0, 0, 0,                                !- X,Y,Z Vertex 3 {m}\n'
        '  0, 10, 0;                               !- X,Y,Z Vertex 4 {m}\n\n'
    )


def test_room_writer():
    """Test the basic functionality of the Room OpenStudio writer."""
    os_model = OSModel()
    room = Room.from_box('Tiny_House', 15, 30, 10)
    south_face = room[3]
    south_face.apertures_by_ratio(0.4, 0.01)
    south_face.apertures[0].overhang(0.5, indoor=False)
    south_face.apertures[0].overhang(0.5, indoor=True)
    south_face.apertures[0].move_shades(Vector3D(0, 0, -0.5))

    os_room = room_to_openstudio(room, os_model)
    assert str(os_room.name()) == 'Tiny_House_Space'

    spaces = os_model.getSpaces()
    faces = os_model.getSurfaces()
    sub_faces = os_model.getSubSurfaces()
    shades = os_model.getShadingSurfaces()
    assert os_vector_len(spaces) == 1
    assert os_vector_len(faces) == 6
    assert os_vector_len(sub_faces) == 1
    assert os_vector_len(shades) == 1


def test_model_writer():
    """Test the basic functionality of the Model OpenStudio writer."""
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

    model = Model('Tiny_House', [room], shade_meshes=[awning_1])

    os_model = model_to_openstudio(model)
    spaces = os_model.getSpaces()
    faces = os_model.getSurfaces()
    sub_faces = os_model.getSubSurfaces()
    shades = os_model.getShadingSurfaces()

    assert os_vector_len(spaces) == 1
    assert os_vector_len(faces) == 6
    assert os_vector_len(sub_faces) == 1
    assert os_vector_len(shades) == 3


def test_model_writer_dynamic_constructions():
    """Test the functionality of the Model OpenStudio writer with dynamic constructions."""
    room = Room.from_box('Tiny_House_Zone', 5, 10, 3)
    south_face = room[3]
    south_face.apertures_by_ratio(0.4, 0.01)
    south_face.apertures[0].overhang(0.5, indoor=False)
    south_face.apertures[0].overhang(0.5, indoor=True)
    south_face.apertures[0].move_shades(Vector3D(0, 0, -0.5))
    north_face = room[1]
    north_face.apertures_by_ratio(0.4, 0.01)
    roof = room[-1]
    roof.apertures_by_ratio(0.1, 0.01)

    lowe_glass = EnergyWindowMaterialGlazing(
        'Low-e Glass', 0.00318, 0.4517, 0.359, 0.714, 0.207,
        0, 0.84, 0.046578, 1.0)
    clear_glass = EnergyWindowMaterialGlazing(
        'Clear Glass', 0.005715, 0.770675, 0.07, 0.8836, 0.0804,
        0, 0.84, 0.84, 1.0)
    gap = EnergyWindowMaterialGas('air gap', thickness=0.03)
    tint_glass = EnergyWindowMaterialGlazing(
        'Tinted Low-e Glass', 0.00318, 0.09, 0.359, 0.16, 0.207,
        0, 0.84, 0.046578, 1.0)
    window_constr_off = WindowConstruction(
        'Double Low-E Clear', [lowe_glass, gap, clear_glass])
    window_constr_on = WindowConstruction(
        'Double Low-E Tint', [lowe_glass, gap, tint_glass])
    sched = ScheduleRuleset.from_daily_values(
        'NighSched', [1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 0, 1, 1, 1])
    double_low_e_ec = WindowConstructionDynamic(
        'Double Low-E EC', [window_constr_on, window_constr_off], sched)
    for skylight in roof.apertures:
        skylight.properties.energy.construction = double_low_e_ec

    model = Model('Tiny_House', [room])

    os_model = model_to_openstudio(model)
    ems_progs = os_model.getEnergyManagementSystemPrograms()
    assert os_vector_len(ems_progs) == 1


def test_model_writer_from_hbjson_with_zones():
    """Test translating a HBJSON to an OpenStudio string."""
    standard_test = 'assets/single_family_with_zones.hbjson'
    standard_test = os.path.join(os.path.dirname(__file__), standard_test)
    model = Model.from_file(standard_test)

    os_model = model_to_openstudio(model)
    spaces = os_model.getSpaces()
    zones = os_model.getThermalZones()

    assert os_vector_len(spaces) == 7
    assert os_vector_len(zones) == 4


def test_model_writer_from_standard_hbjson():
    """Test translating a HBJSON to an OpenStudio string."""
    standard_test = 'assets/2023_rac_advanced_sample_project.hbjson'
    standard_test = os.path.join(os.path.dirname(__file__), standard_test)
    model = Model.from_file(standard_test)

    os_model = model_to_openstudio(model)
    spaces = os_model.getSpaces()
    assert os_vector_len(spaces) == 102


def test_model_writer_from_complete_hbjson():
    """Test the translation of a Model with programs, constructions and HVAC to OSM."""
    standard_test = 'assets/sample_lab_building.hbjson'
    standard_test = os.path.join(os.path.dirname(__file__), standard_test)
    model = Model.from_file(standard_test)

    os_model = model_to_openstudio(model)
    spaces = os_model.getSpaces()
    assert os_vector_len(spaces) == 100
