# coding=utf-8
"""OpenStudio ProgramType translator."""
from __future__ import division

from honeybee.typing import clean_ep_string
from honeybee_energy.programtype import ProgramType

from honeybee_openstudio.load import people_to_openstudio, lighting_to_openstudio, \
    electric_equipment_to_openstudio, gas_equipment_to_openstudio, \
    infiltration_to_openstudio, ventilation_to_openstudio, people_from_openstudio, \
    lighting_from_openstudio, electric_equipment_from_openstudio, \
    gas_equipment_from_openstudio, infiltration_from_openstudio, \
    ventilation_from_openstudio
from honeybee_openstudio.openstudio import OSSpaceType, OSDefaultScheduleSet


def program_type_to_openstudio(
    program_type, os_model, os_schedule_set=None, include_infiltration=True
):
    """Convert Honeybee ProgramType to OpenStudio SpaceType.

    Args:
        program_type: A Honeybee-energy ProgramType to be translated to OpenStudio.
        os_model: The OpenStudio Model object to which the SpaceType will be added.
        os_schedule_set: An optional DefaultScheduleSet object to be used for the
            SpaceType's schedules in place of those already assigned to the ProgramType.
            Typically, this should be a DefaultScheduleSet pulled from the output
            of the program_types_to_openstudio_schedule_sets function in this module.
            If None, schedules will be assigned directly to the SpaceType instead of
            being assigned via schedule set. (Default: None).
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
    # if there is a schedule set input, then assign it
    include_sch = True
    if os_schedule_set is not None:
        os_space_type.setDefaultScheduleSet(os_schedule_set)
        include_sch = False
    # assign people
    if program_type.people is not None:
        os_people = people_to_openstudio(program_type.people, os_model, include_sch)
        os_people.setSpaceType(os_space_type)
    # assign lighting
    if program_type.lighting is not None:
        os_lights = lighting_to_openstudio(program_type.lighting, os_model, include_sch)
        os_lights.setSpaceType(os_space_type)
    # assign electric equipment
    if program_type.electric_equipment is not None:
        os_equip = electric_equipment_to_openstudio(
            program_type.electric_equipment, os_model, include_sch
        )
        os_equip.setSpaceType(os_space_type)
    # assign gas equipment
    if program_type.gas_equipment is not None:
        os_equip = gas_equipment_to_openstudio(
            program_type.gas_equipment, os_model, include_sch
        )
        os_equip.setSpaceType(os_space_type)
    # assign infiltration
    if program_type.infiltration is not None and include_infiltration:
        os_inf = infiltration_to_openstudio(program_type.infiltration, os_model, include_sch)
        os_inf.setSpaceType(os_space_type)
    # assign ventilation
    if program_type.ventilation is not None:
        os_vent = ventilation_to_openstudio(program_type.ventilation, os_model)
        os_space_type.setDesignSpecificationOutdoorAir(os_vent)
    return os_space_type


def program_types_to_openstudio_schedule_sets(program_types, os_model):
    """Convert an array of Honeybee ProgramType to OpenStudio DefaultScheduleSet.

    The result of this method will has the minimum number of DefaultScheduleSet
    objects that are needed to describe all of the programs under the program_types.
    This way, a small number of schedule sets can be used to edit multiple
    programs in the OpenStudio Application.

    Note that the schedules used by the input program_types must be in the os_model
    already for this method to translate the schedule sets correctly.

    Args:
        program_types: An array of Honeybee-energy ProgramTypes to be translated
            to OpenStudio DefaultScheduleSet.
        os_model: The OpenStudio Model object to which the SpaceType will be added.

    Returns:
        A dictionary with ProgramType identifiers as keys and OpenStudio
        DefaultScheduleSet objects as values.
    """
    # sort programs by display name to help similar programs get the same schedule set
    program_types = sorted(program_types, key=lambda p: p.display_name)

    # track the schedules used by each of the input ProgramTypes
    sch_set_dict, sch_set_vals = {}, []
    for program in program_types:
        # get all of the relevant schedules from the program
        occ_sch, act_sch = None, None
        if program.people is not None:
            occ_sch = program.people.occupancy_schedule.identifier
            act_sch = program.people.activity_schedule.identifier
        light_sch = program.lighting.schedule.identifier \
            if program.lighting is not None else None
        e_equip_sch = program.electric_equipment.schedule.identifier \
            if program.electric_equipment is not None else None
        g_equip_sch = program.gas_equipment.schedule.identifier \
            if program.gas_equipment is not None else None
        inf_sch = program.infiltration.schedule.identifier \
            if program.infiltration is not None else None
        all_prog_sch = [occ_sch, act_sch, light_sch, e_equip_sch, g_equip_sch, inf_sch]

        # compare the schedules against those already in the list
        sch_set_i = None
        for si, ss_vals in enumerate(sch_set_vals):
            for i, (p_val, ss_val) in enumerate(zip(all_prog_sch, ss_vals)):
                if p_val is None:
                    continue
                elif ss_val is None:  # we can use an existing set
                    ss_vals[i] = p_val
                elif p_val != ss_val:  # we cannot use an existing set
                    break
            else:  # use the existing schedule set
                sch_set_i = si
                break

        # if we were unable to find an existing schedule set, establish a new one
        if sch_set_i is None:
            sch_set_i = len(sch_set_vals)
            sch_set_vals.append(all_prog_sch)
        sch_set_dict[program.identifier] = sch_set_i

    # using all of the unique collected schedules, create DefaultScheduleSet objects
    sch_set_objs = []
    for i, ss_vals in enumerate(sch_set_vals):
        os_sch_set = OSDefaultScheduleSet(os_model)
        os_sch_set.setName('Schedule Set {}'.format(i + 1))
        occ_sch, act_sch, light_sch, e_equip_sch, g_equip_sch, inf_sch = ss_vals
        # set the occupancy schedule
        if occ_sch is not None:
            occ_sch = os_model.getScheduleByName(occ_sch)
            if occ_sch.is_initialized():
                occ_sch = occ_sch.get()
                os_sch_set.setNumberofPeopleSchedule(occ_sch)
        # set the activity schedule
        if act_sch is not None:
            act_sch = os_model.getScheduleByName(act_sch)
            if act_sch.is_initialized():
                act_sch = act_sch.get()
                os_sch_set.setPeopleActivityLevelSchedule(act_sch)
        # set the lighting schedule
        if light_sch is not None:
            light_sch = os_model.getScheduleByName(light_sch)
            if light_sch.is_initialized():
                light_sch = light_sch.get()
                os_sch_set.setLightingSchedule(light_sch)
        # set the electric equipment schedule
        if e_equip_sch is not None:
            e_equip_sch = os_model.getScheduleByName(e_equip_sch)
            if e_equip_sch.is_initialized():
                e_equip_sch = e_equip_sch.get()
                os_sch_set.setElectricEquipmentSchedule(e_equip_sch)
        # set the gas equipment schedule
        if g_equip_sch is not None:
            g_equip_sch = os_model.getScheduleByName(g_equip_sch)
            if g_equip_sch.is_initialized():
                g_equip_sch = g_equip_sch.get()
                os_sch_set.setGasEquipmentSchedule(g_equip_sch)
        # set the infiltration equipment schedule
        if inf_sch is not None:
            inf_sch = os_model.getScheduleByName(inf_sch)
            if inf_sch.is_initialized():
                inf_sch = inf_sch.get()
                os_sch_set.setInfiltrationSchedule(inf_sch)
        sch_set_objs.append(os_sch_set)

    # replace the integers in the sch_set_dict with the objects and return it
    for prog_id in sch_set_dict.keys():
        sch_set_dict[prog_id] = sch_set_objs[sch_set_dict[prog_id]]
    return sch_set_dict


def program_type_from_openstudio(os_space_type, schedules=None):
    """Convert OpenStudio SpaceType to Honeybee ProgramType."""
    program_type = ProgramType(clean_ep_string(os_space_type.nameString()))
    # assign people
    for os_people in os_space_type.people():
        people_def = os_people.peopleDefinition()  # only translate if people per floor
        if people_def.peopleperSpaceFloorArea().is_initialized():
            program_type.people = people_from_openstudio(os_people, schedules)
    # assign lighting
    for os_lights in os_space_type.lights():
        light_def = os_lights.lightsDefinition()  # only translate if watts per floor
        if light_def.wattsperSpaceFloorArea().is_initialized():
            program_type.lighting = lighting_from_openstudio(os_lights, schedules)
    # assign electric equipment
    for os_equip in os_space_type.electricEquipment():
        electric_eq_def = os_equip.electricEquipmentDefinition()
        if electric_eq_def.wattsperSpaceFloorArea().is_initialized():
            program_type.electric_equipment = \
                electric_equipment_from_openstudio(os_equip, schedules)
    # assign gas equipment
    for os_equip in os_space_type.gasEquipment():
        electric_eq_def = os_equip.gasEquipmentDefinition()
        if electric_eq_def.wattsperSpaceFloorArea().is_initialized():
            program_type.gas_equipment = \
                gas_equipment_from_openstudio(os_equip, schedules)
    # assign infiltration
    for os_inf in os_space_type.spaceInfiltrationDesignFlowRates():
        if os_inf.flowperExteriorSurfaceArea().is_initialized():
            program_type.infiltration = infiltration_from_openstudio(os_inf, schedules)
    # assign ventilation
    if os_space_type.designSpecificationOutdoorAir().is_initialized():
        os_vent = os_space_type.designSpecificationOutdoorAir().get()
        program_type.ventilation = ventilation_from_openstudio(os_vent, schedules)
    # assign the display name and return it
    if os_space_type.displayName().is_initialized():
        program_type.display_name = os_space_type.displayName().get()
    return program_type
