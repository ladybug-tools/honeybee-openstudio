# coding=utf-8
"""Methods to write Honeybee Models to OpenStudio."""
from __future__ import division

from ladybug_geometry.geometry3d import Face3D
from honeybee.typing import clean_ep_string
from honeybee.altnumber import autocalculate
from honeybee.facetype import RoofCeiling, Floor, AirBoundary
from honeybee.boundarycondition import Outdoors, Ground, Surface
from honeybee_energy.boundarycondition import Adiabatic, OtherSideTemperature
from honeybee_energy.construction.dynamic import WindowConstructionDynamic
from honeybee_energy.hvac.idealair import IdealAirSystem
from honeybee_energy.lib.constructionsets import generic_construction_set

from honeybee_openstudio.openstudio import OSModel, OSPoint3dVector, OSPoint3d, \
    OSShadingSurfaceGroup, OSShadingSurface, OSSubSurface, OSSurface, OSSpace, \
    OSThermalZone, OSBuildingStory, OSSurfacePropertyOtherSideCoefficients, \
    OSEnergyManagementSystemProgramCallingManager
from honeybee_openstudio.schedule import schedule_type_limits_to_openstudio, \
    schedule_to_openstudio
from honeybee_openstudio.material import material_to_openstudio
from honeybee_openstudio.construction import construction_to_openstudio, \
    air_mixing_to_openstudio, window_shading_control_to_openstudio, \
    window_dynamic_ems_program_to_openstudio
from honeybee_openstudio.constructionset import construction_set_to_openstudio
from honeybee_openstudio.load import people_to_openstudio, lighting_to_openstudio, \
    electric_equipment_to_openstudio, gas_equipment_to_openstudio, \
    hot_water_to_openstudio, infiltration_to_openstudio, ventilation_to_openstudio, \
    setpoint_to_openstudio_thermostat, setpoint_to_openstudio_humidistat
from honeybee_openstudio.programtype import program_type_to_openstudio
from honeybee_openstudio.shw import shw_system_to_openstudio
from honeybee_openstudio.hvac.idealair import ideal_air_system_to_openstudio


def face_3d_to_openstudio(face_3d):
    """Convert a Face3D into an OpenStudio Point3dVector.

    Args:
        face_3d: A ladybug-geometry Face3D object for which an OpenStudio Point3dVector
            string will be generated.

    Returns:
        An OpenStudio Point3dVector to be used to construct geometry objects.
    """
    os_vertices = OSPoint3dVector()
    for pt in face_3d.upper_left_counter_clockwise_vertices:
        try:
            os_vertices.append(OSPoint3d(pt.x, pt.y, pt.z))
        except AttributeError:  # using OpenStudio .NET bindings
            os_vertices.Add(OSPoint3d(pt.x, pt.y, pt.z))
    return os_vertices


def shade_mesh_to_openstudio(shade_mesh, os_model):
    """Create OpenStudio objects from a ShadeMesh.

    Args:
        shade_mesh: A honeybee ShadeMesh for which OpenStudio objects will be returned.
        os_model: The OpenStudio Model object to which the ShadeMesh will be added.

    Returns:
        A list of OpenStudio ShadingSurface objects.
    """
    # loop through the mesh faces and create individual shade objects
    os_shades = []
    os_shd_group = OSShadingSurfaceGroup(os_model)
    os_shd_group.setName(shade_mesh.identifier)
    for i, shade in enumerate(shade_mesh.geometry.face_vertices):
        shade_face = Face3D(shade)
        os_vertices = face_3d_to_openstudio(shade_face)
        os_shade = OSShadingSurface(os_vertices, os_model)
        os_shade.setName('{}_{}'.format(shade_mesh.identifier, i))
        os_shade.setShadingSurfaceGroup(os_shd_group)
        os_shades.append(os_shade)
    if shade_mesh._display_name is not None:
        for os_shade in os_shades:
            os_shade.setDisplayName(shade_mesh.display_name)
    construction = shade_mesh.properties.energy.construction
    if shade_mesh.properties.energy.is_construction_set_on_object and \
            not construction.is_default:
        os_construction = os_model.getConstructionByName(construction.identifier)
        if os_construction.is_initialized():
            for os_shade in os_shades:
                os_shade.setConstruction(os_construction)
    trans_sched = shade_mesh.properties.energy.transmittance_schedule
    if trans_sched is not None:
        os_schedule = os_model.getScheduleByName(trans_sched.identifier)
        if os_schedule.is_initialized():
            for os_shade in os_shades:
                os_shade.setTransmittanceSchedule(os_schedule)
    return os_shades


def shade_to_openstudio(shade, os_model):
    """Create an OpenStudio object from a Shade.

    Args:
        shade: A honeybee Shade for which an OpenStudio object will be returned.
        os_model: The OpenStudio Model object to which the Shade will be added.

    Returns:
        An OpenStudio ShadingSurface object.
    """
    os_vertices = face_3d_to_openstudio(shade.geometry)
    os_shade = OSShadingSurface(os_vertices, os_model)
    os_shade.setName(shade.identifier)
    if shade._display_name is not None:
        os_shade.setDisplayName(shade.display_name)
    construction = shade.properties.energy.construction
    if shade.properties.energy.is_construction_set_on_object and \
            not construction.is_default:
        os_construction = os_model.getConstructionByName(construction.identifier)
        if os_construction.is_initialized():
            os_shade.setConstruction(os_construction)
    trans_sched = shade.properties.energy.transmittance_schedule
    if trans_sched is not None:
        os_schedule = os_model.getScheduleByName(trans_sched.identifier)
        if os_schedule.is_initialized():
            os_shade.setTransmittanceSchedule(os_schedule)
    # TODO: add the translation of PVProperties
    return os_shade


def door_to_openstudio(door, os_model):
    """Create an OpenStudio object from a Door.

    Args:
        door: A honeybee Door for which an OpenStudio object will be returned.
        os_model: The OpenStudio Model object to which the Door will be added.

    Returns:
        An OpenStudio SubSurface object if the Door has a parent. An OpenStudio
        ShadingSurface object if the Door has no parent.
    """
    # convert the base geometry to OpenStudio
    os_vertices = face_3d_to_openstudio(door.geometry)
    # translate the geometry to either a SubSurface or a ShadingSurface
    if door.has_parent:
        os_door = OSSubSurface(os_vertices, os_model)
        if door.is_glass:
            dr_type = 'GlassDoor'
        else:
            par = door.parent
            dr_type = 'OverheadDoor' if isinstance(par.boundary_condition, Outdoors) and \
                isinstance(par.type, (RoofCeiling, Floor)) else 'Door'
        os_door.setSubSurfaceType(dr_type)
        # assign the construction if it's hard set
        construction = door.properties.energy.construction
        if door.properties.energy.is_construction_set_on_object:
            if construction.has_shade:
                constr_id = construction.window_construction.identifier
            elif construction.is_dynamic:
                constr_id = '{}State0'.format(construction.constructions[0].identifier)
            else:
                constr_id = construction.identifier
            os_construction = os_model.getConstructionByName(constr_id)
            if os_construction.is_initialized():
                os_construction = os_construction.get()
                os_door.setConstruction(os_construction)
        # assign the frame property if the window construction has one
        if construction.has_frame:
            frame_id = construction.frame.identifier
            frame = os_model.getWindowPropertyFrameAndDividerByName(frame_id)
            if frame.is_initialized():
                os_frame = frame.get()
                os_door.setWindowPropertyFrameAndDivider(os_frame)
        # create the WindowShadingControl object if it is needed
        if construction.has_shade:
            shd_prop_str = window_shading_control_to_openstudio(construction, os_model)
            os_door.setShadingControl(shd_prop_str)
    else:
        os_door = OSShadingSurface(os_vertices, os_model)
        for shd in door._outdoor_shades:
            shade_to_openstudio(shd, os_model)

    # set the object name and return it
    os_door.setName(door.identifier)
    if door._display_name is not None:
        os_door.setDisplayName(door.display_name)
    return os_door


def aperture_to_openstudio(aperture, os_model):
    """Create an OpenStudio object from an Aperture.

    Args:
        aperture: A honeybee Aperture for which an OpenStudio object will be returned.
        os_model: The OpenStudio Model object to which the Aperture will be added.

    Returns:
        An OpenStudio SubSurface object if the Aperture has a parent. An OpenStudio
        ShadingSurface object if the Aperture has no parent.
    """
    # convert the base geometry to OpenStudio
    os_vertices = face_3d_to_openstudio(aperture.geometry)
    # translate the geometry to either a SubSurface or a ShadingSurface
    if aperture.has_parent:
        os_aperture = OSSubSurface(os_vertices, os_model)
        if aperture.is_operable:
            ap_type = 'OperableWindow'
        else:
            par = aperture.parent
            ap_type = 'Skylight' if isinstance(par.boundary_condition, Outdoors) and \
                isinstance(par.type, (RoofCeiling, Floor)) else 'FixedWindow'
        os_aperture.setSubSurfaceType(ap_type)
        # assign the construction if it's hard set
        construction = aperture.properties.energy.construction
        if aperture.properties.energy.is_construction_set_on_object:
            if construction.has_shade:
                constr_id = construction.window_construction.identifier
            elif construction.is_dynamic:
                constr_id = '{}State0'.format(construction.constructions[0].identifier)
            else:
                constr_id = construction.identifier
            os_construction = os_model.getConstructionByName(constr_id)
            if os_construction.is_initialized():
                os_construction = os_construction.get()
                os_aperture.setConstruction(os_construction)
        # assign the frame property if the window construction has one
        if construction.has_frame:
            frame_id = construction.frame.identifier
            frame = os_model.getWindowPropertyFrameAndDividerByName(frame_id)
            if frame.is_initialized():
                os_frame = frame.get()
                os_aperture.setWindowPropertyFrameAndDivider(os_frame)
        # create the WindowShadingControl object if it is needed
        if construction.has_shade:
            shd_prop_str = window_shading_control_to_openstudio(construction, os_model)
            os_aperture.setShadingControl(shd_prop_str)
    else:
        os_aperture = OSShadingSurface(os_vertices, os_model)
        for shd in aperture._outdoor_shades:
            shade_to_openstudio(shd, os_model)

    # set the object name and return it
    os_aperture.setName(aperture.identifier)
    if aperture._display_name is not None:
        os_aperture.setDisplayName(aperture.display_name)
    return os_aperture


def face_to_openstudio(face, os_model, adj_map=None):
    """Create an OpenStudio object from a Face.

    This method also adds all Apertures, Doors, and Shades assigned to the Face.

    Args:
        face: A honeybee Face for which an OpenStudio object will be returned.
        os_model: The OpenStudio Model object to which the Face will be added.
        adj_map: An optional dictionary with keys for 'faces' and 'sub_faces'
            that will have the space Surfaces and SubSurfaces added to it
            such that adjacencies can be assigned after running this method.

    Returns:
        An OpenStudio Surface object if the Face has a parent. An OpenStudio
        ShadingSurface object if the Face has no parent.
    """
    # translate the geometry to either a SubSurface or a ShadingSurface
    if face.has_parent:
        # create the Surface
        os_vertices = face_3d_to_openstudio(face.geometry)
        os_face = OSSurface(os_vertices, os_model)

        # select the correct face type
        if isinstance(face.type, AirBoundary):
            os_f_type = 'Wall'  # air boundaries are not a Surface type in EnergyPlus
        elif isinstance(face.type, RoofCeiling):
            if face.altitude < 0:
                os_f_type = 'Wall'  # ensure E+ does not try to flip the Face
            elif isinstance(face.boundary_condition, (Outdoors, Ground)):
                os_f_type = 'Roof'  # E+ distinguishes between Roof and Ceiling
            else:
                os_f_type = 'Ceiling'
        elif isinstance(face.type, Floor) and face.altitude > 0:
            os_f_type = 'Wall'  # ensure E+ does not try to flip the Face
        else:
            os_f_type = face.type.name
        os_face.setSurfaceType(os_f_type)

        # assign the boundary condition
        fbc = face.boundary_condition
        if not isinstance(fbc, (Surface, OtherSideTemperature)):
            os_face.setOutsideBoundaryCondition(fbc.name)
        if isinstance(fbc, Outdoors):
            if not fbc.sun_exposure:
                os_face.setSunExposure('NoSun')
            if not fbc.wind_exposure:
                os_face.setWindExposure('NoWind')
            if fbc.view_factor != autocalculate:
                os_face.setViewFactortoGround(fbc.view_factor)
        elif isinstance(fbc, OtherSideTemperature):
            srf_prop = OSSurfacePropertyOtherSideCoefficients(os_model)
            srf_prop.setName('{}_OtherTemp'.format(face.identifier))
            htc = fbc.heat_transfer_coefficient
            os_face.setCombinedConvectiveRadiativeFilmCoefficient(htc)
            if fbc.temperature == autocalculate:
                srf_prop.setConstantTemperatureCoefficient(0)
                srf_prop.setExternalDryBulbTemperatureCoefficient(1)
            else:
                srf_prop.setConstantTemperature(fbc.temperature)
                srf_prop.setConstantTemperatureCoefficient(1)
                srf_prop.setExternalDryBulbTemperatureCoefficient(0)
            os_face.setSurfacePropertyOtherSideCoefficients(srf_prop)

        # assign the construction if it's hard set, an AirBoundary, or Adiabatic
        if face.properties.energy.is_construction_set_on_object or \
                isinstance(face.type, AirBoundary) or \
                isinstance(face.boundary_condition, (Adiabatic, OtherSideTemperature)):
            construction_id = face.properties.energy.construction.identifier
            os_construction = os_model.getConstructionByName(construction_id)
            if os_construction.is_initialized():
                os_construction = os_construction.get()
                os_face.setConstruction(os_construction)

        # create the sub-faces
        sub_faces = {}
        for ap in face.apertures:
            if len(ap.geometry) <= 4:  # ignore apertures to be triangulated
                os_ap = aperture_to_openstudio(ap, os_model)
                os_ap.setSurface(os_face)
                sub_faces[ap.identifier] = os_ap
        for dr in face.doors:
            if len(dr.geometry) <= 4:  # ignore doors to be triangulated
                os_dr = door_to_openstudio(dr, os_model)
                os_dr.setSurface(os_face)
                sub_faces[dr.identifier] = os_dr

        # update the adjacency map if it exists
        if adj_map is not None:
            adj_map['faces'][face.identifier] = os_face
            adj_map['sub_faces'].update(sub_faces)
    else:
        os_vertices = face_3d_to_openstudio(face.punched_geometry)
        os_face = OSShadingSurface(os_vertices, os_model)
        for ap in face.apertures:
            aperture_to_openstudio(ap.duplicate(), os_model)
        for dr in face.doors:
            door_to_openstudio(dr.duplicate(), os_model)
        for shd in face._outdoor_shades:
            shade_to_openstudio(shd, os_model)

    # set the object name and return it
    os_face.setName(face.identifier)
    if face._display_name is not None:
        os_face.setDisplayName(face.display_name)
    return os_face


def room_to_openstudio(room, os_model, adj_map=None, include_infiltration=True):
    """Create OpenStudio objects from a Room.

    Args:
        room: A honeybee Room for which an OpenStudio object will be returned.
        os_model: The OpenStudio Model object to which the Room will be added.
        adj_map: An optional dictionary with keys for 'faces' and 'sub_faces'
            that will have the space Surfaces and SubSurfaces added to it
            such that adjacencies can be assigned after running this method.
        include_infiltration: Boolean for whether or not infiltration will be included
            in the translation of the Room. It may be desirable to set this
            to False if the building airflow is being modeled with the EnergyPlus
            AirFlowNetwork. (Default: True).

    Returns:
        An OpenStudio Space object for the Room.
    """
    # create the space
    os_space = OSSpace(os_model)
    os_space.setName('{}_Space'.format(room.identifier))
    if room._display_name is not None:
        os_space.setDisplayName(room.display_name)
    if room.exclude_floor_area:
        os_space.setPartofTotalFloorArea(False)

    # assign the construction set if specified
    if room.properties.energy._construction_set is not None:
        con_set_id = room.properties.energy.construction_set.identifier
        os_con_set = os_model.getDefaultConstructionSetByName(con_set_id)
        if os_con_set.is_initialized():
            os_con_set = os_con_set.get()
            os_space.setDefaultConstructionSet(os_con_set)

    # assign the program type if specified
    overridden_loads = room.properties.energy.has_overridden_space_loads
    if not overridden_loads and room.properties.energy._program_type is not None:
        # assign loads using the OpenStudio SpaceType
        space_type_id = room.properties.energy.program_type.identifier
        os_space_type = os_model.getSpaceTypeByName(space_type_id)
        if os_space_type.is_initialized():
            space_type_object = os_space_type.get()
            os_space.setSpaceType(space_type_object)
    elif overridden_loads:
        # assign loads directly to the space
        people = room.properties.energy.people
        if people is not None:
            os_people = people_to_openstudio(people, os_model)
            os_people.setName('{}..{}'.format(people.identifier, room.identifier))
            os_people.setSpace(os_space)
        lighting = room.properties.energy.lighting
        if lighting is not None:
            os_lights = lighting_to_openstudio(lighting, os_model)
            os_lights.setName('{}..{}'.format(lighting.identifier, room.identifier))
            os_lights.setSpace(os_space)
        equipment = room.properties.energy.electric_equipment
        if equipment is not None:
            os_equip = electric_equipment_to_openstudio(equipment, os_model)
            os_equip.setName('{}..{}'.format(equipment.identifier, room.identifier))
            os_equip.setSpace(os_space)
        equipment = room.properties.energy.gas_equipment
        if equipment is not None:
            os_equip = gas_equipment_to_openstudio(equipment, os_model)
            os_equip.setName('{}..{}'.format(equipment.identifier, room.identifier))
            os_equip.setSpace(os_space)
        infilt = room.properties.energy.infiltration
        if infilt is not None and include_infiltration:
            os_inf = infiltration_to_openstudio(infilt, os_model)
            os_inf.setName('{}..{}'.format(infilt.identifier, room.identifier))
            os_inf.setSpace(os_space)
    # assign the ventilation and catch the case that the SpaceType one is not correct
    if overridden_loads or room.properties.energy._ventilation is not None:
        vent = room.properties.energy.ventilation
        if vent is not None:
            os_vent = os_model.getDesignSpecificationOutdoorAirByName(vent.identifier)
            if os_vent.is_initialized():
                os_vent = os_vent.get()
            else:
                os_vent = ventilation_to_openstudio(vent, os_model)
            os_space.setDesignSpecificationOutdoorAir(os_vent)

    # assign all of the faces to the room
    for face in room.faces:
        os_face = face_to_openstudio(face, os_model, adj_map)
        os_face.setSpace(os_space)

    # add any assigned shades to a group for the room
    child_shades = []
    child_shades.extend(room._outdoor_shades)
    for face in room._faces:
        child_shades.extend(face._outdoor_shades)
        for ap in face.apertures:
            child_shades.extend(ap._outdoor_shades)
        for dr in face.doors:
            child_shades.extend(dr._outdoor_shades)
    if len(child_shades) != 0:
        os_shd_group = OSShadingSurfaceGroup(os_model)
        os_shd_group.setName('{} Shades'.format(room.identifier))
        os_shd_group.setSpace(os_space)
        os_shd_group.setShadingSurfaceType('Space')
        for shd in child_shades:
            os_shade = shade_to_openstudio(shd, os_model)
            os_shade.setShadingSurfaceGroup(os_shd_group)

    return os_space


def model_to_openstudio(
    model, seed_model=None, schedule_directory=None,
    use_geometry_names=False, use_resource_names=False,
    triangulate_non_planar_orphaned=False, enforce_rooms=False
):
    """Create an OpenStudio Model from a Honeybee Model.

    The resulting Model will include all geometry (Rooms, Faces, Apertures,
    Doors, Shades), all fully-detailed constructions + materials, all fully-detailed
    schedules, and the room properties.

    Args:
        model: The Honeybee Model to be converted into an OpenStudio Model.
        seed_model: An optional OpenStudio Model object to which the Honeybee
            Model will be added. If None, a new OpenStudio Model will be
            initialized within this method. (Default: None).
        schedule_directory: An optional file directory to which all file-based
            schedules should be written to. If None, all ScheduleFixedIntervals
            will be translated to Schedule:Compact and written fully into the
            IDF string instead of to Schedule:File. (Default: None).
        use_geometry_names: Boolean to note whether a cleaned version of all
            geometry display names should be used instead of identifiers when
            translating the Model to OSM and IDF. Using this flag will affect
            all Rooms, Faces, Apertures, Doors, and Shades. It will generally
            result in more read-able names in the OSM and IDF but this means
            that it will not be easy to map the EnergyPlus results back to the
            input Honeybee Model. Cases of duplicate IDs resulting from
            non-unique names will be resolved by adding integers to the ends
            of the new IDs that are derived from the name. (Default: False).
        use_resource_names: Boolean to note whether a cleaned version of all
            resource display names should be used instead of identifiers when
            translating the Model to OSM and IDF. Using this flag will affect
            all Materials, Constructions, ConstructionSets, Schedules, Loads,
            and ProgramTypes. It will generally result in more read-able names
            for the resources in the OSM and IDF. Cases of duplicate IDs
            resulting from non-unique names will be resolved by adding integers
            to the ends of the new IDs that are derived from the name. (Default: False).
        triangulate_non_planar_orphaned: Boolean to note whether any non-planar
            orphaned geometry in the model should be triangulated upon export.
            This can be helpful because OpenStudio simply raises an error when
            it encounters non-planar geometry, which would hinder the ability
            to save files that are to be corrected later. (Default: False).
        enforce_rooms: Boolean to note whether this method should enforce the
            presence of Rooms in the Model, which is as necessary prerequisite
            for simulation in EnergyPlus. (Default: False).

    Usage:

    .. code-block:: python

        import os
        from honeybee.model import Model
        from honeybee.room import Room
        from honeybee.config import folders
        import openstudio
        from honeybee_openstudio.writer import model_to_openstudio

        # Crate an input Model
        room = Room.from_box('Tiny House Zone', 5, 10, 3)
        room.properties.energy.program_type = office_program
        room.properties.energy.add_default_ideal_air()
        hb_model = Model('Tiny House', [room])

        # translate the honeybee model to an openstudio model
        os_model = model_to_openstudio(model)

        # save the OpenStudio model to an OSM
        osm = os.path.join(folders.default_simulation_folder, 'in.osm')
        os_model.save(osm, overwrite=True)

        # save the OpenStudio model to an IDF file
        idf_translator = openstudio.energyplus.ForwardTranslator()
        workspace = idf_translator.translateModel(os_model)
        idf = os.path.join(folders.default_simulation_folder, 'in.idf')
        workspace.save(idf, overwrite=True)
    """
    # check for rooms if this is enforced
    if enforce_rooms:
        assert len(model.rooms) != 0, \
            'Model contains no Rooms and therefore cannot be simulated in EnergyPlus.'

    # duplicate model to avoid mutating it as we edit it for energy simulation
    original_model = model
    model = model.duplicate()

    # scale the model if the units are not meters
    if model.units != 'Meters':
        model.convert_to_units('Meters')
    # remove degenerate geometry within native E+ tolerance of 0.01 meters
    try:
        model.remove_degenerate_geometry(0.01)
    except ValueError:
        error = 'Failed to remove degenerate Rooms.\nYour Model units system is: {}. ' \
            'Is this correct?'.format(original_model.units)
        raise ValueError(error)
    if triangulate_non_planar_orphaned:
        model.triangulate_non_planar_quads(0.01)

    # remove the HVAC from any Rooms lacking setpoints
    rem_msgs = model.properties.energy.remove_hvac_from_no_setpoints()
    if len(rem_msgs) != 0:
        print('\n'.join(rem_msgs))

    # reset the IDs to be derived from the display_names if requested
    if use_geometry_names:
        id_map = model.reset_ids()
        model.properties.energy.sync_detailed_hvac_ids(id_map['rooms'])
    if use_resource_names:
        model.properties.energy.reset_resource_ids()

    # resolve the properties across zones
    single_zones, zone_dict = model.properties.energy.resolve_zones()

    # create the OpenStudio model object and setup the Building
    os_model = OSModel() if seed_model is None else seed_model
    os_building = os_model.getBuilding()
    if model._display_name is not None:
        os_building.setName(clean_ep_string(model.display_name))
    else:
        os_building.setName(model.identifier)
    os_model.setDayofWeekforStartDay('Sunday')  # this avoids lots of warnings

    # write all of the schedules and type limits
    schedules, type_limits = [], []
    always_on_included = False
    all_scheds = model.properties.energy.schedules + \
        model.properties.energy.orphaned_trans_schedules
    for sched in all_scheds:
        if sched.identifier == 'Always On':
            always_on_included = True
        schedules.append(sched)
        t_lim = sched.schedule_type_limit
        if t_lim is not None and not _instance_in_array(t_lim, type_limits):
            type_limits.append(t_lim)
    if not always_on_included:
        always_schedule = model.properties.energy._always_on_schedule()
        schedules.append(always_schedule)
    for stl in type_limits:
        schedule_type_limits_to_openstudio(stl, os_model)
    for sch in schedules:
        schedule_to_openstudio(sch, os_model, schedule_directory)

    # write all of the materials, constructions, and construction sets
    materials, constructions, dynamic_cons = [], [], []
    all_constrs = model.properties.energy.constructions + \
        generic_construction_set.constructions_unique
    for constr in set(all_constrs):
        try:
            materials.extend(constr.materials)
            constructions.append(constr)
            if constr.has_frame:
                materials.append(constr.frame)
            if constr.has_shade:
                if constr.window_construction in all_constrs:
                    constructions.pop(-1)  # avoid duplicate specification
                if constr.is_switchable_glazing:
                    materials.append(constr.switched_glass_material)
            elif constr.is_dynamic:
                dynamic_cons.append(constr)
        except AttributeError:
            try:  # AirBoundaryConstruction or ShadeConstruction
                constructions.append(constr)  # AirBoundaryConstruction
            except TypeError:
                pass  # ShadeConstruction; no need to write it
    for mat in set(materials):
        material_to_openstudio(mat, os_model)
    for constr in constructions:
        construction_to_openstudio(constr, os_model)
    os_generic_c_set = construction_set_to_openstudio(generic_construction_set, os_model)
    os_building.setDefaultConstructionSet(os_generic_c_set)
    for con_set in model.properties.energy.construction_sets:
        construction_set_to_openstudio(con_set, os_model)

    # translate all of the programs
    for program in model.properties.energy.program_types:
        program_type_to_openstudio(program, os_model)

    # create all of the spaces
    space_map, story_map = {}, {}
    adj_map = {'faces': {}, 'sub_faces': {}}
    for room in model.rooms:
        os_space = room_to_openstudio(room, os_model, adj_map)
        space_map[room.identifier] = os_space
        try:
            story_map[room.story].append(os_space)
        except KeyError:  # first room found on the story
            story_map[room.story] = [os_space]

    # create all of the zones
    zone_map = {}
    for room in single_zones:
        os_zone = OSThermalZone(os_model)
        os_zone.setName(room.identifier)
        os_space = space_map[room.identifier]
        os_space.setThermalZone(os_zone)
        zone_map[room.identifier] = os_zone
        if room.multiplier != 1:
            os_zone.setMultiplier(room.multiplier)
        os_zone.setCeilingHeight(room.geometry.max.z - room.geometry.min.z)
        os_zone.setVolume(room.volume)
        if room.properties.energy.setpoint is not None:
            set_pt = room.properties.energy.setpoint
            therm = setpoint_to_openstudio_thermostat(set_pt, os_model, room.identifier)
            os_zone.setThermostatSetpointDualSetpoint(therm)
            humid = setpoint_to_openstudio_humidistat(set_pt, os_model, room.identifier)
            if humid is not None:
                os_zone.setZoneControlHumidistat(humid)
    for zone_id, zone_data in zone_dict.items():
        rooms, z_prop, set_pt, vent = zone_data
        mult, ceil_hgt, vol, _, _ = z_prop
        os_zone = OSThermalZone(os_model)
        os_zone.setName(zone_id)
        for room in rooms:
            os_space = space_map[room.identifier]
            os_space.setThermalZone(os_zone)
            zone_map[room.identifier] = os_zone
        if mult != 1:
            os_zone.setMultiplier(mult)
        os_zone.setCeilingHeight(ceil_hgt)
        os_zone.setVolume(vol)
        if set_pt is not None:
            therm = setpoint_to_openstudio_thermostat(set_pt, os_model, zone_id)
            os_zone.setThermostatSetpointDualSetpoint(therm)
            humid = setpoint_to_openstudio_humidistat(set_pt, os_model, zone_id)
            if humid is not None:
                os_zone.setZoneControlHumidistat(humid)

    # triangulate any apertures or doors with more than 4 vertices
    tri_apertures, _ = model.triangulated_apertures()
    for tri_aps in tri_apertures:
        for i, ap in enumerate(tri_aps):
            if i != 0:
                ap.properties.energy.vent_opening = None
            os_ap = aperture_to_openstudio(ap, model)
            os_face = adj_map['faces'][ap.parent.identifier]
            os_ap.setSurface(os_face)
            adj_map['sub_faces'][ap.identifier] = os_ap
    tri_doors, _ = model.triangulated_doors()
    for tri_drs in tri_doors:
        for i, dr in enumerate(tri_drs):
            if i != 0:
                dr.properties.energy.vent_opening = None
            os_dr = door_to_openstudio(dr, model)
            os_face = adj_map['faces'][dr.parent.identifier]
            os_dr.setSurface(os_face)
            adj_map['sub_faces'][dr.identifier] = os_dr

    # assign stories to the rooms
    for story_id, os_spaces in story_map.items():
        story = OSBuildingStory(os_model)
        if story_id is not None:  # the users has specified the name of the story
            story.setName(story_id)
        else:  # give the room a dummy story so that it works with David's measures
            story.setName('UndefinedStory')
        for os_space in os_spaces:
            os_space.setBuildingStory(story)

    # assign adjacencies to all of the rooms
    already_adj = set()
    for room in model.rooms:
        for face in room.faces:
            if isinstance(face.boundary_condition, Surface):
                if face.identifier not in already_adj:
                    # add the adjacency to the set
                    adj_id = face.boundary_condition.boundary_condition_object
                    already_adj.add(adj_id)
                    # get the openstudio Surfaces and set the adjacency
                    base_os_face = adj_map['faces'][face.identifier]
                    adj_os_face = adj_map['faces'][adj_id]
                    base_os_face.setAdjacentSurface(adj_os_face)
                    # set the adjacency of all sub-faces
                    for sub_face in face.sub_faces:
                        adj_id = sub_face.boundary_condition.boundary_condition_object
                        base_os_sub_face = adj_map['sub_faces'][sub_face.identifier]
                        adj_os_sub_face = adj_map['sub_faces'][adj_id]
                        base_os_sub_face.setAdjacentSubSurface(adj_os_sub_face)

    # if simple ventilation is being used, add air mixing objects
    vent_sim_control = model.properties.energy.ventilation_simulation_control
    if vent_sim_control.vent_control_type == 'SingleZone':
        for room in model.rooms:
            for face in room.faces:
                if isinstance(face.type, AirBoundary):  # write the air mixing objects
                    try:
                        adj_room = face.boundary_condition.boundary_condition_objects[-1]
                        target_zone = zone_dict[room.identifier]
                        source_zone = zone_dict[adj_room]
                        air_mixing_to_openstudio(face, target_zone, source_zone, os_model)
                    except AttributeError as e:
                        raise ValueError(
                            'Face "{}" is an Air Boundary but lacks a Surface boundary '
                            'condition.\n{}'.format(face.full_id, e))

    # assign HVAC systems to all of the rooms
    zone_rooms = {room.zone: room for room in single_zones}
    for zone_id, zone_data in zone_dict.items():
        for room in zone_data[0]:
            if room.properties.energy.hvac is not None:
                zone_rooms[zone_id] = room
                break
    for zone_id, room in zone_rooms.items():
        hvac = room.properties.energy.hvac
        if isinstance(hvac, IdealAirSystem):
            os_hvac = ideal_air_system_to_openstudio(hvac, os_model, room)
            if room.identifier != zone_id:
                os_hvac.setName('{} Ideal Loads Air System'.format(zone_id))
            os_zone = zone_map[room.identifier]
            os_hvac.addToThermalZone(os_zone)

    # write service hot water and any SHW systems
    shw_sys_dict = {}
    for room in model.rooms:
        hot_water = room.properties.energy.service_hot_water
        if hot_water is not None and hot_water.flow_per_area != 0:
            os_shw_conn = hot_water_to_openstudio(hot_water, room, os_model)
            total_flow = (hot_water.flow_per_area / 3600000.) * room.floor_area
            water_temp = hot_water.target_temperature
            shw_sys = room.properties.energy.shw
            shw_sys_id = shw_sys.identifier \
                if shw_sys is not None else 'Default_District_SHW'
            try:  # try to add the hot water to the existing system
                shw_sys_props = shw_sys_dict[shw_sys_id]
                shw_sys_props[1].append(os_shw_conn)
                shw_sys_props[2] += total_flow
                if water_temp > shw_sys_props[3]:
                    shw_sys_props[3] = water_temp
            except KeyError:  # first time that the SHW system is encountered
                shw_sys_props = [shw_sys, [os_shw_conn], total_flow, water_temp]
                shw_sys_dict[shw_sys_id] = shw_sys_props
    if len(shw_sys_dict) != 0:
        # add all of the SHW Systems to the model 
        for shw_sys_props in shw_sys_dict.values():
            shw_sys, os_shw_conns, total_flow, w_temp = shw_sys_props
            shw_system_to_openstudio(shw_sys, os_shw_conns, total_flow, w_temp, os_model)

    # write any EMS programs for dynamic constructions
    if len(dynamic_cons) != 0:
        # create the program calling manager
        os_prog_manager = OSEnergyManagementSystemProgramCallingManager(os_model)
        os_prog_manager.setName('Dynamic_Window_Constructions')
        os_prog_manager.setCallingPoint('BeginTimestepBeforePredictor')
        # get all of the sub-faces with the dynamic construction
        dyn_dict = {}
        for room in model.rooms:
            for face in room.faces:
                for sf in face.sub_faces:
                    con = sf.properties.energy.construction
                    if isinstance(con, WindowConstructionDynamic):
                        os_sf = adj_map['sub_faces'][sf.identifier]
                        try:
                            dyn_dict[con.identifier].append(os_sf)
                        except KeyError:
                            dyn_dict[con.identifier] = [os_sf]
        for con in dynamic_cons:
            ems_program = window_dynamic_ems_program_to_openstudio(
                con, dyn_dict[con.identifier], os_model)
            os_prog_manager.addProgram(ems_program)

    # add the orphaned objects
    for face in model.orphaned_faces:
        face_to_openstudio(face, os_model)
    for aperture in model.orphaned_apertures:
        aperture_to_openstudio(aperture, os_model)
    for door in model.orphaned_doors:
        door_to_openstudio(door, os_model)
    for shade in model.orphaned_shades:
        shade_to_openstudio(shade, os_model)
    for shade_mesh in model.shade_meshes:
        shade_mesh_to_openstudio(shade_mesh, os_model)

    # return the Model object
    return os_model


def _instance_in_array(object_instance, object_array):
    """Check if a specific object instance is already in an array.

    This can be much faster than  `if object_instance in object_array`
    when you expect to be testing a lot of the same instance of an object for
    inclusion in an array since the builtin method uses an == operator to
    test inclusion.
    """
    for val in object_array:
        if val is object_instance:
            return True
    return False
