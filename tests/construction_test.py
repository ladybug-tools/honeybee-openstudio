# coding=utf-8
"""Test the translators for constructions to OpenStudio."""
import sys

from honeybee_energy.material.opaque import EnergyMaterial, EnergyMaterialNoMass
from honeybee_energy.material.glazing import EnergyWindowMaterialGlazing
from honeybee_energy.material.gas import EnergyWindowMaterialGas
from honeybee_energy.material.shade import EnergyWindowMaterialShade, \
    EnergyWindowMaterialBlind
from honeybee_energy.construction.opaque import OpaqueConstruction
from honeybee_energy.construction.window import WindowConstruction
from honeybee_energy.construction.windowshade import WindowConstructionShade
from honeybee_energy.construction.dynamic import WindowConstructionDynamic
from honeybee_energy.construction.shade import ShadeConstruction
from honeybee_energy.construction.air import AirBoundaryConstruction
from honeybee_energy.schedule.ruleset import ScheduleRuleset

from honeybee_openstudio.openstudio import OSModel
from honeybee_openstudio.schedule import schedule_to_openstudio
from honeybee_openstudio.material import material_to_openstudio
from honeybee_openstudio.construction import construction_to_openstudio


def test_opaque_construction_to_openstudio():
    """Test the translation of OpaqueConstruction to OpenStudio."""
    os_model = OSModel()
    concrete = EnergyMaterial('Concrete', 0.15, 2.31, 2322, 832, 'MediumRough',
                              0.95, 0.75, 0.8)
    insulation = EnergyMaterialNoMass('Insulation R-3', 3, 'MediumSmooth')
    wall_gap = EnergyMaterial('Wall Air Gap', 0.1, 0.67, 1.2925, 1006.1)
    gypsum = EnergyMaterial('Gypsum', 0.0127, 0.16, 784.9, 830, 'MediumRough',
                            0.93, 0.6, 0.65)
    wall_constr = OpaqueConstruction(
        'Generic Wall Construction', [concrete, insulation, wall_gap, gypsum])

    material_to_openstudio(concrete, os_model)
    material_to_openstudio(insulation, os_model)
    material_to_openstudio(wall_gap, os_model)
    material_to_openstudio(gypsum, os_model)
    os_construction = construction_to_openstudio(wall_constr, os_model)
    assert str(os_construction.name()) == 'Generic Wall Construction'
    os_construction_str = str(os_construction)
    assert os_construction_str.startswith('OS:Construction,')

    materials = os_construction.layers()
    if (sys.version_info >= (3, 0)):  # we are in cPython
        assert len(materials) == 4
    else:
        assert materials.Count == 4


def test_window_construction_to_openstudio():
    """Test the translation of WindowConstruction to OpenStudio."""
    os_model = OSModel()
    lowe_glass = EnergyWindowMaterialGlazing(
        'Low-e Glass', 0.00318, 0.4517, 0.359, 0.714, 0.207,
        0, 0.84, 0.046578, 1.0)
    clear_glass = EnergyWindowMaterialGlazing(
        'Clear Glass', 0.005715, 0.770675, 0.07, 0.8836, 0.0804,
        0, 0.84, 0.84, 1.0)
    gap = EnergyWindowMaterialGas('air gap', thickness=0.0127)
    double_low_e = WindowConstruction(
        'Double Low-E Window', [lowe_glass, gap, clear_glass])
    triple_clear = WindowConstruction(
        'Triple Clear Window', [clear_glass, gap, clear_glass, gap, clear_glass])

    material_to_openstudio(lowe_glass, os_model)
    material_to_openstudio(clear_glass, os_model)
    material_to_openstudio(gap, os_model)

    os_construction = construction_to_openstudio(double_low_e, os_model)
    assert str(os_construction.name()) == 'Double Low-E Window'
    os_construction_str = str(os_construction)
    assert os_construction_str.startswith('OS:Construction,')
    materials = os_construction.layers()
    if (sys.version_info >= (3, 0)):  # we are in cPython
        assert len(materials) == 3
    else:
        assert materials.Count == 3

    os_construction = construction_to_openstudio(triple_clear, os_model)
    assert str(os_construction.name()) == 'Triple Clear Window'
    os_construction_str = str(os_construction)
    assert os_construction_str.startswith('OS:Construction,')
    materials = os_construction.layers()
    if (sys.version_info >= (3, 0)):  # we are in cPython
        assert len(materials) == 5
    else:
        assert materials.Count == 5


def test_window_simple_construction_to_openstudio():
    """Test the translation of a simple WindowConstruction to OpenStudio."""
    os_model = OSModel()
    double_low_e = WindowConstruction.from_simple_parameters(
        'NECB Window Construction', 1.7, 0.4)
    for mat in double_low_e.materials:
        material_to_openstudio(mat, os_model)

    os_construction = construction_to_openstudio(double_low_e, os_model)
    assert str(os_construction.name()) == 'NECB Window Construction'
    os_construction_str = str(os_construction)
    assert os_construction_str.startswith('OS:Construction,')
    materials = os_construction.layers()
    if (sys.version_info >= (3, 0)):  # we are in cPython
        assert len(materials) == 1
    else:
        assert materials.Count == 1


def test_window_construction_shade_to_openstudio():
    """Test the translation of a WindowConstructionShade to OpenStudio."""
    os_model = OSModel()
    lowe_glass = EnergyWindowMaterialGlazing(
        'Low-e Glass', 0.00318, 0.4517, 0.359, 0.714, 0.207,
        0, 0.84, 0.046578, 1.0)
    clear_glass = EnergyWindowMaterialGlazing(
        'Clear Glass', 0.005715, 0.770675, 0.07, 0.8836, 0.0804,
        0, 0.84, 0.84, 1.0)
    gap = EnergyWindowMaterialGas('air gap', thickness=0.0127)
    shade_mat = EnergyWindowMaterialShade(
        'Low-e Diffusing Shade', 0.005, 0.15, 0.5, 0.25, 0.5, 0, 0.4,
        0.2, 0.1, 0.75, 0.25)
    window_constr = WindowConstruction('Double Low-E', [lowe_glass, gap, clear_glass])
    window_clear = WindowConstruction('Double Low-E', [clear_glass, gap, clear_glass])
    sched = ScheduleRuleset.from_daily_values(
        'NighSched', [1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 0, 1, 1, 1])

    double_low_e_shade = WindowConstructionShade(
        'Double Low-E with Shade', window_constr, shade_mat, 'Exterior',
        'OnIfHighSolarOnWindow', 200, sched)
    double_low_e_between_shade = WindowConstructionShade(
        'Double Low-E Between Shade', window_clear, shade_mat, 'Between')
    double_ext_shade = WindowConstructionShade(
        'Double Outside Shade', window_clear, shade_mat, 'Interior')

    material_to_openstudio(lowe_glass, os_model)
    material_to_openstudio(clear_glass, os_model)
    material_to_openstudio(gap, os_model)
    material_to_openstudio(shade_mat, os_model)
    schedule_to_openstudio(sched, os_model)

    os_construction = construction_to_openstudio(double_low_e_shade, os_model)
    assert str(os_construction.name()) == 'Double Low-E with Shade'
    os_construction_str = str(os_construction)
    assert os_construction_str.startswith('OS:Construction,')
    materials = os_construction.layers()
    if (sys.version_info >= (3, 0)):  # we are in cPython
        assert len(materials) == 4
    else:
        assert materials.Count == 4

    os_construction = construction_to_openstudio(double_low_e_between_shade, os_model)
    assert str(os_construction.name()) == 'Double Low-E Between Shade'
    os_construction_str = str(os_construction)
    assert os_construction_str.startswith('OS:Construction,')
    materials = os_construction.layers()
    if (sys.version_info >= (3, 0)):  # we are in cPython
        assert len(materials) == 5
    else:
        assert materials.Count == 5

    os_construction = construction_to_openstudio(double_ext_shade, os_model)
    assert str(os_construction.name()) == 'Double Outside Shade'
    os_construction_str = str(os_construction)
    assert os_construction_str.startswith('OS:Construction,')
    materials = os_construction.layers()
    if (sys.version_info >= (3, 0)):  # we are in cPython
        assert len(materials) == 4
    else:
        assert materials.Count == 4


def test_window_construction_blind_to_openstudio():
    """Test the translation of a WindowConstructionShade with a blind to OpenStudio."""
    os_model = OSModel()
    lowe_glass = EnergyWindowMaterialGlazing(
        'Low-e Glass', 0.00318, 0.4517, 0.359, 0.714, 0.207,
        0, 0.84, 0.046578, 1.0)
    clear_glass = EnergyWindowMaterialGlazing(
        'Clear Glass', 0.005715, 0.770675, 0.07, 0.8836, 0.0804,
        0, 0.84, 0.84, 1.0)
    gap = EnergyWindowMaterialGas('air gap', thickness=0.03)
    shade_mat = EnergyWindowMaterialBlind(
        'Plastic Blind', 'Vertical', 0.025, 0.01875, 0.003, 90, 0.2, 0.05, 0.4,
        0.05, 0.45, 0, 0.95, 0.1, 1)
    window_constr = WindowConstruction('Double Low-E', [lowe_glass, gap, clear_glass])
    window_clear = WindowConstruction('Double Low-E', [clear_glass, gap, clear_glass])
    sched = ScheduleRuleset.from_daily_values(
        'NighSched', [1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 0, 1, 1, 1])
    double_low_e_shade = WindowConstructionShade(
        'Double Low-E with Blind', window_constr, shade_mat, 'Exterior',
        'OnIfHighSolarOnWindow', 200, sched)
    double_low_e_between_shade = WindowConstructionShade(
        'Double Low-E Between Blind', window_clear, shade_mat, 'Between')
    double_low_e_ext_shade = WindowConstructionShade(
        'Double Low-E Outside Blind', window_constr, shade_mat, 'Interior')

    material_to_openstudio(lowe_glass, os_model)
    material_to_openstudio(clear_glass, os_model)
    material_to_openstudio(gap, os_model)
    material_to_openstudio(shade_mat, os_model)
    schedule_to_openstudio(sched, os_model)

    os_construction = construction_to_openstudio(double_low_e_shade, os_model)
    assert str(os_construction.name()) == 'Double Low-E with Blind'
    os_construction_str = str(os_construction)
    assert os_construction_str.startswith('OS:Construction,')
    materials = os_construction.layers()
    if (sys.version_info >= (3, 0)):  # we are in cPython
        assert len(materials) == 4
    else:
        assert materials.Count == 4

    os_construction = construction_to_openstudio(double_low_e_between_shade, os_model)
    assert str(os_construction.name()) == 'Double Low-E Between Blind'
    os_construction_str = str(os_construction)
    assert os_construction_str.startswith('OS:Construction,')
    materials = os_construction.layers()
    if (sys.version_info >= (3, 0)):  # we are in cPython
        assert len(materials) == 5
    else:
        assert materials.Count == 5

    os_construction = construction_to_openstudio(double_low_e_ext_shade, os_model)
    assert str(os_construction.name()) == 'Double Low-E Outside Blind'
    os_construction_str = str(os_construction)
    assert os_construction_str.startswith('OS:Construction,')
    materials = os_construction.layers()
    if (sys.version_info >= (3, 0)):  # we are in cPython
        assert len(materials) == 4
    else:
        assert materials.Count == 4


def test_window_construction_ec_to_openstudio():
    """Test the translation of electrochromic WindowConstruction to OpenStudio."""
    os_model = OSModel()
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
    window_constr = WindowConstruction('Double Low-E', [lowe_glass, gap, clear_glass])
    sched = ScheduleRuleset.from_daily_values(
        'NighSched', [1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 0, 1, 1, 1])
    double_low_e_ec = WindowConstructionShade(
        'Double Low-E Inside EC', window_constr, tint_glass, 'Exterior',
        'OnIfHighSolarOnWindow', 200, sched)
    double_low_e_between_ec = WindowConstructionShade(
        'Double Low-E Between EC', window_constr, tint_glass, 'Between')
    double_low_e_ext_ec = WindowConstructionShade(
        'Double Low-E Outside EC', window_constr, tint_glass, 'Interior')

    material_to_openstudio(lowe_glass, os_model)
    material_to_openstudio(clear_glass, os_model)
    material_to_openstudio(gap, os_model)
    material_to_openstudio(tint_glass, os_model)
    schedule_to_openstudio(sched, os_model)

    os_construction = construction_to_openstudio(double_low_e_ec, os_model)
    assert str(os_construction.name()) == 'Double Low-E Inside EC'
    os_construction_str = str(os_construction)
    assert os_construction_str.startswith('OS:Construction,')
    materials = os_construction.layers()
    if (sys.version_info >= (3, 0)):  # we are in cPython
        assert len(materials) == 3
    else:
        assert materials.Count == 3

    os_construction = construction_to_openstudio(double_low_e_between_ec, os_model)
    assert str(os_construction.name()) == 'Double Low-E Between EC'
    os_construction_str = str(os_construction)
    assert os_construction_str.startswith('OS:Construction,')
    materials = os_construction.layers()
    if (sys.version_info >= (3, 0)):  # we are in cPython
        assert len(materials) == 3
    else:
        assert materials.Count == 3

    os_construction = construction_to_openstudio(double_low_e_ext_ec, os_model)
    assert str(os_construction.name()) == 'Double Low-E Outside EC'
    os_construction_str = str(os_construction)
    assert os_construction_str.startswith('OS:Construction,')
    materials = os_construction.layers()
    if (sys.version_info >= (3, 0)):  # we are in cPython
        assert len(materials) == 3
    else:
        assert materials.Count == 3


def test_window_construction_dynamic_to_openstudio():
    """Test the translation of WindowConstructionDynamic to OpenStudio."""
    os_model = OSModel()
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

    material_to_openstudio(lowe_glass, os_model)
    material_to_openstudio(clear_glass, os_model)
    material_to_openstudio(gap, os_model)
    material_to_openstudio(tint_glass, os_model)
    schedule_to_openstudio(sched, os_model)

    os_constructions = construction_to_openstudio(double_low_e_ec, os_model)
    assert len(os_constructions) == 2
    for os_construction in os_constructions:
        assert str(os_construction.name()).startswith('Double Low-E')
        os_construction_str = str(os_construction)
        assert os_construction_str.startswith('OS:Construction,')
        materials = os_construction.layers()
        if (sys.version_info >= (3, 0)):  # we are in cPython
            assert len(materials) == 3
        else:
            assert materials.Count == 3


def test_shade_construction_to_openstudio():
    """Test the translation of a ShadeConstruction to OpenStudio."""
    os_model = OSModel()
    light_shelf_in = ShadeConstruction('Indoor Light Shelf', 0.5, 0.6)
    light_shelf_out = ShadeConstruction('Outdoor Light Shelf', 0.5, 0.6, True)

    os_construction = construction_to_openstudio(light_shelf_in, os_model)
    assert str(os_construction.name()) == 'Indoor Light Shelf'
    os_construction_str = str(os_construction)
    assert os_construction_str.startswith('OS:Construction,')

    os_construction = construction_to_openstudio(light_shelf_out, os_model)
    assert str(os_construction.name()) == 'Outdoor Light Shelf'
    os_construction_str = str(os_construction)
    assert os_construction_str.startswith('OS:Construction,')


def test_air_construction_to_openstudio():
    """Test the translation of AirBoundaryConstruction to OpenStudio."""
    os_model = OSModel()
    night_flush = ScheduleRuleset.from_daily_values(
        'Night Flush', [1, 1, 1, 1, 1, 1, 1, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5,
                        0.5, 0.5, 0.5, 0.5, 0.5, 1, 1, 1])
    night_flush_constr = AirBoundaryConstruction('Night Flush Boundary', 0.4, night_flush)

    schedule_to_openstudio(night_flush, os_model)

    os_construction = construction_to_openstudio(night_flush_constr, os_model)
    assert str(os_construction.name()) == 'Night Flush Boundary'
    os_construction_str = str(os_construction)
    assert os_construction_str.startswith('OS:Construction:AirBoundary,')
