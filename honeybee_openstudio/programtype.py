# coding=utf-8
"""OpenStudio ProgramType translator."""
from __future__ import division

from honeybee_openstudio.load import people_to_openstudio, lighting_to_openstudio, \
    electric_equipment_to_openstudio, gas_equipment_to_openstudio, \
    infiltration_to_openstudio, ventilation_to_openstudio
from honeybee_openstudio.openstudio import OSSpaceType


def program_type_to_openstudio(program_type, os_model, include_infiltration=True):
    """Convert Honeybee ProgramType to OpenStudio SpaceType.

    Args:
        program_type: A Honeybee-energy ProgramType to be translated to OpenStudio.
        os_model: The OpenStudio Model object to which the SpaceType will be added.
        include_infiltration: Boolean for whether or not infiltration will be included
            in the translation of the ProgramType. It may be desirable to set this
            to False if the building airflow is being modeled with the EnergyPlus
            AirFlowNetwork. (Default: True).
    """
    # create openstudio space type object
    os_space_type = OSSpaceType(os_model)
    os_space_type.setName(program_type.identifier)
    if program_type._display_name is not None:
        os_space_type.setDisplayName(program_type.display_name)
    # if the program is from honeybee-energy-standards, also set the measure tag
    std_spc_type = program_type.identifier.split('::')
    if len(std_spc_type) == 3:  # originated from honeybee-energy-standards
        std_spc_type = std_spc_type[2]
        std_spc_type = std_spc_type.split('_')[0]
        os_space_type.setStandardsSpaceType(std_spc_type)
    # assign people
    if program_type.people is not None:
        os_people = people_to_openstudio(program_type.people, os_model)
        os_people.setSpaceType(os_space_type)
    # assign lighting
    if program_type.lighting is not None:
        os_lights = lighting_to_openstudio(program_type.lighting, os_model)
        os_lights.setSpaceType(os_space_type)
    # assign electric equipment
    if program_type.electric_equipment is not None:
        os_equip = electric_equipment_to_openstudio(program_type.electric_equipment, os_model)
        os_equip.setSpaceType(os_space_type)
    # assign gas equipment
    if program_type.gas_equipment is not None:
        os_equip = gas_equipment_to_openstudio(program_type.gas_equipment, os_model)
        os_equip.setSpaceType(os_space_type)
    # assign infiltration
    if program_type.infiltration is not None and include_infiltration:
        os_inf = infiltration_to_openstudio(program_type.infiltration, os_model)
        os_inf.setSpaceType(os_space_type)
    # assign ventilation
    if program_type.ventilation is not None:
        os_vent = ventilation_to_openstudio(program_type.ventilation, os_model)
        os_space_type.setDesignSpecificationOutdoorAir(os_vent)
    return os_space_type
