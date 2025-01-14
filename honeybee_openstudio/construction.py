# coding=utf-8
"""OpenStudio construction translators."""
from __future__ import division

from honeybee_energy.construction.opaque import OpaqueConstruction
from honeybee_energy.construction.window import WindowConstruction
from honeybee_energy.construction.windowshade import WindowConstructionShade
from honeybee_energy.construction.dynamic import WindowConstructionDynamic
from honeybee_energy.construction.shade import ShadeConstruction
from honeybee_energy.construction.air import AirBoundaryConstruction
from honeybee_energy.lib.constructions import air_boundary

from honeybee_openstudio.material import material_to_openstudio
from honeybee_openstudio.openstudio import OSConstruction, OSMaterialVector, \
    OSShadingControl, OSConstructionAirBoundary, OSZoneMixing, \
    OSStandardOpaqueMaterial, OSStandardGlazing


def standard_construction_to_openstudio(construction, os_model):
    """Convert Honeybee OpaqueConstruction or WindowConstruction to OpenStudio."""
    os_construction = OSConstruction(os_model)
    os_construction.setName(construction.identifier)
    if construction._display_name is not None:
        os_construction.setDisplayName(construction.display_name)
    os_materials = OSMaterialVector()
    for mat_id in construction.layers:
        material = os_model.getMaterialByName(mat_id)
        if material.is_initialized():
            os_material = material.get()
            try:
                os_materials.append(os_material)
            except AttributeError:  # using OpenStudio .NET bindings
                os_materials.Add(os_material)
    os_construction.setLayers(os_materials)
    return os_construction


def window_shade_construction_to_openstudio(construction, os_model):
    """Convert Honeybee WindowConstructionShade to OpenStudio Constructions."""
    # create the unshaded construction
    standard_construction_to_openstudio(construction.window_construction, os_model)
    # create the shaded construction
    os_shaded_con = OSConstruction(os_model)
    os_shaded_con.setName(construction.identifier)
    if construction._display_name is not None:
        os_shaded_con.setDisplayName(construction.display_name)
    os_materials = OSMaterialVector()
    for mat in construction.materials:
        material = os_model.getMaterialByName(mat.identifier)
        if material.is_initialized():
            os_material = material.get()
        else:  # it's a custom gap material that has not been added yet
            os_material = material_to_openstudio(mat, os_model)
        try:
            os_materials.append(os_material)
        except AttributeError:  # using OpenStudio .NET bindings
            os_materials.Add(os_material)
    os_shaded_con.setLayers(os_materials)
    return os_shaded_con


def window_shading_control_to_openstudio(construction, os_model):
    """Convert Honeybee WindowConstructionShade to OpenStudio ShadingControl.

    Each Aperture or Door that has a WindowConstructionShade assigned to it
    will have to call this method and then add the shading control to the
    OpenStudio SubSurface using the setShadingControl method.
    """
    # create the ShadingControl object
    os_shaded_con = os_model.getConstructionByName(construction.identifier)
    if os_shaded_con.is_initialized():
        os_shaded_con = os_shaded_con.get()
    else:
        msg = 'Failed to find construction "{}" for OpenStudio ShadingControl.'.format(
            construction.identifier)
        raise ValueError(msg)
    os_shade_control = OSShadingControl(os_shaded_con)
    # set the properties of the ShadingControl
    control_type = 'OnIfScheduleAllows' if construction.schedule is not None and \
        construction.control_type == 'AlwaysOn' else construction.control_type
    os_shade_control.setShadingControlType(control_type)
    os_shade_control.setShadingType(construction._ep_shading_type)
    if construction.schedule is not None:
        sch = os_model.getScheduleByName(construction.schedule.identifier)
        if sch.is_initialized():
            sch = sch.get()
            os_shade_control.setSchedule(sch)
    if construction.setpoint is not None:
        os_shade_control.setSetpoint(construction.setpoint)
    return os_shade_control


def air_construction_to_openstudio(construction, os_model):
    """Convert Honeybee AirBoundaryConstruction to OpenStudio ConstructionAirBoundary."""
    os_construction = OSConstructionAirBoundary(os_model)
    os_construction.setName(construction.identifier)
    if construction._display_name is not None:
        os_construction.setDisplayName(construction.display_name)
    os_construction.setAirExchangeMethod('None')
    return os_construction


def air_mixing_to_openstudio(face, target_zone, source_zone, os_model):
    """Convert Honeybee AirBoundaryConstruction to OpenStudio ZoneMixing.

    Args:
        face: A honeybee Face that has an AirBoundary face type.
        target_zone: The OpenStudio ThermalZone for the target of air mixing.
        source_zone: The OpenStudio ThermalZone for the source of air mixing.
        os_model: The OpenStudio Model to which the zone mixing is being added.
    """
    # calculate the flow rate and schedule
    construction = face.properties.energy.construction
    if isinstance(construction, AirBoundaryConstruction):
        flow_rate = face.area * construction.air_mixing_per_area
        schedule = construction.air_mixing_schedule.identifier
    else:
        flow_rate = face.area * air_boundary.air_mixing_per_area
        schedule = air_boundary.air_mixing_schedule.identifier
    # create the ZoneMixing object
    os_zone_mixing = OSZoneMixing(target_zone)
    os_zone_mixing.setSourceZone(source_zone)
    os_zone_mixing.setDesignFlowRate(flow_rate)
    flow_sch_ref = os_model.getScheduleByName(schedule)
    if flow_sch_ref.is_initialized():
        flow_sched = flow_sch_ref.get()
        os_zone_mixing.setSchedule(flow_sched)
    return os_zone_mixing


def shade_construction_to_openstudio(construction, os_model):
    """Convert Honeybee ShadeConstruction to OpenStudio Construction."""
    os_construction = OSConstruction(os_model)
    os_construction.setName(construction.identifier)
    if construction._display_name is not None:
        os_construction.setDisplayName(construction.display_name)
    os_materials = OSMaterialVector()
    if construction.is_specular:
        os_material = OSStandardGlazing(os_model)
        os_material.setFrontSideSolarReflectanceatNormalIncidence(
            construction.solar_reflectance)
        os_material.setFrontSideVisibleReflectanceatNormalIncidence(
            construction.visible_reflectance)
    else:
        os_material = OSStandardOpaqueMaterial(os_model)
        os_material.setSolarAbsorptance(1 - construction.solar_reflectance)
        os_material.setVisibleAbsorptance(1 - construction.visible_reflectance)
    try:
        os_materials.append(os_material)
    except AttributeError:  # using OpenStudio .NET bindings
        os_materials.Add(os_material)
    os_construction.setLayers(os_materials)
    return os_construction


def construction_to_openstudio(construction, os_model):
    """Convert any Honeybee energy construction into an OpenStudio object.

    Args:
        construction: A honeybee-energy Python object of a construction.
        os_model: The OpenStudio Model object to which the Room will be added.

    Returns:
        An OpenStudio object for the construction.
    """
    if isinstance(construction, (OpaqueConstruction, WindowConstruction)):
        return standard_construction_to_openstudio(construction, os_model)
    elif isinstance(construction, WindowConstructionShade):
        return window_shade_construction_to_openstudio(construction, os_model)
    elif isinstance(construction, WindowConstructionDynamic):
        # TODO: implement dynamic window constructions
        raise NotImplementedError(
            'WindowConstructionDynamic to OpenStudio not implemented.')
    elif isinstance(construction, ShadeConstruction):
        return shade_construction_to_openstudio(construction, os_model)
    elif isinstance(construction, AirBoundaryConstruction):
        return air_construction_to_openstudio(construction, os_model)
    else:
        raise ValueError(
            '{} is not a recognized Energy Construction type'.format(type(construction))
        )
