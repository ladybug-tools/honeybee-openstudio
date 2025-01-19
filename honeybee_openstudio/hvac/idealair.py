# coding=utf-8
"""OpenStudio IdealLoadsAirSystem translator."""
from __future__ import division
from honeybee.altnumber import autosize, no_limit

from honeybee_openstudio.openstudio import OSZoneHVACIdealLoadsAirSystem


def ideal_air_system_to_openstudio(hvac, os_model, room=None):
    """Convert Honeybee IdealAirSystem to OpenStudio ZoneHVACIdealLoadsAirSystem.

    Args:
        hvac: A Honeybee-energy IdealAirSystem to be translated to OpenStudio.
        os_model: The OpenStudio Model object to which the IdealAirSystem
            will be added.
        room: An optional Honeybee Room to be used to set various properties
            of the system (including the EnergyPlus name, and humidity control).
    """
    # create openstudio ideal air system object
    os_ideal_air = OSZoneHVACIdealLoadsAirSystem(os_model)
    if room is None:
        os_ideal_air.setName(hvac.identifier)
    else:
        os_ideal_air.setName('{} Ideal Loads Air System'.format(room.identifier))
    if hvac._display_name is not None:
        hvac.setDisplayName(hvac.display_name)
    # assign the dehumidification based on the room
    os_ideal_air.setDehumidificationControlType('None')  # default when no humidistat
    if room is not None:
        setpoint = room.properties.energy.setpoint
        if setpoint.humidifying_schedule is not None:
            os_ideal_air.setDehumidificationControlType('Humidistat')
            os_ideal_air.setHumidificationControlType('Humidistat')
    # assign the economizer type
    os_ideal_air.setOutdoorAirEconomizerType(hvac.economizer_type)
    # set the sensible and latent heat recovery
    if hvac.sensible_heat_recovery != 0:
        os_ideal_air.setSensibleHeatRecoveryEffectiveness(hvac.sensible_heat_recovery)
        os_ideal_air.setHeatRecoveryType('Sensible')
    else:
        os_ideal_air.setSensibleHeatRecoveryEffectiveness(0)
    if hvac.latent_heat_recovery != 0:
        os_ideal_air.setLatentHeatRecoveryEffectiveness(hvac.latent_heat_recovery)
        os_ideal_air.setHeatRecoveryType('Enthalpy')
    else:
        os_ideal_air.setLatentHeatRecoveryEffectiveness(0)
    # assign the demand controlled ventilation
    if hvac.demand_controlled_ventilation:
        os_ideal_air.setDemandControlledVentilationType('OccupancySchedule')
    else:
        os_ideal_air.setDemandControlledVentilationType('None')
    # set the heating and cooling supply air temperature
    os_ideal_air.setMaximumHeatingSupplyAirTemperature(hvac.heating_air_temperature)
    os_ideal_air.setMinimumCoolingSupplyAirTemperature(hvac.cooling_air_temperature)
    # assign limits to the system's heating capacity
    if hvac.heating_limit == no_limit:
        os_ideal_air.setHeatingLimit('NoLimit')
    else:
        os_ideal_air.setHeatingLimit('LimitCapacity')
    if hvac.heating_limit == autosize:
        os_ideal_air.autosizeMaximumSensibleHeatingCapacity()
    else:
        os_ideal_air.setMaximumSensibleHeatingCapacity(hvac.heating_limit)
    # assign limits to the system's cooling capacity
    if hvac.cooling_limit == no_limit:
        os_ideal_air.setCoolingLimit('NoLimit')
    else:
        os_ideal_air.setCoolingLimit('LimitFlowRateAndCapacity')
    if hvac.cooling_limit == autosize:
        os_ideal_air.autosizeMaximumTotalCoolingCapacity()
        os_ideal_air.autosizeMaximumCoolingAirFlowRate()
    else:
        os_ideal_air.setMaximumTotalCoolingCapacity(hvac.cooling_limit)
        os_ideal_air.autosizeMaximumCoolingAirFlowRate()
    # assign heating availability schedule
    if hvac.heating_availability is not None:
        os_schedule = os_model.getScheduleByName(hvac.heating_availability.identifier)
        if os_schedule.is_initialized():
            os_schedule = os_schedule.get()
            os_ideal_air.setHeatingAvailabilitySchedule(os_schedule)
    # assign cooling availability schedule
    if hvac.cooling_availability is not None:
        os_schedule = os_model.getScheduleByName(hvac.cooling_availability.identifier)
        if os_schedule.is_initialized():
            os_schedule = os_schedule.get()
            os_ideal_air.setCoolingAvailabilitySchedule(os_schedule)
    return os_ideal_air
