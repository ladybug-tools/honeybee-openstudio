# coding=utf-8
"""OpenStudio ConstructionSet translator."""
from __future__ import division
from honeybee_energy.construction.dynamic import WindowConstructionDynamic

from honeybee_openstudio.openstudio import OSDefaultConstructionSet, \
    OSDefaultSurfaceConstructions, OSDefaultSubSurfaceConstructions


def _assign_construction_to_subset(construction, os_constr_subset, face_type, os_model):
    """Assign a Honeybee construction object to an OpenStudio sub-set.

    Args:
        construction: The honeybee-energy construction object assigned to the
            ConstructionsSet (this can be None).
        os_constr_subset: The OpenStudio DefaultSurfaceConstructions object
            to which the construction will be added.
        face_type: Text for the type of Face to which the construction will be
            added. Must be either Wall, Floor or RoofCeiling.
        os_model: The OpenStudio Model.
    """
    if construction is not None:
        construction_ref = os_model.getConstructionByName(construction.identifier)
        if construction_ref.is_initialized():
            os_construction = construction_ref.get()
            if face_type == 'Wall':
                os_constr_subset.setWallConstruction(os_construction)
            elif face_type == 'Floor':
                os_constr_subset.setFloorConstruction(os_construction)
            else:
                os_constr_subset.setRoofCeilingConstruction(os_construction)


def _glazing_construction(construction, os_model):
    """Get an OpenStudio window construction with a check for dynamic constructions."""
    if construction is None:
        return None
    construction_id = construction.identifier \
        if not isinstance(construction, WindowConstructionDynamic) \
        else construction.constructions[0].identifier
    constr_ref = os_model.getConstructionByName(construction_id)
    if constr_ref.is_initialized():
        os_construction = constr_ref.get()
        return os_construction


def construction_set_to_openstudio(construction_set, os_model):
    """Convert Honeybee ConstructionSet to OpenStudio DefaultConstructionSet."""
    # create the construction set object
    os_constr_set = OSDefaultConstructionSet(os_model)
    os_constr_set.setName(construction_set.identifier)
    if construction_set._display_name is not None:
        os_constr_set.setDisplayName(construction_set.display_name)

    int_surf_const = OSDefaultSurfaceConstructions(os_model)
    ext_surf_const = OSDefaultSurfaceConstructions(os_model)
    grnd_surf_const = OSDefaultSurfaceConstructions(os_model)
    int_subsurf_const = OSDefaultSubSurfaceConstructions(os_model)
    ext_subsurf_const = OSDefaultSubSurfaceConstructions(os_model)

    os_constr_set.setDefaultInteriorSurfaceConstructions(int_surf_const)
    os_constr_set.setDefaultExteriorSurfaceConstructions(ext_surf_const)
    os_constr_set.setDefaultGroundContactSurfaceConstructions(grnd_surf_const)
    os_constr_set.setDefaultInteriorSubSurfaceConstructions(int_subsurf_const)
    os_constr_set.setDefaultExteriorSubSurfaceConstructions(ext_subsurf_const)

    # determine the frame type for measure tags
    frame_type = 'Metal Framing with Thermal Break' \
        if 'WoodFramed' in construction_set.identifier else 'Non-Metal Framing'

    # assign the constructions in the wall set
    int_con = construction_set.wall_set._interior_construction
    if int_con is not None:
        int_wall_ref = os_model.getConstructionByName(int_con.identifier)
        if int_wall_ref.is_initialized():
            interior_wall = int_wall_ref.get()
            int_surf_const.setWallConstruction(interior_wall)
            os_constr_set.setAdiabaticSurfaceConstruction(interior_wall)
    ext_con = construction_set.wall_set._exterior_construction
    _assign_construction_to_subset(ext_con, ext_surf_const, 'Wall', os_model)
    ground_con = construction_set.wall_set._ground_construction
    _assign_construction_to_subset(ground_con, grnd_surf_const, 'Wall', os_model)

    # assign the constructions in the floor set
    int_con = construction_set.floor_set._interior_construction
    _assign_construction_to_subset(int_con, int_surf_const, 'Floor', os_model)
    ext_con = construction_set.floor_set._exterior_construction
    _assign_construction_to_subset(ext_con, ext_surf_const, 'Floor', os_model)
    ground_con = construction_set.floor_set._ground_construction
    _assign_construction_to_subset(ground_con, grnd_surf_const, 'Floor', os_model)

    # assign the constructions in the roof ceiling set
    int_con = construction_set.roof_ceiling_set._interior_construction
    _assign_construction_to_subset(int_con, int_surf_const, 'RoofCeiling', os_model)
    ext_con = construction_set.roof_ceiling_set._exterior_construction
    _assign_construction_to_subset(ext_con, ext_surf_const, 'RoofCeiling', os_model)
    ground_con = construction_set.roof_ceiling_set._ground_construction
    _assign_construction_to_subset(ground_con, grnd_surf_const, 'RoofCeiling', os_model)

    # assign the constructions in the aperture set
    int_ap_con = construction_set.aperture_set._interior_construction
    int_ap_con = _glazing_construction(int_ap_con, os_model)
    if int_ap_con is not None:
        int_subsurf_const.setFixedWindowConstruction(int_ap_con)
        int_subsurf_const.setOperableWindowConstruction(int_ap_con)
        int_subsurf_const.setSkylightConstruction(int_ap_con)
    win_ap_con = construction_set.aperture_set._window_construction
    win_ap_con = _glazing_construction(win_ap_con, os_model)
    if win_ap_con is not None:
        ext_subsurf_const.setFixedWindowConstruction(win_ap_con)
        std_info = win_ap_con.standardsInformation()
        std_info.setFenestrationType('Fixed Window')
        std_info.setFenestrationFrameType(frame_type)
        std_info.setIntendedSurfaceType('ExteriorWindow')
    sky_ap_con = construction_set.aperture_set._skylight_construction
    sky_ap_con = _glazing_construction(sky_ap_con, os_model)
    if sky_ap_con is not None:
        ext_subsurf_const.setSkylightConstruction(sky_ap_con)
        std_info = sky_ap_con.standardsInformation()
        std_info.setFenestrationType('Fixed Window')
        std_info.setFenestrationFrameType(frame_type)
        if not std_info.intendedSurfaceType().is_initialized():
            std_info.setIntendedSurfaceType('Skylight')
    op_ap_con = construction_set.aperture_set._operable_construction
    op_ap_con = _glazing_construction(op_ap_con, os_model)
    if op_ap_con is not None:
        ext_subsurf_const.setOperableWindowConstruction(op_ap_con)
        std_info = op_ap_con.standardsInformation()
        std_info.setFenestrationFrameType(frame_type)
        std_info.setIntendedSurfaceType('ExteriorWindow')
        if not std_info.intendedSurfaceType().is_initialized():
            std_info.setFenestrationType('Operable Window')

    # assign the constructions in the door set
    int_dr_con = construction_set.door_set._interior_construction
    if int_dr_con is not None:
        int_door_ref = os_model.getConstructionByName(int_dr_con.identifier)
        if int_door_ref.is_initialized():
            interior_door = int_door_ref.get()
            int_subsurf_const.setDoorConstruction(interior_door)
            int_subsurf_const.setOverheadDoorConstruction(interior_door)
    ext_dr_con = construction_set.door_set._exterior_construction
    if ext_dr_con is not None:
        ext_door_ref = os_model.getConstructionByName(ext_dr_con.identifier)
        if ext_door_ref.is_initialized():
            exterior_door = ext_door_ref.get()
            ext_subsurf_const.setDoorConstruction(exterior_door)
            std_info = exterior_door.standardsInformation()
            if not std_info.intendedSurfaceType().is_initialized():
                std_info.setIntendedSurfaceType('ExteriorDoor')
    ov_dr_con = construction_set.door_set._overhead_construction
    if ov_dr_con is not None:
        overhead_door_ref = os_model.getConstructionByName(ov_dr_con.identifier)
        if overhead_door_ref.is_initialized():
            overhead_door = overhead_door_ref.get()
            ext_subsurf_const.setOverheadDoorConstruction(overhead_door)
            std_info = overhead_door.standardsInformation()
            if not std_info.intendedSurfaceType().is_initialized():
                std_info.setIntendedSurfaceType('OverheadDoor')
    ext_glz_for_con = construction_set.door_set._exterior_glass_construction
    ext_glz_for_con = _glazing_construction(ext_glz_for_con, os_model)
    if ext_glz_for_con is not None:
        ext_subsurf_const.setGlassDoorConstruction(ext_glz_for_con)
        std_info = ext_glz_for_con.standardsInformation()
        if not std_info.fenestrationType().is_initialized():
            std_info.setFenestrationType('Glazed Door')
        std_info.setFenestrationFrameType(frame_type)
        if not std_info.intendedSurfaceType().is_initialized():
            std_info.setIntendedSurfaceType('GlassDoor')
    int_glz_for_con = construction_set.door_set._interior_glass_construction
    int_glz_for_con = _glazing_construction(int_glz_for_con, os_model)
    if int_glz_for_con is not None:
        int_subsurf_const.setGlassDoorConstruction(int_glz_for_con)

    # assign the shading construction to construction set
    shade_con = construction_set._shade_construction
    if shade_con is not None:
        shade_ref = os_model.getConstructionByName(shade_con.identifier)
        if shade_ref.is_initialized():
            shade_construction = shade_ref.get()
            os_constr_set.setSpaceShadingConstruction(shade_construction)

    return os_constr_set
