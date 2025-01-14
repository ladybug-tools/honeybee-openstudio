# coding=utf-8
"""Test the translators for materials to OpenStudio."""
from honeybee_energy.material.opaque import EnergyMaterial, EnergyMaterialNoMass, \
    EnergyMaterialVegetation
from honeybee_energy.material.glazing import EnergyWindowMaterialGlazing, \
    EnergyWindowMaterialSimpleGlazSys
from honeybee_energy.material.gas import EnergyWindowMaterialGas, \
    EnergyWindowMaterialGasMixture, EnergyWindowMaterialGasCustom
from honeybee_energy.material.frame import EnergyWindowFrame
from honeybee_energy.material.shade import EnergyWindowMaterialShade, \
    EnergyWindowMaterialBlind

from honeybee_openstudio.openstudio import OSModel
from honeybee_openstudio.material import material_to_openstudio


def test_opaque_material_to_openstudio():
    """Test the basic functionality of the EnergyMaterial."""
    os_model = OSModel()
    concrete = EnergyMaterial('Concrete', 0.2, 0.5, 800, 1200,
                              'MediumSmooth', 0.95, 0.75, 0.8)

    os_material = material_to_openstudio(concrete, os_model)
    assert str(os_material.name()) == 'Concrete'
    os_material_str = str(os_material)
    assert os_material_str.startswith('OS:Material,')


def test_opaque_no_mass_material_to_openstudio():
    """Test the basic functionality of the EnergyMaterialNoMass."""
    os_model = OSModel()
    insul_r2 = EnergyMaterialNoMass('Insulation R-2', 2,
                                    'MediumSmooth', 0.95, 0.75, 0.8)

    os_material = material_to_openstudio(insul_r2, os_model)
    assert str(os_material.name()) == 'Insulation R-2'
    os_material_str = str(os_material)
    assert os_material_str.startswith('OS:Material:NoMass,')


def test_vegetation_material_to_openstudio():
    """Test the basic functionality of the EnergyMaterialVegetation."""
    os_model = OSModel()
    g_roof = EnergyMaterialVegetation(
        'roofmcroofface', 0.5, 0.45, 1250, 950, 'Rough',
        0.89, 0.65, 0.7, 0.5, 2, 0.35, 0.9, 275)

    os_material = material_to_openstudio(g_roof, os_model)
    assert str(os_material.name()) == 'roofmcroofface'
    os_material_str = str(os_material)
    assert os_material_str.startswith('OS:Material:RoofVegetation,')


def test_glazing_material_to_openstudio():
    """Test the basic functionality of the EnergyWindowMaterialGlazing."""
    os_model = OSModel()
    lowe = EnergyWindowMaterialGlazing(
        'Low-e Glass', 0.00318, 0.4517, 0.359, 0.714, 0.207,
        0, 0.84, 0.046578, 1.0)

    os_material = material_to_openstudio(lowe, os_model)
    assert str(os_material.name()) == 'Low-e Glass'
    os_material_str = str(os_material)
    assert os_material_str.startswith('OS:WindowMaterial:Glazing,')


def test_simple_glazing_sys_material_to_openstudio():
    """Test the basic functionality of the EnergyWindowMaterialSimpleGlazSys."""
    os_model = OSModel()
    lowe_sys = EnergyWindowMaterialSimpleGlazSys(
        'Double Pane Low-e', 1.8, 0.35, 0.55)

    os_material = material_to_openstudio(lowe_sys, os_model)
    assert str(os_material.name()) == 'Double Pane Low-e'
    os_material_str = str(os_material)
    assert os_material_str.startswith('OS:WindowMaterial:SimpleGlazingSystem,')


def test_gas_material_to_openstudio():
    """Test the basic functionality of the EnergyWindowMaterialGas."""
    os_model = OSModel()
    air = EnergyWindowMaterialGas('Air Gap', 0.0125, 'Air')

    os_material = material_to_openstudio(air, os_model)
    assert str(os_material.name()) == 'Air Gap'
    os_material_str = str(os_material)
    assert os_material_str.startswith('OS:WindowMaterial:Gas,')


def test_gas_mixture_material_to_openstudio():
    """Test the basic functionality of the EnergyWindowMaterialGas."""
    os_model = OSModel()
    air_argon = EnergyWindowMaterialGasMixture(
        'Air Argon Gap', 0.0125, ('Air', 'Argon'), (0.1, 0.9))

    os_material = material_to_openstudio(air_argon, os_model)
    assert str(os_material.name()) == 'Air Argon Gap'
    os_material_str = str(os_material)
    assert os_material_str.startswith('OS:WindowMaterial:GasMixture,')


def test_gas_custom_material_to_openstudio():
    """Test the basic functionality of the EnergyWindowMaterialGasCustom."""
    os_model = OSModel()
    co2_gap = EnergyWindowMaterialGasCustom('CO2', 0.0125, 0.0146, 0.000014, 827.73)
    co2_gap.specific_heat_ratio = 1.4
    co2_gap.molecular_weight = 44

    os_material = material_to_openstudio(co2_gap, os_model)
    assert str(os_material.name()) == 'CO2'
    os_material_str = str(os_material)
    assert os_material_str.startswith('OS:WindowMaterial:Gas,')


def test_shade_material_to_openstudio():
    """Test the basic functionality of the EnergyWindowMaterialShade."""
    os_model = OSModel()
    shade_mat = EnergyWindowMaterialShade(
        'Low-e Diffusing Shade', 0.025, 0.15, 0.5, 0.25, 0.5, 0, 0.4,
        0.2, 0.1, 0.75, 0.25)

    os_material = material_to_openstudio(shade_mat, os_model)
    assert str(os_material.name()) == 'Low-e Diffusing Shade'
    os_material_str = str(os_material)
    assert os_material_str.startswith('OS:WindowMaterial:Shade,')


def test_blind_material_to_openstudio():
    """Test the basic functionality of the EnergyWindowMaterialBlind."""
    os_model = OSModel()
    shade_mat = EnergyWindowMaterialBlind(
        'Plastic Blind', 'Vertical', 0.025, 0.01875, 0.003, 90, 0.2, 0.05, 0.4,
        0.05, 0.45, 0, 0.95, 0.1, 1)

    os_material = material_to_openstudio(shade_mat, os_model)
    assert str(os_material.name()) == 'Plastic Blind'
    os_material_str = str(os_material)
    assert os_material_str.startswith('OS:WindowMaterial:Blind,')


def test_frame_material_to_openstudio():
    """Test the basic functionality of the EnergyWindowFrame."""
    os_model = OSModel()
    wood_frame = EnergyWindowFrame(
        'Wood_Frame_050_032', 0.05, 3.2, 2.6, 0.05, 0.1, 0.95, 0.75, 0.8)

    os_material = material_to_openstudio(wood_frame, os_model)
    assert str(os_material.name()) == 'Wood_Frame_050_032'
    os_material_str = str(os_material)
    assert os_material_str.startswith('OS:WindowProperty:FrameAndDivider,')
