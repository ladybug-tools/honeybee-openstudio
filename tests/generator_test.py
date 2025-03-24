# coding=utf-8
"""Test the translators for photovoltaics and generators to OpenStudio."""
from ladybug_geometry.geometry3d import Vector3D
from honeybee.shade import Shade
from honeybee.room import Room
from honeybee.model import Model
from honeybee_energy.generator.pv import PVProperties
from honeybee_energy.generator.loadcenter import ElectricLoadCenter

from honeybee_openstudio.openstudio import OSModel, os_vector_len
from honeybee_openstudio.writer import model_to_openstudio, shade_to_openstudio


def test_pv_properties_to_openstudio():
    """Test the translation of PVProperties to OpenStudio."""
    os_model = OSModel()
    shade = Shade.from_vertices(
        'pv_shade_object', [[0, 0, 1], [10, 0, 1], [10, 1, 2], [0, 1, 2]])
    pv_props = PVProperties('Standard PV Product')
    shade.properties.energy.pv_properties = pv_props

    shade_to_openstudio(shade, os_model)
    os_pv_gens = os_model.getGeneratorPVWattss()
    assert os_vector_len(os_pv_gens) == 1
    os_pv_gen = os_pv_gens[0]
    assert str(os_pv_gen.name()) == 'Standard PV Product..pv_shade_object'
    os_pv_gen_str = str(os_pv_gen)
    assert os_pv_gen_str.startswith('OS:Generator:PVWatts,')


def test_electric_load_center_to_openstudio():
    """Test the translation of ElectricLoadCenter to OpenStudio."""
    room = Room.from_box('Tiny_House_Zone', 5, 10, 3)
    south_face = room[3]
    south_face.apertures_by_ratio(0.4, 0.01)
    pv_overhangs = south_face.apertures[0].overhang(0.5, indoor=False)
    south_face.apertures[0].overhang(0.5, indoor=True)
    south_face.apertures[0].move_shades(Vector3D(0, 0, -0.5))
    pv_props = PVProperties('Standard PV Product')
    pv_overhangs[0].properties.energy.pv_properties = pv_props
    model = Model('Tiny_House', [room])
    load_center = ElectricLoadCenter(0.98, 1.2)
    model.properties.energy.electric_load_center = load_center

    os_model = model_to_openstudio(model)
    os_pv_gens = os_model.getGeneratorPVWattss()
    assert os_vector_len(os_pv_gens) == 1

    os_load_centers = os_model.getElectricLoadCenterDistributions()
    assert os_vector_len(os_load_centers) == 1
    os_load_center = os_load_centers[0]
    assert str(os_load_center.name()) == 'Model Load Center Distribution'
    os_load_center_str = str(os_load_center)
    assert os_load_center_str.startswith('OS:ElectricLoadCenter:Distribution,')
    os_inverter = os_load_center.inverter()
    assert os_inverter.is_initialized()
    os_inverter = os_inverter.get()
    os_inverter_str = str(os_inverter)
    assert os_inverter_str.startswith('OS:ElectricLoadCenter:Inverter:PVWatts,')
