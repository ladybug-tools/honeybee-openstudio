# coding=utf-8
"""Test the translators for InternalMass to OpenStudio."""
from honeybee_energy.internalmass import InternalMass
from honeybee_energy.construction.opaque import OpaqueConstruction
from honeybee_energy.material.opaque import EnergyMaterial

from honeybee_openstudio.openstudio import OSModel
from honeybee_openstudio.construction import material_to_openstudio, \
    construction_to_openstudio
from honeybee_openstudio.internalmass import internal_mass_to_openstudio


def test_internal_mass_to_openstudio():
    """Test the translation of InternalMass to OpenStudio."""
    os_model = OSModel()
    rammed_earth = EnergyMaterial('40cm Rammed Earth', 0.4, 2.31, 2322, 832,
                                  'MediumRough', 0.95, 0.75, 0.8)
    earth_constr = OpaqueConstruction('Rammed Earth Construction', [rammed_earth])
    chimney_mass = InternalMass('Rammed Earth Chimney', earth_constr, 10)

    material_to_openstudio(rammed_earth, os_model)
    construction_to_openstudio(earth_constr, os_model)
    os_mass = internal_mass_to_openstudio(chimney_mass, os_model)

    os_mass_str = str(os_mass)
    assert os_mass_str.startswith('OS:InternalMass,')
    os_mass_def = os_mass.internalMassDefinition()
    os_mass_def_str = str(os_mass_def)
    assert os_mass_def_str.startswith('OS:InternalMass:Definition,')
