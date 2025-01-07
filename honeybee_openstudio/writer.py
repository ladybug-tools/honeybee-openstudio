# coding=utf-8
"""Methods to write to OpenStudio."""
import openstudio

from ladybug_geometry.geometry3d import Face3D
from honeybee.typing import clean_ep_string
from honeybee.altnumber import autocalculate
from honeybee.facetype import RoofCeiling, Floor, AirBoundary
from honeybee.boundarycondition import Outdoors, Ground, Surface
from honeybee_energy.boundarycondition import OtherSideTemperature


def face_3d_to_openstudio(face_3d):
    """Convert a Face3D into an OpenStudio Point3dVector.

    Args:
        face_3d: A ladybug-geometry Face3D object for which an OpenStudio Point3dVector
            string will be generated.

    Returns:
        An OpenStudio Point3dVector to be used to construct geometry objects.
    """
    os_vertices = openstudio.Point3dVector()
    for pt in face_3d.upper_left_counter_clockwise_vertices:
        os_vertices.append(openstudio.Point3d(pt.x, pt.y, pt.z))
    return os_vertices


def shade_mesh_to_openstudio(shade_mesh, model):
    """Create OpenStudio objects from a ShadeMesh.

    Args:
        shade_mesh: A honeybee ShadeMesh for which OpenStudio objects will be returned.
        model: The OpenStudio Model object to which the ShadeMesh will be added.

    Returns:
        A list of OpenStudio ShadingSurface objects.
    """
    # loop through the mesh faces and create individual shade objects
    os_shades = []
    os_shd_group = openstudio.model.ShadingSurfaceGroup(model)
    os_shd_group.setName(shade_mesh.identifier)
    for i, shade in enumerate(shade_mesh.geometry.face_vertices):
        shade_face = Face3D(shade)
        os_vertices = face_3d_to_openstudio(shade_face)
        os_shade = openstudio.model.ShadingSurface(os_vertices, model)
        os_shade.setName('{}_{}'.format(shade_mesh.identifier, i))
        os_shade.setShadingSurfaceGroup(os_shd_group)
        os_shades.append(os_shade)
    return os_shades


def shade_to_openstudio(shade, model):
    """Create an OpenStudio object from a Shade.

    Args:
        shade: A honeybee Shade for which an OpenStudio object will be returned.
        model: The OpenStudio Model object to which the Shade will be added.

    Returns:
        An OpenStudio ShadingSurface object.
    """
    os_vertices = face_3d_to_openstudio(shade.geometry)
    os_shade = openstudio.model.ShadingSurface(os_vertices, model)
    os_shade.setName(shade.identifier)
    return os_shade


def door_to_openstudio(door, model):
    """Create an OpenStudio object from a Door.

    Args:
        door: A honeybee Door for which an OpenStudio object will be returned.
        model: The OpenStudio Model object to which the Door will be added.

    Returns:
        An OpenStudio SubSurface object if the Door has a parent. An OpenStudio
        ShadingSurface object if the Door has no parent.
    """
    # convert the base geometry to OpenStudio
    os_vertices = face_3d_to_openstudio(door.geometry)
    # translate the geometry to either a SubSurface or a ShadingSurface
    if door.has_parent:
        os_door = openstudio.model.SubSurface(os_vertices, model)
        if door.is_glass:
            dr_type = 'GlassDoor'
        else:
            par = door.parent
            dr_type = 'OverheadDoor' if isinstance(par.boundary_condition, Outdoors) and \
                isinstance(par.type, (RoofCeiling, Floor)) else 'Door'
        os_door.setSubSurfaceType(dr_type)
    else:
        os_door = openstudio.model.ShadingSurface(os_vertices, model)
        for shd in door._outdoor_shades:
            shade_to_openstudio(shd, model)

    # set the object name and return it
    os_door.setName(door.identifier)
    return os_door


def aperture_to_openstudio(aperture, model):
    """Create an OpenStudio object from an Aperture.

    Args:
        aperture: A honeybee Aperture for which an OpenStudio object will be returned.
        model: The OpenStudio Model object to which the Aperture will be added.

    Returns:
        An OpenStudio SubSurface object if the Aperture has a parent. An OpenStudio
        ShadingSurface object if the Aperture has no parent.
    """
    # convert the base geometry to OpenStudio
    os_vertices = face_3d_to_openstudio(aperture.geometry)
    # translate the geometry to either a SubSurface or a ShadingSurface
    if aperture.has_parent:
        os_aperture = openstudio.model.SubSurface(os_vertices, model)
        if aperture.is_operable:
            ap_type = 'OperableWindow'
        else:
            par = aperture.parent
            ap_type = 'Skylight' if isinstance(par.boundary_condition, Outdoors) and \
                isinstance(par.type, (RoofCeiling, Floor)) else 'FixedWindow'
        os_aperture.setSubSurfaceType(ap_type)
    else:
        os_aperture = openstudio.model.ShadingSurface(os_vertices, model)
        for shd in aperture._outdoor_shades:
            shade_to_openstudio(shd, model)

    # set the object name and return it
    os_aperture.setName(aperture.identifier)
    return os_aperture


def face_to_openstudio(face, model, adj_map=None):
    """Create an OpenStudio object from a Face.

    This method also adds all Apertures, Doors, and Shades assigned to the Face.

    Args:
        face: A honeybee Face for which an OpenStudio object will be returned.
        model: The OpenStudio Model object to which the Face will be added.
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
        os_face = openstudio.model.Surface(os_vertices, model)

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
            srf_prop = openstudio.model.SurfacePropertyOtherSideCoefficients(model)
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

        # create the sub-faces
        sub_faces = {}
        for ap in face.apertures:
            os_ap = aperture_to_openstudio(ap, model)
            os_ap.setSurface(os_face)
            sub_faces[ap.identifier] = os_ap
        for dr in face.doors:
            os_dr = door_to_openstudio(dr, model)
            os_dr.setSurface(os_face)
            sub_faces[dr.identifier] = os_dr

        # update the adjacency map if it exists
        if adj_map is not None:
            adj_map['faces'][face.identifier] = os_face
            adj_map['sub_faces'].update(sub_faces)
    else:
        os_vertices = face_3d_to_openstudio(face.punched_geometry)
        os_face = openstudio.model.ShadingSurface(os_vertices, model)
        for ap in face.apertures:
            aperture_to_openstudio(ap.duplicate(), model)
        for dr in face.doors:
            door_to_openstudio(dr.duplicate(), model)
        for shd in face._outdoor_shades:
            shade_to_openstudio(shd, model)

    # set the object name and return it
    os_face.setName(face.identifier)
    return os_face


def room_to_openstudio(room, model, adj_map=None):
    """Create OpenStudio objects from a Room.

    Args:
        room: A honeybee Room for which an OpenStudio object will be returned.
        model: The OpenStudio Model object to which the Room will be added.
        adj_map: An optional dictionary with keys for 'faces' and 'sub_faces'
            that will have the space Surfaces and SubSurfaces added to it
            such that adjacencies can be assigned after running this method.

    Returns:
        An OpenStudio Space object for the Room.
    """
    # create the space and thermal zone
    os_space = openstudio.model.Space(model)
    os_space.setName('{}_Space'.format(room.identifier))
    os_zone = openstudio.model.ThermalZone(model)
    os_zone.setName(room.identifier)
    os_space.setThermalZone(os_zone)

    # assign the multiplier, exclude_floor_area, and geometry properties
    if room.multiplier != 1:
        os_zone.setMultiplier(room.multiplier)
    if room.exclude_floor_area:
        os_space.setPartofTotalFloorArea(False)
    os_zone.setCeilingHeight(room.geometry.max.z - room.geometry.min.z)
    os_zone.setVolume(room.volume)

    # assign all of the faces to the room
    for face in room.faces:
        os_face = face_to_openstudio(face, model, adj_map)
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
        os_shd_group = openstudio.model.ShadingSurfaceGroup(model)
        os_shd_group.setName('{} Shades'.format(room.identifier))
        os_shd_group.setSpace(os_space)
        os_shd_group.setShadingSurfaceType('Space')
        for shd in child_shades:
            os_shade = shade_to_openstudio(shd, model)
            os_shade.setShadingSurfaceGroup(os_shd_group)

    return os_space


def model_to_openstudio(model, seed_model=None):
    """Create an OpenStudio Model from a Honeybee Model.

    The resulting Model will include all geometry (Rooms, Faces, Apertures,
    Doors, Shades), all fully-detailed constructions + materials, all fully-detailed
    schedules, and the room properties.

    Args:
        model: The Honeybee Model to be converted into an OpenStudio Model.

    Usage:

    .. code-block:: python

        import os
        import openstudio
        from honeybee.model import Model
        from honeybee.room import Room
        from honeybee.config import folders

        # Crate an input Model
        room = Room.from_box('Tiny House Zone', 5, 10, 3)
        room.properties.energy.program_type = office_program
        room.properties.energy.add_default_ideal_air()
        hb_model = Model('Tiny House', [room])

        # translate the honeybee model to an openstudio model
        os_model = model.to.openstudio(model)

        # save the OpenStudio model to an OSM
        osm = os.path.join(folders.default_simulation_folder, 'in.osm')
        model.save(osm, overwrite=True)

        # save the OpenStudio model to an IDF file
        idf_translator = openstudio.energyplus.ForwardTranslator()
        workspace = idf_translator.translateModel(os_model)
        idf = os.path.join(folders.default_simulation_folder, 'in.idf')
        workspace.save(idf, overwrite=True)
    """
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

    # create the OpenStudio model object
    os_model = openstudio.model.Model() if seed_model is None else seed_model
    building = os_model.getBuilding()
    if model._display_name is not None:
        building.setName(clean_ep_string(model.display_name))
    else:
        building.setName(model.identifier)

    # TODO: translate all of the schedules, constructions and programs

    # create all of the rooms
    story_map = {}
    adj_map = {'faces': {}, 'sub_faces': {}}
    for room in model.rooms:
        os_space = room_to_openstudio(room, os_model, adj_map)
        try:
            story_map[room.story].append(os_space)
        except KeyError:  # first room found on the story
            story_map[room.story] = [os_space]

    # assign stories to the rooms
    for story_id, os_spaces in story_map.items():
        story = openstudio.model.BuildingStory(os_model)
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
