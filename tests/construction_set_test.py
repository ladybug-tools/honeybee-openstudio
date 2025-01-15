# coding=utf-8
"""Test the translators for ConstructionSets to OpenStudio."""
from honeybee_energy.constructionset import ConstructionSet
from honeybee_energy.construction.opaque import OpaqueConstruction
from honeybee_energy.construction.window import WindowConstruction
from honeybee_energy.construction.shade import ShadeConstruction
from honeybee_energy.material.opaque import EnergyMaterial
from honeybee_energy.material.glazing import EnergyWindowMaterialGlazing
from honeybee_energy.material.gas import EnergyWindowMaterialGas
from honeybee_energy.lib.constructionsets import generic_construction_set

from honeybee_openstudio.openstudio import OSModel
from honeybee_openstudio.material import material_to_openstudio
from honeybee_openstudio.construction import construction_to_openstudio
from honeybee_openstudio.constructionset import construction_set_to_openstudio


def test_generic_construction_set_to_openstudio():
    """Test the translation of the default generic ConstructionSet to OpenStudio"""
    os_model = OSModel()
    for mat in generic_construction_set.materials_unique:
        material_to_openstudio(mat, os_model)
    for con in generic_construction_set.constructions_unique:
        construction_to_openstudio(con, os_model)
    os_con_set = construction_set_to_openstudio(generic_construction_set, os_model)

    assert str(os_con_set.name()) == 'Default Generic Construction Set'
    os_construction_str = str(os_con_set)
    assert os_construction_str.startswith('OS:DefaultConstructionSet,')
    assert os_con_set.defaultExteriorSurfaceConstructions().is_initialized()
    ext_set = os_con_set.defaultExteriorSurfaceConstructions().get()
    assert ext_set.floorConstruction().is_initialized()
    assert ext_set.wallConstruction().is_initialized()
    assert ext_set.roofCeilingConstruction().is_initialized()
    assert os_con_set.defaultInteriorSurfaceConstructions().is_initialized()
    int_set = os_con_set.defaultInteriorSurfaceConstructions().get()
    assert int_set.floorConstruction().is_initialized()
    assert int_set.wallConstruction().is_initialized()
    assert int_set.roofCeilingConstruction().is_initialized()
    assert os_con_set.defaultGroundContactSurfaceConstructions().is_initialized()
    gnd_set = os_con_set.defaultGroundContactSurfaceConstructions().get()
    assert gnd_set.floorConstruction().is_initialized()
    assert gnd_set.wallConstruction().is_initialized()
    assert gnd_set.roofCeilingConstruction().is_initialized()
    assert os_con_set.defaultExteriorSubSurfaceConstructions().is_initialized()
    ext_sub_set = os_con_set.defaultExteriorSubSurfaceConstructions().get()
    assert ext_sub_set.fixedWindowConstruction().is_initialized()
    assert ext_sub_set.operableWindowConstruction().is_initialized()
    assert ext_sub_set.doorConstruction().is_initialized()
    assert ext_sub_set.glassDoorConstruction().is_initialized()
    assert ext_sub_set.overheadDoorConstruction().is_initialized()
    assert ext_sub_set.skylightConstruction().is_initialized()
    assert os_con_set.defaultInteriorSubSurfaceConstructions().is_initialized()
    int_sub_set = os_con_set.defaultInteriorSubSurfaceConstructions().get()
    assert int_sub_set.fixedWindowConstruction().is_initialized()
    assert int_sub_set.operableWindowConstruction().is_initialized()
    assert int_sub_set.doorConstruction().is_initialized()
    assert int_sub_set.glassDoorConstruction().is_initialized()
    assert int_sub_set.overheadDoorConstruction().is_initialized()
    assert int_sub_set.skylightConstruction().is_initialized()
    assert os_con_set.adiabaticSurfaceConstruction().is_initialized()
    assert os_con_set.spaceShadingConstruction().is_initialized()


def test_custom_opaque_construction_set_to_openstudio():
    """Test the translation of a custom ConstructionSet to OpenStudio."""
    os_model = OSModel()
    default_set = ConstructionSet('Thermal Mass Construction Set')
    concrete20 = EnergyMaterial('20cm Concrete', 0.2, 2.31, 2322, 832,
                                'MediumRough', 0.95, 0.75, 0.8)
    concrete10 = EnergyMaterial('10cm Concrete', 0.1, 2.31, 2322, 832,
                                'MediumRough', 0.95, 0.75, 0.8)
    stone_door = EnergyMaterial('Stone Door', 0.05, 2.31, 2322, 832,
                                'MediumRough', 0.95, 0.75, 0.8)
    thick_constr = OpaqueConstruction(
        'Thick Concrete Construction', [concrete20])
    thin_constr = OpaqueConstruction(
        'Thin Concrete Construction', [concrete10])
    door_constr = OpaqueConstruction(
        'Stone Door', [stone_door])
    light_shelf = ShadeConstruction('Light Shelf', 0.5, 0.5, True)

    default_set.wall_set.exterior_construction = thick_constr
    default_set.wall_set.interior_construction = thin_constr
    default_set.wall_set.ground_construction = thick_constr
    default_set.floor_set.exterior_construction = thick_constr
    default_set.floor_set.interior_construction = thin_constr
    default_set.floor_set.ground_construction = thick_constr
    default_set.roof_ceiling_set.exterior_construction = thick_constr
    default_set.roof_ceiling_set.interior_construction = thin_constr
    default_set.roof_ceiling_set.ground_construction = thick_constr
    default_set.door_set.exterior_construction = door_constr
    default_set.door_set.interior_construction = door_constr
    default_set.door_set.overhead_construction = door_constr
    default_set.shade_construction = light_shelf

    for mat in default_set.materials_unique:
        material_to_openstudio(mat, os_model)
    for con in default_set.constructions_unique:
        construction_to_openstudio(con, os_model)
    os_con_set = construction_set_to_openstudio(default_set, os_model)

    assert str(os_con_set.name()) == 'Thermal Mass Construction Set'
    os_construction_str = str(os_con_set)
    assert os_construction_str.startswith('OS:DefaultConstructionSet,')
    assert os_con_set.defaultExteriorSurfaceConstructions().is_initialized()
    ext_set = os_con_set.defaultExteriorSurfaceConstructions().get()
    assert ext_set.floorConstruction().is_initialized()
    assert ext_set.wallConstruction().is_initialized()
    assert ext_set.roofCeilingConstruction().is_initialized()
    assert os_con_set.defaultInteriorSurfaceConstructions().is_initialized()
    int_set = os_con_set.defaultInteriorSurfaceConstructions().get()
    assert int_set.floorConstruction().is_initialized()
    assert int_set.wallConstruction().is_initialized()
    assert int_set.roofCeilingConstruction().is_initialized()
    assert os_con_set.defaultGroundContactSurfaceConstructions().is_initialized()
    gnd_set = os_con_set.defaultGroundContactSurfaceConstructions().get()
    assert gnd_set.floorConstruction().is_initialized()
    assert gnd_set.wallConstruction().is_initialized()
    assert gnd_set.roofCeilingConstruction().is_initialized()
    assert os_con_set.defaultExteriorSubSurfaceConstructions().is_initialized()
    ext_sub_set = os_con_set.defaultExteriorSubSurfaceConstructions().get()
    assert not ext_sub_set.fixedWindowConstruction().is_initialized()
    assert not ext_sub_set.operableWindowConstruction().is_initialized()
    assert ext_sub_set.doorConstruction().is_initialized()
    assert not ext_sub_set.glassDoorConstruction().is_initialized()
    assert ext_sub_set.overheadDoorConstruction().is_initialized()
    assert not ext_sub_set.skylightConstruction().is_initialized()
    assert os_con_set.defaultInteriorSubSurfaceConstructions().is_initialized()
    int_sub_set = os_con_set.defaultInteriorSubSurfaceConstructions().get()
    assert not int_sub_set.fixedWindowConstruction().is_initialized()
    assert not int_sub_set.operableWindowConstruction().is_initialized()
    assert int_sub_set.doorConstruction().is_initialized()
    assert not int_sub_set.glassDoorConstruction().is_initialized()
    assert int_sub_set.overheadDoorConstruction().is_initialized()
    assert not int_sub_set.skylightConstruction().is_initialized()
    assert os_con_set.adiabaticSurfaceConstruction().is_initialized()
    assert os_con_set.spaceShadingConstruction().is_initialized()


def test_custom_window_construction_set_to_openstudio():
    """Test the translation of a custom ConstructionSet to OpenStudio."""
    os_model = OSModel()
    default_set = ConstructionSet('Tinted Window Set')
    tinted_glass = EnergyWindowMaterialGlazing(
        'Tinted Glass', 0.006, 0.35, 0.03, 0.884, 0.0804, 0, 0.84, 0.84, 1.0)
    gap = EnergyWindowMaterialGas('Window Air Gap', thickness=0.0127)
    double_tint = WindowConstruction(
        'Double Tinted Window', [tinted_glass, gap, tinted_glass])
    single_tint = WindowConstruction(
        'Single Tinted Window', [tinted_glass])

    default_set.aperture_set.window_construction = double_tint
    default_set.aperture_set.interior_construction = single_tint
    default_set.aperture_set.skylight_construction = double_tint
    default_set.aperture_set.operable_construction = double_tint
    default_set.door_set.exterior_glass_construction = double_tint
    default_set.door_set.interior_glass_construction = single_tint

    for mat in default_set.materials_unique:
        material_to_openstudio(mat, os_model)
    for con in default_set.constructions_unique:
        construction_to_openstudio(con, os_model)
    os_con_set = construction_set_to_openstudio(default_set, os_model)

    assert str(os_con_set.name()) == 'Tinted Window Set'
    os_construction_str = str(os_con_set)
    assert os_construction_str.startswith('OS:DefaultConstructionSet,')
    assert os_con_set.defaultExteriorSurfaceConstructions().is_initialized()
    ext_set = os_con_set.defaultExteriorSurfaceConstructions().get()
    assert not ext_set.floorConstruction().is_initialized()
    assert not ext_set.wallConstruction().is_initialized()
    assert not ext_set.roofCeilingConstruction().is_initialized()
    assert os_con_set.defaultInteriorSurfaceConstructions().is_initialized()
    int_set = os_con_set.defaultInteriorSurfaceConstructions().get()
    assert not int_set.floorConstruction().is_initialized()
    assert not int_set.wallConstruction().is_initialized()
    assert not int_set.roofCeilingConstruction().is_initialized()
    assert os_con_set.defaultGroundContactSurfaceConstructions().is_initialized()
    gnd_set = os_con_set.defaultGroundContactSurfaceConstructions().get()
    assert not gnd_set.floorConstruction().is_initialized()
    assert not gnd_set.wallConstruction().is_initialized()
    assert not gnd_set.roofCeilingConstruction().is_initialized()
    assert os_con_set.defaultExteriorSubSurfaceConstructions().is_initialized()
    ext_sub_set = os_con_set.defaultExteriorSubSurfaceConstructions().get()
    assert ext_sub_set.fixedWindowConstruction().is_initialized()
    assert ext_sub_set.operableWindowConstruction().is_initialized()
    assert not ext_sub_set.doorConstruction().is_initialized()
    assert ext_sub_set.glassDoorConstruction().is_initialized()
    assert not ext_sub_set.overheadDoorConstruction().is_initialized()
    assert ext_sub_set.skylightConstruction().is_initialized()
    assert os_con_set.defaultInteriorSubSurfaceConstructions().is_initialized()
    int_sub_set = os_con_set.defaultInteriorSubSurfaceConstructions().get()
    assert int_sub_set.fixedWindowConstruction().is_initialized()
    assert int_sub_set.operableWindowConstruction().is_initialized()
    assert not int_sub_set.doorConstruction().is_initialized()
    assert int_sub_set.glassDoorConstruction().is_initialized()
    assert not int_sub_set.overheadDoorConstruction().is_initialized()
    assert int_sub_set.skylightConstruction().is_initialized()
    assert not os_con_set.adiabaticSurfaceConstruction().is_initialized()
    assert not os_con_set.spaceShadingConstruction().is_initialized()
