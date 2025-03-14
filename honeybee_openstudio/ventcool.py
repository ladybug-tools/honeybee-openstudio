# coding=utf-8
"""OpenStudio ventilative cooling translators."""
from __future__ import division

from honeybee_energy.ventcool.control import VentilationControl

from honeybee_openstudio.openstudio import OSZoneVentilationWindandStackOpenArea, \
    OSZoneVentilationDesignFlowRate, OSAirflowNetworkCrack, OSAirflowNetworkSimpleOpening, \
    OSAirflowNetworkHorizontalOpening, OSAirflowNetworkReferenceCrackConditions


def ventilation_opening_to_openstudio(opening, os_model):
    """Convert VentilationOpening to OpenStudio ZoneVentilationWindandStackOpenArea.

    Args:
        opening: The Honeybee VentilationOpening object to be translated
            to OpenStudio. Note that this object must be assigned to a parent
            Aperture with a parent Room in order to be successfully translated.
        os_model: The OpenStudio model to which the ZoneVentilationWindandStackOpenArea
            is to be added.
    """
    # check that a parent is assigned
    assert opening.parent is not None, 'VentilationOpening must be assigned ' \
        'to an Aperture or Door to translate to_openstudio.'
    # get the VentilationControl object from the room
    control = None
    room = None
    if opening.parent.has_parent:
        if opening.parent.parent.has_parent:
            room = opening.parent.parent.parent
            if room.properties.energy.window_vent_control is not None:
                control = room.properties.energy.window_vent_control
    if control is None:  # use default ventilation control
        control = VentilationControl()
    assert room is not None, 'VentilationOpening must have a parent Room to ' \
        'translate to_openstudio.'
    # process the properties on this object into IDF format
    angle = opening.parent.horizontal_orientation() \
        if opening.parent.normal.z != 1 else 0
    angle = angle % 360
    height = (opening.parent.geometry.max.z - opening.parent.geometry.min.z) * \
        opening.fraction_height_operable
    # create wind and stack object and set all of its properties
    os_opening = OSZoneVentilationWindandStackOpenArea(os_model)
    os_opening.setName('{}_Opening'.format(opening.parent.identifier))
    os_opening.setOpeningArea(opening.parent.area * opening.fraction_area_operable)
    os_opening.setHeightDifference(height)
    os_opening.setEffectiveAngle(angle)
    os_opening.setDischargeCoefficientforOpening(opening.discharge_coefficient)
    if opening.wind_cross_vent:
        os_opening.autocalculateOpeningEffectiveness()
    else:
        os_opening.setOpeningEffectiveness(0)
    # set the properties of the ventilation control
    os_opening.setMinimumIndoorTemperature(control.min_indoor_temperature)
    os_opening.setMaximumIndoorTemperature(control.max_indoor_temperature)
    os_opening.setMinimumOutdoorTemperature(control.min_outdoor_temperature)
    os_opening.setMaximumOutdoorTemperature(control.max_outdoor_temperature)
    os_opening.setDeltaTemperature(control.delta_temperature)
    if control.schedule is not None:
        vent_sch = os_model.getScheduleByName(control.schedule.identifier)
        if vent_sch.is_initialized():
            os_vent_sch = vent_sch.get()
            os_opening.setOpeningAreaFractionSchedule(os_vent_sch)
    return os_opening


def ventilation_fan_to_openstudio(fan, os_model):
    """Convert VentilationFan to OpenStudio ZoneVentilationDesignFlowRate."""
    # create zone ventilation object and set identifier
    os_fan = OSZoneVentilationDesignFlowRate(os_model)
    os_fan.setName(fan.identifier)
    if fan._display_name is not None:
        os_fan.setDisplayName(fan.display_name)
    # assign fan properties
    os_fan.setDesignFlowRate(fan.flow_rate)
    os_fan.setFanPressureRise(fan.pressure_rise)
    os_fan.setFanTotalEfficiency(fan.efficiency)
    os_fan.setVentilationType(fan.ventilation_type)
    # set all of the ventilation control properties
    os_fan.setMinimumIndoorTemperature(fan.control.min_indoor_temperature)
    os_fan.setMaximumIndoorTemperature(fan.control.max_indoor_temperature)
    os_fan.setMinimumOutdoorTemperature(fan.control.min_outdoor_temperature)
    os_fan.setMaximumOutdoorTemperature(fan.control.max_outdoor_temperature)
    os_fan.setDeltaTemperature(fan.control.delta_temperature)
    # assign schedule if it exists
    if fan.control.schedule is not None:
        vent_sch = os_model.getScheduleByName(fan.control.schedule.identifier)
        if vent_sch.is_initialized():
            os_vent_sch = vent_sch.get()
            os_fan.setSchedule(os_vent_sch)
    return os_fan


def ventilation_opening_to_openstudio_afn(opening, os_model, os_reference_crack=None):
    """Convert VentilationOpening to OpenStudio AirflowNetworkSurface.

    The returned output will be None if the VentilationOpening's parent
    Subface is not yet in the OpenStudio Model.

    Args:
        opening: The Honeybee VentilationOpening object to be translated
            to OpenStudio. Note that this object must be assigned to a parent
            Aperture with a parent Room in order to be successfully translated.
        os_model: The OpenStudio model to which the AirflowNetworkSurface
            is to be added.
        os_reference_crack: An optional AirflowNetworkReferenceCrackConditions
            object to set the reference when the ventilation opening is being
            translated to a large crack. This happens when the ventilation
            opening is horizontal and in an outdoor Face.
    """
    # check that a parent is assigned
    assert opening.parent is not None, 'VentilationOpening must be assigned ' \
        'to an Aperture or Door to translate to_openstudio.'
    # get the tilt and BC of the parent so that we can use the correct AFN object
    srf_tilt = opening.parent.tilt
    srf_bc = opening.parent.boundary_condition.name
    # process the flow coefficient, flow exponent and fraction area operable
    flow_coefficient = opening.flow_coefficient_closed \
        if opening.flow_coefficient_closed > 1.0e-09 else 1.0e-09
    flow_exponent = 0.65  # default value
    discharge_coeff = 0.45  # default value
    two_way_thresh = 0.0001  # default value
    open_fac = opening.fraction_area_operable
    # create an opening obj
    if srf_tilt < 10 or srf_tilt > 170:
        if srf_bc == 'Outdoors':
            # create a crack object to represent an exterior in-operable horizontal skylight
            open_fac = None
            if os_reference_crack is None:
                os_reference_crack = OSAirflowNetworkReferenceCrackConditions(os_model)
                os_reference_crack.setTemperature(20)
                os_reference_crack.setBarometricPressure(101325)
                os_reference_crack.setHumidityRatio(0)
            os_opening = OSAirflowNetworkCrack(
                os_model, flow_coefficient, flow_exponent, os_reference_crack)
        else:
            # create a HorizontalOpening object to for the interior horizontal window
            slope_ang = 90 - srf_tilt if srf_tilt < 10 else 90 - (180 - srf_tilt)
            os_opening = OSAirflowNetworkHorizontalOpening(
                os_model, flow_coefficient, flow_exponent, slope_ang, discharge_coeff)
    else:
        # create the simple opening object for the Aperture or Door using default values
        os_opening = OSAirflowNetworkSimpleOpening(
          os_model, flow_coefficient, flow_exponent, two_way_thresh, discharge_coeff)
        os_opening.setAirMassFlowExponentWhenOpeningisClosed(opening.flow_exponent_closed)
        os_opening.setMinimumDensityDifferenceforTwoWayFlow(opening.two_way_threshold)
        os_opening.setDischargeCoefficient(opening.discharge_coefficient)

    # create the AirflowNetworkSurface and assign the opening factor
    opt_sub_f = os_model.getSubSurfaceByName(opening.parent.identifier)
    if opt_sub_f.is_initialized():
        sub_f = opt_sub_f.get()
        os_afn_srf = sub_f.getAirflowNetworkSurface(os_opening)
        if open_fac is not None:
            os_afn_srf.setWindowDoorOpeningFactorOrCrackFactor(open_fac)
        return os_afn_srf
