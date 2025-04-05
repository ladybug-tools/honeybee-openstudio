# coding=utf-8
"""OpenStudio translators for template HVAC systems."""
from __future__ import division

from honeybee.typing import clean_ep_string
from honeybee_energy.hvac.allair._base import _AllAirBase
from honeybee_energy.hvac.doas._base import _DOASBase

from honeybee_openstudio.openstudio import openstudio_model
from .standards.hvac_systems import model_add_hvac_system


def template_hvac_to_openstudio(hvac, os_zones, os_model):
    """Convert Honeybee HVAC TemplateSystem to OpenStudio.

    Args:
        hvac: Any honeybee-energy TemplateSystem class instance to be translated
            to OpenStudio.
        os_zones: A dictionary with two keys, each of which has a value for a
            list of OpenStudio ThermalZones. The keys are heated_zones and
            cooled_zones and the lists under each key note the OpenStudio
            ThermalZones to be given heating and cooling equipment by the HVAC.
        os_model: The OpenStudio Model object to which the HVAC system
            will be added.
    """
    # unpack the heated and cooled zones and organize them into groups
    heated_zones, cooled_zones = os_zones['heated_zones'], os_zones['cooled_zones']
    heated_and_cooled_zones, cooled_only_zones, heated_only_zones = [], [], []
    heat_dict = {z.nameString(): z for z in heated_zones}
    cool_dict = {z.nameString(): z for z in cooled_zones}
    for zone in heated_zones + cooled_zones:
        zone_name = zone.nameString()
        if zone_name in heat_dict and zone_name in cool_dict:
            heated_and_cooled_zones.append(zone)
        elif zone_name in cool_dict:
            cooled_only_zones.append(zone)
        else:
            heated_only_zones.append(zone)
    system_zones = heated_and_cooled_zones + cooled_only_zones
    heat_dict.update(cool_dict)
    zones = list(heat_dict.values())

    # determine the DOAS type from the demand controlled ventilation
    dcv = getattr(hvac, 'demand_controlled_ventilation', False)
    doas_type = 'DOAS' if not dcv else 'DOAS with DCV'
    air_loop = None  # will be returned from HVAC creation

    # add the HVAC system equipment using the equipment type
    # system type naming convention:
    # [ventilation strategy] [cooling system and plant] [heating system and plant]
    equip = hvac.equipment_type
    if equip == 'ElectricBaseboard':
        model_add_hvac_system(os_model, 'Baseboards', 'Electricity',
                              None, None, heated_zones)

    elif equip == 'BoilerBaseboard':
        model_add_hvac_system(os_model, 'Baseboards', 'NaturalGas',
                              None, None, heated_zones)

    elif equip == 'ASHPBaseboard':
        model_add_hvac_system(os_model, 'Baseboards', 'AirSourceHeatPump',
                              None, None, heated_zones)

    elif equip == 'DHWBaseboard':
        model_add_hvac_system(os_model, 'Baseboards', 'DistrictHeating',
                              None, None, heated_zones)

    elif equip == 'EvapCoolers_ElectricBaseboard':
        model_add_hvac_system(os_model, 'Baseboards', 'Electricity',
                              None, None, heated_zones)
        model_add_hvac_system(os_model, 'Evaporative Cooler',
                              None, None, 'Electricity', cooled_zones)

    elif equip == 'EvapCoolers_BoilerBaseboard':
        model_add_hvac_system(os_model, 'Baseboards', 'NaturalGas',
                              None, None, heated_zones)
        model_add_hvac_system(os_model, 'Evaporative Cooler', None, None,
                              'Electricity', cooled_zones)

    elif equip == 'EvapCoolers_ASHPBaseboard':
        model_add_hvac_system(os_model, 'Baseboards', 'AirSourceHeatPump',
                              None, None, heated_zones)
        model_add_hvac_system(os_model, 'Evaporative Cooler', None, None,
                              'Electricity', cooled_zones)

    elif equip == 'EvapCoolers_DHWBaseboard':
        model_add_hvac_system(os_model, 'Baseboards', 'DistrictHeating',
                              None, None, heated_zones)
        model_add_hvac_system(os_model, 'Evaporative Cooler', None, None,
                              'Electricity', cooled_zones)

    elif equip == 'EvapCoolers_Furnace':
        # use unit heater to represent forced air furnace to limit to one air loop per zone
        model_add_hvac_system(os_model, 'Unit Heaters', 'NaturalGas',
                              None, None, heated_zones)
        model_add_hvac_system(os_model, 'Evaporative Cooler', None, None,
                              'Electricity', cooled_zones)

    elif equip == 'EvapCoolers_UnitHeaters':
        model_add_hvac_system(os_model, 'Unit Heaters', 'NaturalGas',
                              None, None, heated_zones)
        model_add_hvac_system(os_model, 'Evaporative Cooler', None, None,
                              'Electricity', cooled_zones)

    elif equip == 'EvapCoolers':
        model_add_hvac_system(os_model, 'Evaporative Cooler', None, None,
                              'Electricity', cooled_zones)

    elif equip == 'DOAS_FCU_Chiller_Boiler':
        air_loop = model_add_hvac_system(os_model, doas_type, 'NaturalGas', None,
                                         'Electricity', zones)
        model_add_hvac_system(os_model, 'Fan Coil', 'NaturalGas', None, 'Electricity',
                              zones, zone_equipment_ventilation=False)

    elif equip == 'DOAS_FCU_Chiller_ASHP':
        air_loop = model_add_hvac_system(os_model, doas_type, 'AirSourceHeatPump',
                                         None, 'Electricity', zones)
        model_add_hvac_system(os_model, 'Fan Coil', 'AirSourceHeatPump', None,
                              'Electricity', zones, zone_equipment_ventilation=False)

    elif equip == 'DOAS_FCU_Chiller_DHW':
        air_loop = model_add_hvac_system(os_model, doas_type, 'DistrictHeating',
                                         None, 'Electricity', zones)
        model_add_hvac_system(os_model, 'Fan Coil', 'DistrictHeating', None,
                              'Electricity', zones, zone_equipment_ventilation=False)

    elif equip == 'DOAS_FCU_Chiller_ElectricBaseboard':
        air_loop = model_add_hvac_system(os_model, doas_type, None, None,
                                         'Electricity', zones)
        model_add_hvac_system(os_model, 'Fan Coil', None, None, 'Electricity', zones,
                              zone_equipment_ventilation=False)
        model_add_hvac_system(os_model, 'Baseboards', 'Electricity', None,
                              None, heated_zones)

    elif equip == 'DOAS_FCU_Chiller_GasHeaters':
        air_loop = model_add_hvac_system(os_model, doas_type, None, None,
                                         'Electricity', zones)
        model_add_hvac_system(os_model, 'Fan Coil', None, None, 'Electricity', zones,
                              zone_equipment_ventilation=False)
        model_add_hvac_system(os_model, 'Unit Heaters', 'NaturalGas', None,
                              None, heated_zones)

    elif equip == 'DOAS_FCU_Chiller':
        air_loop = model_add_hvac_system(os_model, doas_type, None, None,
                                         'Electricity', zones)
        model_add_hvac_system(os_model, 'Fan Coil', None, None, 'Electricity', zones,
                              zone_equipment_ventilation=False)

    elif equip == 'DOAS_FCU_ACChiller_Boiler':
        air_loop = model_add_hvac_system(os_model, doas_type, 'NaturalGas', None,
                                         'Electricity', zones,
                                         chilled_water_loop_cooling_type='AirCooled')
        model_add_hvac_system(os_model, 'Fan Coil', 'NaturalGas', None, 'Electricity',
                              zones, chilled_water_loop_cooling_type='AirCooled',
                              zone_equipment_ventilation=False)

    elif equip == 'DOAS_FCU_ACChiller_ASHP':
        air_loop = model_add_hvac_system(os_model, doas_type, 'AirSourceHeatPump', None,
                                         'Electricity', zones,
                                         chilled_water_loop_cooling_type='AirCooled')
        model_add_hvac_system(os_model, 'Fan Coil', 'AirSourceHeatPump', None,
                              'Electricity', zones,
                              chilled_water_loop_cooling_type='AirCooled',
                              zone_equipment_ventilation=False)

    elif equip == 'DOAS_FCU_ACChiller_DHW':
        air_loop = model_add_hvac_system(os_model, doas_type, 'DistrictHeating', None,
                                         'Electricity', zones,
                                         chilled_water_loop_cooling_type='AirCooled')
        model_add_hvac_system(os_model, 'Fan Coil', 'DistrictHeating', None,
                              'Electricity', zones,
                              chilled_water_loop_cooling_type='AirCooled',
                              zone_equipment_ventilation=False)

    elif equip == 'DOAS_FCU_ACChiller_ElectricBaseboard':
        air_loop = model_add_hvac_system(os_model, doas_type, None, None,
                                         'Electricity', zones,
                                         chilled_water_loop_cooling_type='AirCooled')
        model_add_hvac_system(os_model, 'Fan Coil', None, None, 'Electricity', zones,
                              chilled_water_loop_cooling_type='AirCooled',
                              zone_equipment_ventilation=False)
        model_add_hvac_system(os_model, 'Baseboards', 'Electricity',
                              None, None, heated_zones)

    elif equip == 'DOAS_FCU_ACChiller_GasHeaters':
        air_loop = model_add_hvac_system(os_model, doas_type, None, None,
                                         'Electricity', zones,
                                         chilled_water_loop_cooling_type='AirCooled')
        model_add_hvac_system(os_model, 'Fan Coil', None, None, 'Electricity', zones,
                              chilled_water_loop_cooling_type='AirCooled',
                              zone_equipment_ventilation=False)
        model_add_hvac_system(os_model, 'Unit Heaters', 'NaturalGas', None,
                              None, heated_zones)

    elif equip == 'DOAS_FCU_ACChiller':
        air_loop = model_add_hvac_system(os_model, doas_type, None, None,
                                         'Electricity', zones,
                                         chilled_water_loop_cooling_type='AirCooled')
        model_add_hvac_system(os_model, 'Fan Coil', None, None, 'Electricity', zones,
                              chilled_water_loop_cooling_type='AirCooled',
                              zone_equipment_ventilation=False)

    elif equip == 'DOAS_FCU_DCW_Boiler':
        air_loop = model_add_hvac_system(os_model, doas_type, 'NaturalGas', None,
                                         'DistrictCooling', zones)
        model_add_hvac_system(os_model, 'Fan Coil', 'NaturalGas', None,
                              'DistrictCooling', zones,
                              zone_equipment_ventilation=False)

    elif equip == 'DOAS_FCU_DCW_ASHP':
        air_loop = model_add_hvac_system(os_model, doas_type, 'AirSourceHeatPump',
                                         None, 'DistrictCooling', zones)
        model_add_hvac_system(os_model, 'Fan Coil', 'AirSourceHeatPump',
                              None, 'DistrictCooling', zones,
                              zone_equipment_ventilation=False)

    elif equip == 'DOAS_FCU_DCW_DHW':
        air_loop = model_add_hvac_system(os_model, doas_type, 'DistrictHeating',
                                         None, 'DistrictCooling', zones)
        model_add_hvac_system(os_model, 'Fan Coil', 'DistrictHeating',
                              None, 'DistrictCooling', zones,
                              zone_equipment_ventilation=False)

    elif equip == 'DOAS_FCU_DCW_ElectricBaseboard':
        air_loop = model_add_hvac_system(os_model, doas_type, None, None,
                                         'DistrictCooling', zones)
        model_add_hvac_system(os_model, 'Fan Coil', None, None, 'DistrictCooling',
                              zones, zone_equipment_ventilation=False)
        model_add_hvac_system(os_model, 'Baseboards', 'Electricity',
                              None, None, heated_zones)

    elif equip == 'DOAS_FCU_DCW_GasHeaters':
        air_loop = model_add_hvac_system(os_model, doas_type, None, None,
                                         'DistrictCooling', zones)
        model_add_hvac_system(os_model, 'Fan Coil', None, None, 'DistrictCooling',
                              zones, zone_equipment_ventilation=False)
        model_add_hvac_system(os_model, 'Unit Heaters', 'NaturalGas',
                              None, None, heated_zones)

    elif equip == 'DOAS_FCU_DCW':
        air_loop = model_add_hvac_system(os_model, doas_type, None, None,
                                         'DistrictCooling', zones)
        model_add_hvac_system(os_model, 'Fan Coil', None, None, 'DistrictCooling', zones,
                              zone_equipment_ventilation=False)

    elif equip == 'DOAS_VRF':
        air_loop = model_add_hvac_system(os_model, doas_type, 'Electricity',
                                         None, 'Electricity', zones,
                                         air_loop_heating_type='DX',
                                         air_loop_cooling_type='DX')
        model_add_hvac_system(os_model, 'VRF', 'Electricity',
                              None, 'Electricity', zones)

    elif equip == 'DOAS_WSHP_FluidCooler_Boiler':
        air_loop = model_add_hvac_system(os_model, doas_type, 'NaturalGas', None,
                                         'Electricity', zones)
        model_add_hvac_system(os_model, 'Water Source Heat Pumps', 'NaturalGas',
                              None, 'Electricity', zones,
                              heat_pump_loop_cooling_type='FluidCooler',
                              zone_equipment_ventilation=False)

    elif equip == 'DOAS_WSHP_CoolingTower_Boiler':
        air_loop = model_add_hvac_system(os_model, doas_type, 'NaturalGas', None,
                                         'Electricity', zones)
        model_add_hvac_system(os_model, 'Water Source Heat Pumps', 'NaturalGas',
                              None, 'Electricity', zones,
                              heat_pump_loop_cooling_type='CoolingTower',
                              zone_equipment_ventilation=False)

    elif equip == 'DOAS_WSHP_GSHP':
        air_loop = model_add_hvac_system(os_model, doas_type, 'Electricity', None,
                                         'Electricity', zones, air_loop_heating_type='DX',
                                         air_loop_cooling_type='DX')
        model_add_hvac_system(os_model, 'Ground Source Heat Pumps', 'Electricity', None,
                              'Electricity', zones, zone_equipment_ventilation=False)

    elif equip == 'DOAS_WSHP_DCW_DHW':
        air_loop = model_add_hvac_system(os_model, doas_type, 'DistrictHeating', None,
                                         'DistrictCooling', zones)
        model_add_hvac_system(os_model, 'Water Source Heat Pumps', 'DistrictHeating',
                              None, 'DistrictCooling', zones,
                              zone_equipment_ventilation=False)

    # ventilation provided by zone fan coil unit in fan coil systems
    elif equip == 'FCU_Chiller_Boiler':
        model_add_hvac_system(os_model, 'Fan Coil', 'NaturalGas', None,
                              'Electricity', zones)

    elif equip == 'FCU_Chiller_ASHP':
        model_add_hvac_system(os_model, 'Fan Coil', 'AirSourceHeatPump',
                              None, 'Electricity', zones)

    elif equip == 'FCU_Chiller_DHW':
        model_add_hvac_system(os_model, 'Fan Coil', 'DistrictHeating',
                              None, 'Electricity', zones)

    elif equip == 'FCU_Chiller_ElectricBaseboard':
        model_add_hvac_system(os_model, 'Fan Coil', None, None, 'Electricity', zones)
        model_add_hvac_system(os_model, 'Baseboards', 'Electricity',
                              None, None, heated_zones)

    elif equip == 'FCU_Chiller_GasHeaters':
        model_add_hvac_system(os_model, 'Fan Coil', None, None, 'Electricity', zones)
        model_add_hvac_system(os_model, 'Unit Heaters', 'NaturalGas',
                              None, None, heated_zones)

    elif equip == 'FCU_Chiller':
        model_add_hvac_system(os_model, 'Fan Coil', None, None, 'Electricity', zones)

    elif equip == 'FCU_ACChiller_Boiler':
        model_add_hvac_system(os_model, 'Fan Coil', 'NaturalGas', None, 'Electricity',
                              zones, chilled_water_loop_cooling_type='AirCooled')

    elif equip == 'FCU_ACChiller_ASHP':
        model_add_hvac_system(os_model, 'Fan Coil', 'AirSourceHeatPump',
                              None, 'Electricity', zones,
                              chilled_water_loop_cooling_type='AirCooled')

    elif equip == 'FCU_ACChiller_DHW':
        model_add_hvac_system(os_model, 'Fan Coil', 'DistrictHeating', None,
                              'Electricity', zones,
                              chilled_water_loop_cooling_type='AirCooled')

    elif equip == 'FCU_ACChiller_ElectricBaseboard':
        model_add_hvac_system(os_model, 'Fan Coil', None, None, 'Electricity', zones,
                              chilled_water_loop_cooling_type='AirCooled')
        model_add_hvac_system(os_model, 'Baseboards', 'Electricity',
                              None, None, heated_zones)

    elif equip == 'FCU_ACChiller_GasHeaters':
        model_add_hvac_system(os_model, 'Fan Coil', None, None, 'Electricity', zones,
                              chilled_water_loop_cooling_type='AirCooled')
        model_add_hvac_system(os_model, 'Unit Heaters', 'NaturalGas',
                              None, None, heated_zones)

    elif equip == 'FCU_ACChiller':
        model_add_hvac_system(os_model, 'Fan Coil', None, None, 'Electricity', zones,
                              chilled_water_loop_cooling_type='AirCooled')

    elif equip == 'FCU_DCW_Boiler':
        model_add_hvac_system(os_model, 'Fan Coil ', 'NaturalGas', None,
                              'DistrictCooling', zones)

    elif equip == 'FCU_DCW_ASHP':
        model_add_hvac_system(os_model, 'Fan Coil', 'AirSourceHeatPump',
                              None, 'DistrictCooling', zones)

    elif equip == 'FCU_DCW_DHW':
        model_add_hvac_system(os_model, 'Fan Coil', 'DistrictHeating',
                              None, 'DistrictCooling', zones)

    elif equip == 'FCU_DCW_ElectricBaseboard':
        model_add_hvac_system(os_model, 'Fan Coil', None, None, 'DistrictCooling', zones)
        model_add_hvac_system(os_model, 'Baseboards', 'Electricity',
                              None, None, heated_zones)

    elif equip == 'FCU_DCW_GasHeaters':
        model_add_hvac_system(os_model, 'Fan Coil', None, None, 'DistrictCooling', zones)
        model_add_hvac_system(os_model, 'Unit Heaters', 'NaturalGas',
                              None, None, heated_zones)

    elif equip == 'FCU_DCW':
        model_add_hvac_system(os_model, 'Fan Coil', None, None, 'DistrictCooling', zones)

    elif equip == 'Furnace':
        # includes ventilation, whereas residential forced air furnace does not.
        model_add_hvac_system(os_model, 'Forced Air Furnace', 'NaturalGas',
                              None, None, heated_zones)

    elif equip == 'Furnace_Electric':
        # includes ventilation, whereas residential forced air furnace does not.
        model_add_hvac_system(os_model, 'Forced Air Furnace', 'Electricity',
                              None, None, heated_zones)

    elif equip == 'GasHeaters':
        model_add_hvac_system(os_model, 'Unit Heaters', 'NaturalGas',
                              None, None, heated_zones)

    elif equip == 'PTAC_ElectricBaseboard':
        model_add_hvac_system(os_model, 'PTAC', None, None, 'Electricity', system_zones)
        model_add_hvac_system(os_model, 'Baseboards', 'Electricity',
                              None, None, heated_zones)

    elif equip == 'PTAC_BoilerBaseboard':
        model_add_hvac_system(os_model, 'PTAC', None, None, 'Electricity', system_zones)
        model_add_hvac_system(os_model, 'Baseboards', 'NaturalGas',
                              None, None, heated_zones)

    elif equip == 'PTAC_DHWBaseboard':
        model_add_hvac_system(os_model, 'PTAC', None, None, 'Electricity', system_zones)
        model_add_hvac_system(os_model, 'Baseboards', 'DistrictHeating',
                              None, None, heated_zones)

    elif equip == 'PTAC_GasHeaters':
        model_add_hvac_system(os_model, 'PTAC', None, None, 'Electricity', system_zones)
        model_add_hvac_system(os_model, 'Unit Heaters', 'NaturalGas',
                              None, None, heated_zones)

    elif equip == 'PTAC_ElectricCoil':
        model_add_hvac_system(os_model, 'PTAC', None, 'Electricity',
                              'Electricity', system_zones)
        # use 'Baseboard electric' for heated only zones
        model_add_hvac_system(os_model, 'Baseboards', 'Electricity',
                              None, None, heated_only_zones)

    elif equip == 'PTAC_GasCoil':
        model_add_hvac_system(os_model, 'PTAC', None, 'NaturalGas',
                              'Electricity', system_zones)
        # use 'Baseboard electric' for heated only zones
        model_add_hvac_system(os_model, 'Baseboards', 'Electricity',
                              None, None, heated_only_zones)

    elif equip == 'PTAC_Boiler':
        model_add_hvac_system(os_model, 'PTAC', 'NaturalGas', None,
                              'Electricity', system_zones)
        # use 'Baseboard gas boiler' for heated only zones
        model_add_hvac_system(os_model, 'Baseboards', 'NaturalGas',
                              None, None, heated_only_zones)

    elif equip == 'PTAC_ASHP':
        model_add_hvac_system(os_model, 'PTAC', 'AirSourceHeatPump',
                              None, 'Electricity', system_zones)
        # use 'Baseboard central air source heat pump' for heated only zones
        model_add_hvac_system(os_model, 'Baseboards', 'AirSourceHeatPump',
                              None, None, heated_only_zones)

    elif equip == 'PTAC_DHW':
        model_add_hvac_system(os_model, 'PTAC', 'DistrictHeating', None,
                              'Electricity', system_zones)
        # use 'Baseboard district hot water heat' for heated only zones
        model_add_hvac_system(os_model, 'Baseboards', 'DistrictHeating',
                              None, None, heated_only_zones)

    elif equip == 'PTAC':
        model_add_hvac_system(os_model, 'PTAC', None, None, 'Electricity', system_zones)

    elif equip == 'PTHP':
        model_add_hvac_system(os_model, 'PTHP', 'Electricity', None,
                              'Electricity', system_zones)
        # use 'Baseboard electric' for heated only zones
        model_add_hvac_system(os_model, 'Baseboards', 'Electricity',
                              None, None, heated_only_zones)

    elif equip == 'PSZAC_ElectricBaseboard':
        air_loop = model_add_hvac_system(os_model, 'PSZ-AC', None, None,
                                         'Electricity', system_zones)
        model_add_hvac_system(os_model, 'Baseboards', 'Electricity',
                              None, None, heated_zones)

    elif equip == 'PSZAC_BoilerBaseboard':
        air_loop = model_add_hvac_system(os_model, 'PSZ-AC', None, None, 'Electricity',
                                         system_zones)
        model_add_hvac_system(os_model, 'Baseboards', 'NaturalGas',
                              None, None, heated_zones)

    elif equip == 'PSZAC_DHWBaseboard':
        air_loop = model_add_hvac_system(os_model, 'PSZ-AC', None, None, 'Electricity',
                                         system_zones)
        model_add_hvac_system(os_model, 'Baseboards', 'DistrictHeating',
                              None, None, heated_zones)

    elif equip == 'PSZAC_GasHeaters':
        air_loop = model_add_hvac_system(os_model, 'PSZ-AC', None, None, 'Electricity',
                                         system_zones)
        model_add_hvac_system(os_model, 'Unit Heaters', 'NaturalGas',
                              None, None, heated_zones)

    elif equip == 'PSZAC_ElectricCoil':
        air_loop = model_add_hvac_system(os_model, 'PSZ-AC', None, 'Electricity',
                                         'Electricity', system_zones)
        # use 'Baseboard electric' for heated only zones
        model_add_hvac_system(os_model, 'Baseboards', 'Electricity',
                              None, None, heated_only_zones)

    elif equip == 'PSZAC_GasCoil':
        air_loop = model_add_hvac_system(os_model, 'PSZ-AC', None, 'NaturalGas',
                                         'Electricity', system_zones)
        # use 'Baseboard electric' for heated only zones
        model_add_hvac_system(os_model, 'Baseboards', 'Electricity',
                              None, None, heated_only_zones)

    elif equip == 'PSZAC_Boiler':
        air_loop = model_add_hvac_system(os_model, 'PSZ-AC', 'NaturalGas', None,
                                         'Electricity', system_zones)
        # use 'Baseboard gas boiler' for heated only zones
        model_add_hvac_system(os_model, 'Baseboards', 'NaturalGas',
                              None, None, heated_only_zones)

    elif equip == 'PSZAC_ASHP':
        air_loop = model_add_hvac_system(os_model, 'PSZ-AC', 'AirSourceHeatPump',
                                         None, 'Electricity', system_zones)
        # use 'Baseboard central air source heat pump' for heated only zones
        model_add_hvac_system(os_model, 'Baseboards', 'AirSourceHeatPump',
                              None, None, heated_only_zones)

    elif equip == 'PSZAC_DHW':
        air_loop = model_add_hvac_system(os_model, 'PSZ-AC', 'DistrictHeating',
                                         None, 'Electricity', system_zones)
        # use 'Baseboard district hot water' for heated only zones
        model_add_hvac_system(os_model, 'Baseboards', 'DistrictHeating',
                              None, None, heated_only_zones)

    elif equip == 'PSZAC':
        air_loop = model_add_hvac_system(os_model, 'PSZ-AC', None, None,
                                         'Electricity', cooled_zones)

    elif equip == 'PSZAC_DCW_ElectricBaseboard':
        air_loop = model_add_hvac_system(os_model, 'PSZ-AC', None, None,
                                         'DistrictCooling', system_zones)
        model_add_hvac_system(os_model, 'Baseboards', 'Electricity',
                              None, None, heated_zones)

    elif equip == 'PSZAC_DCW_BoilerBaseboard':
        air_loop = model_add_hvac_system(os_model, 'PSZ-AC', None, None,
                                         'DistrictCooling', system_zones)
        model_add_hvac_system(os_model, 'Baseboards', 'NaturalGas',
                              None, None, heated_zones)

    elif equip == 'PSZAC_DCW_GasHeaters':
        air_loop = model_add_hvac_system(os_model, 'PSZ-AC', None, None,
                                         'DistrictCooling', system_zones)
        model_add_hvac_system(os_model, 'Unit Heaters', 'NaturalGas',
                              None, None, heated_zones)

    elif equip == 'PSZAC_DCW_ElectricCoil':
        air_loop = model_add_hvac_system(os_model, 'PSZ-AC', None, 'Electricity',
                                         'DistrictCooling', system_zones)
        # use 'Baseboard electric' for heated only zones
        model_add_hvac_system(os_model, 'Baseboards', 'Electricity',
                              None, None, heated_only_zones)

    elif equip == 'PSZAC_DCW_GasCoil':
        air_loop = model_add_hvac_system(os_model, 'PSZ-AC', None, 'NaturalGas',
                                         'DistrictCooling', system_zones)
        # use 'Baseboard electric' for heated only zones
        model_add_hvac_system(os_model, 'Baseboards', 'Electricity',
                              None, None, heated_only_zones)

    elif equip == 'PSZAC_DCW_Boiler':
        air_loop = model_add_hvac_system(os_model, 'PSZ-AC', 'NaturalGas', None,
                                         'DistrictCooling', system_zones)
        # use 'Baseboard gas boiler' for heated only zones
        model_add_hvac_system(os_model, 'Baseboards', 'NaturalGas',
                              None, None, heated_only_zones)

    elif equip == 'PSZAC_DCW_ASHP':
        air_loop = model_add_hvac_system(os_model, 'PSZ-AC', 'AirSourceHeatPump',
                                         None, 'DistrictCooling', system_zones)
        # use 'Baseboard central air source heat pump' for heated only zones
        model_add_hvac_system(os_model, 'Baseboards', 'AirSourceHeatPump',
                              None, None, heated_only_zones)

    elif equip == 'PSZAC_DCW_DHW':
        air_loop = model_add_hvac_system(os_model, 'PSZ-AC', 'DistrictHeating',
                                         None, 'DistrictCooling', system_zones)
        # use 'Baseboard district hot water' for heated only zones
        model_add_hvac_system(os_model, 'Baseboards', 'DistrictHeating',
                              None, None, heated_only_zones)

    elif equip == 'PSZAC_DCW':
        air_loop = model_add_hvac_system(os_model, 'PSZ-AC', None, None,
                                         'DistrictCooling', cooled_zones)

    elif equip == 'PSZHP':
        air_loop = model_add_hvac_system(os_model, 'PSZ-HP', 'Electricity', None,
                                         'Electricity', system_zones)
        # use 'Baseboard electric' for heated only zones
        model_add_hvac_system(os_model, 'Baseboards', 'Electricity',
                              None, None, heated_only_zones)

    # PVAV systems by default use a DX coil for cooling
    elif equip == 'PVAV_Boiler':
        air_loop = model_add_hvac_system(os_model, 'PVAV Reheat', 'NaturalGas',
                                         'NaturalGas', 'Electricity', zones)

    elif equip == 'PVAV_ASHP':
        air_loop = model_add_hvac_system(os_model, 'PVAV Reheat', 'AirSourceHeatPump',
                                         'AirSourceHeatPump', 'Electricity', zones)

    elif equip == 'PVAV_DHW':
        air_loop = model_add_hvac_system(os_model, 'PVAV Reheat', 'DistrictHeating',
                                         'DistrictHeating', 'Electricity', zones)

    elif equip == 'PVAV_PFP':
        air_loop = model_add_hvac_system(os_model, 'PVAV PFP Boxes', 'Electricity',
                                         'Electricity', 'Electricity', zones)

    elif equip == 'PVAV_BoilerElectricReheat':
        air_loop = model_add_hvac_system(os_model, 'PVAV Reheat', 'Gas', 'Electricity',
                                         'Electricity', zones)

    # all residential systems do not have ventilation
    elif equip == 'ResidentialAC_ElectricBaseboard':
        model_add_hvac_system(os_model, 'Residential AC', None, None, None, cooled_zones)
        model_add_hvac_system(os_model, 'Baseboards', 'Electricity',
                              None, None, heated_zones)

    elif equip == 'ResidentialAC_BoilerBaseboard':
        model_add_hvac_system(os_model, 'Residential AC', None, None, None, cooled_zones)
        model_add_hvac_system(os_model, 'Baseboards', 'NaturalGas',
                              None, None, heated_zones)

    elif equip == 'ResidentialAC_ASHPBaseboard':
        model_add_hvac_system(os_model, 'Residential AC', None, None, None, cooled_zones)
        model_add_hvac_system(os_model, 'Baseboards', 'AirSourceHeatPump',
                              None, None, heated_zones)

    elif equip == 'ResidentialAC_DHWBaseboard':
        model_add_hvac_system(os_model, 'Residential AC', None, None, None, cooled_zones)
        model_add_hvac_system(os_model, 'Baseboards', 'DistrictHeating',
                              None, None, heated_zones)

    elif equip == 'ResidentialAC_ResidentialFurnace':
        model_add_hvac_system(os_model, 'Residential Forced Air Furnace with AC',
                              None, None, None, zones)

    elif equip == 'ResidentialAC':
        model_add_hvac_system(os_model, 'Residential AC', None, None, None, cooled_zones)

    elif equip == 'ResidentialHP':
        model_add_hvac_system(os_model, 'Residential Air Source Heat Pump',
                              'Electricity', None, 'Electricity', zones)

    elif equip == 'ResidentialHPNoCool':
        model_add_hvac_system(os_model, 'Residential Air Source Heat Pump',
                              'Electricity', None, None, heated_zones)

    elif equip == 'ResidentialFurnace':
        model_add_hvac_system(os_model, 'Residential Forced Air Furnace',
                              'NaturalGas', None, None, zones)

    elif equip == 'VAV_Chiller_Boiler':
        air_loop = model_add_hvac_system(os_model, 'VAV Reheat', 'NaturalGas',
                                         'NaturalGas', 'Electricity', zones)

    elif equip == 'VAV_Chiller_ASHP':
        air_loop = model_add_hvac_system(os_model, 'VAV Reheat', 'AirSourceHeatPump',
                                         'AirSourceHeatPump', 'Electricity', zones)

    elif equip == 'VAV_Chiller_DHW':
        air_loop = model_add_hvac_system(os_model, 'VAV Reheat', 'DistrictHeating',
                                         'DistrictHeating', 'Electricity', zones)

    elif equip == 'VAV_Chiller_PFP':
        air_loop = model_add_hvac_system(os_model, 'VAV PFP Boxes', 'NaturalGas',
                                         'NaturalGas', 'Electricity', zones)

    elif equip == 'VAV_Chiller_GasCoil':
        air_loop = model_add_hvac_system(os_model, 'VAV Gas Reheat', 'NaturalGas',
                                         'NaturalGas', 'Electricity', zones)

    elif equip == 'VAV_ACChiller_Boiler':
        air_loop = model_add_hvac_system(os_model, 'VAV Reheat', 'NaturalGas',
                                         'NaturalGas', 'Electricity', zones,
                                         chilled_water_loop_cooling_type='AirCooled')

    elif equip == 'VAV_ACChiller_ASHP':
        air_loop = model_add_hvac_system(os_model, 'VAV Reheat', 'AirSourceHeatPump',
                                         'AirSourceHeatPump', 'Electricity', zones,
                                         chilled_water_loop_cooling_type='AirCooled')

    elif equip == 'VAV_ACChiller_DHW':
        air_loop = model_add_hvac_system(os_model, 'VAV Reheat', 'DistrictHeating',
                                         'DistrictHeating', 'Electricity', zones,
                                         chilled_water_loop_cooling_type='AirCooled')

    elif equip == 'VAV_ACChiller_PFP':
        air_loop = model_add_hvac_system(os_model, 'VAV PFP Boxes', 'NaturalGas',
                                         'NaturalGas', 'Electricity', zones,
                                         chilled_water_loop_cooling_type='AirCooled')

    elif equip == 'VAV_ACChiller_GasCoil':
        air_loop = model_add_hvac_system(os_model, 'VAV Gas Reheat', 'NaturalGas',
                                         'NaturalGas', 'Electricity', zones,
                                         chilled_water_loop_cooling_type='AirCooled')

    elif equip == 'VAV_DCW_Boiler':
        air_loop = model_add_hvac_system(os_model, 'VAV Reheat', 'NaturalGas',
                                         'NaturalGas', 'DistrictCooling', zones)

    elif equip == 'VAV_DCW_ASHP':
        air_loop = model_add_hvac_system(os_model, 'VAV Reheat', 'AirSourceHeatPump',
                                         'AirSourceHeatPump', 'DistrictCooling', zones)

    elif equip == 'VAV_DCW_DHW':
        air_loop = model_add_hvac_system(os_model, 'VAV Reheat', 'DistrictHeating',
                                         'DistrictHeating', 'DistrictCooling', zones)

    elif equip == 'VAV_DCW_PFP':
        air_loop = model_add_hvac_system(os_model, 'VAV PFP Boxes', 'NaturalGas',
                                         'NaturalGas', 'DistrictCooling', zones)

    elif equip == 'VAV_DCW_GasCoil':
        air_loop = model_add_hvac_system(os_model, 'VAV Gas Reheat', 'NaturalGas',
                                         'NaturalGas', 'DistrictCooling', zones)

    elif equip == 'VRF':
        model_add_hvac_system(os_model, 'VRF', 'Electricity', None, 'Electricity', zones)

    elif equip == 'WSHP_FluidCooler_Boiler':
        model_add_hvac_system(os_model, 'Water Source Heat Pumps',
                              'NaturalGas', None, 'Electricity', zones,
                              heat_pump_loop_cooling_type='FluidCooler')

    elif equip == 'WSHP_CoolingTower_Boiler':
        model_add_hvac_system(os_model, 'Water Source Heat Pumps',
                              'NaturalGas', None, 'Electricity', zones,
                              heat_pump_loop_cooling_type='CoolingTower')

    elif equip == 'WSHP_GSHP':
        model_add_hvac_system(os_model, 'Ground Source Heat Pumps',
                              'Electricity', None, 'Electricity', zones)

    elif equip == 'WSHP_DCW_DHW':
        model_add_hvac_system(os_model, 'Water Source Heat Pumps', 'DistrictHeating',
                              None, 'DistrictCooling', zones)

    elif equip == 'WindowAC_ElectricBaseboard':
        model_add_hvac_system(os_model, 'Window AC', None, None,
                              'Electricity', cooled_zones)
        model_add_hvac_system(os_model, 'Baseboards', 'Electricity',
                              None, None, heated_zones)

    elif equip == 'WindowAC_BoilerBaseboard':
        model_add_hvac_system(os_model, 'Window AC', None, None,
                              'Electricity', cooled_zones)
        model_add_hvac_system(os_model, 'Baseboards', 'NaturalGas',
                              None, None, heated_zones)

    elif equip == 'WindowAC_ASHPBaseboard':
        model_add_hvac_system(os_model, 'Window AC', None, None,
                              'Electricity', cooled_zones)
        model_add_hvac_system(os_model, 'Baseboards', 'AirSourceHeatPump',
                              None, None, heated_zones)

    elif equip == 'WindowAC_DHWBaseboard':
        model_add_hvac_system(os_model, 'Window AC', None, None,
                              'Electricity', cooled_zones)
        model_add_hvac_system(os_model, 'Baseboards', 'DistrictHeating',
                              None, None, heated_zones)

    elif equip == 'WindowAC_Furnace':
        model_add_hvac_system(os_model, 'Window AC', None, None,
                              'Electricity', cooled_zones)
        model_add_hvac_system(os_model, 'Forced Air Furnace', 'NaturalGas',
                              None, None, heated_zones)

    elif equip == 'WindowAC_GasHeaters':
        model_add_hvac_system(os_model, 'Window AC', None, None,
                              'Electricity', cooled_zones)
        model_add_hvac_system(os_model, 'Unit Heaters', 'NaturalGas',
                              None, None, heated_zones)

    elif equip == 'WindowAC':
        model_add_hvac_system(os_model, 'Window AC', None, None,
                              'Electricity', cooled_zones)

    else:
        print('HVAC system type "{}" not recognized'.format(equip))

    # assign all of the properties associated with the air loop
    if air_loop is not None:
        # name the air loop with the name the user specified for the HVAC
        clean_hvac_name = clean_ep_string(hvac.display_name)
        if not isinstance(air_loop, list):
            air_loop.setName(clean_hvac_name)
            os_air_loops = [air_loop]
        else:
            os_air_loops = air_loop
            for i, loop in enumerate(os_air_loops):
                loop.setName('{} {}'.format(clean_hvac_name, i))

        # assign the properties that are specific to All-Air systems
        if isinstance(hvac, _AllAirBase):
            for os_air_loop in os_air_loops:
                # assign the economizer
                oasys = os_air_loop.airLoopHVACOutdoorAirSystem()
                if oasys.is_initialized():
                    os_oasys = oasys.get()
                    oactrl = os_oasys.getControllerOutdoorAir()
                    oactrl.setEconomizerControlType(hvac.economizer_type)
                    # assign demand controlled ventilation
                    if hvac.demand_controlled_ventilation:
                        vent_ctrl = oactrl.controllerMechanicalVentilation()
                        vent_ctrl.setDemandControlledVentilationNoFail(True)
                        oactrl.resetMinimumFractionofOutdoorAirSchedule()

        # assign the properties that are specific to DOAS systems
        if isinstance(hvac, _DOASBase):
            if hvac.doas_availability_schedule is not None:
                sch_id = hvac.doas_availability_schedule.identifier
                schedule = openstudio_model.getScheduleByName(sch_id)
                if schedule.is_initialized():
                    avail_sch = schedule.get()
                    for os_air_loop in os_air_loops:
                        os_air_loop.setAvailabilitySchedule(avail_sch)

        # set the sensible heat recovery if it is specified
        if hvac.sensible_heat_recovery != 0:
            for os_air_loop in os_air_loops:
                heat_ex = _get_or_add_heat_recovery(os_model, os_air_loop)
                # ratio of max to standard efficiency from OpenStudio Standards
                eff_standard = hvac.sensible_heat_recovery
                heat_ex.setSensibleEffectivenessat100CoolingAirFlow(eff_standard)
                heat_ex.setSensibleEffectivenessat100HeatingAirFlow(eff_standard)

        # set the latent heat recovery ity is specified
        if hvac.latent_heat_recovery != 0:
            for os_air_loop in os_air_loops:
                heat_ex = _get_or_add_heat_recovery(os_model, os_air_loop)
                # ratio of max to standard efficiency from OpenStudio Standards
                eff_standard = hvac.latent_heat_recovery
                heat_ex.setLatentEffectivenessat100CoolingAirFlow(eff_standard)
                heat_ex.setLatentEffectivenessat100HeatingAirFlow(eff_standard)

        # assign an electric humidifier if there's an air loop and the zones have a humidistat
        humidistat_exists = False
        for zone in zones:
            h_stat = zone.zoneControlHumidistat()
            if h_stat.is_initialized():
                humidistat_exists = True
                if isinstance(hvac, _DOASBase):
                    z_sizing = zone.sizingZone()
                    z_sizing.setDedicatedOutdoorAirSystemControlStrategy(
                        'NeutralDehumidifiedSupplyAir')
        if humidistat_exists:
            for os_air_loop in os_air_loops:
                _add_humidifier(os_model, os_air_loop)

        # set the outdoor air controller to respect room-level ventilation schedules if they exist
        oa_sch, oa_sch_name, = None, None
        for i, zone in enumerate(zones):
            oa_spec = zone.spaces()[0].designSpecificationOutdoorAir()
            if oa_spec.is_initialized():
                oa_spec = oa_spec.get()
                space_oa_sch = oa_spec.outdoorAirFlowRateFractionSchedule()
                if space_oa_sch.is_initialized():
                    space_oa_sch = space_oa_sch.get()
                    space_oa_sch_name = space_oa_sch.nameString()
                    if i == 0 or space_oa_sch_name == oa_sch_name:
                        oa_sch, oa_sch_name = space_oa_sch, space_oa_sch_name
                    else:  # different schedules across zones; just use constant max
                        oa_sch = None
        if oa_sch is not None:
            for os_air_loop in os_air_loops:
                oasys = os_air_loop.airLoopHVACOutdoorAirSystem()
                if oasys.is_initialized():
                    os_oasys = oasys.get()
                    oactrl = os_oasys.getControllerOutdoorAir()
                    oactrl.resetMinimumFractionofOutdoorAirSchedule()
                    oactrl.setMinimumOutdoorAirSchedule(oa_sch)


def _get_or_add_heat_recovery(os_model, os_air_loop):
    """Get an existing heat exchanger in an air loop or add one if it does not exist."""
    # get an existing heat energy recovery unit from an air loop
    for supply_comp in os_air_loop.oaComponents():
        if supply_comp.to_HeatExchangerAirToAirSensibleAndLatent().is_initialized():
            return supply_comp.to_HeatExchangerAirToAirSensibleAndLatent().get()

    # create a heat recovery unit with default zero efficiencies
    heat_ex = openstudio_model.HeatExchangerAirToAirSensibleAndLatent(os_model)
    heat_ex.setEconomizerLockout(False)
    heat_ex.setName('{}_Heat Recovery Unit'.format(os_air_loop.nameString()))
    heat_ex.setSensibleEffectivenessat100CoolingAirFlow(0.0)
    heat_ex.setSensibleEffectivenessat100HeatingAirFlow(0.0)
    heat_ex.setLatentEffectivenessat100CoolingAirFlow(0.0)
    heat_ex.setLatentEffectivenessat100HeatingAirFlow(0.0)

    # add the heat exchanger to the air loop
    outdoor_node = os_air_loop.reliefAirNode()
    if outdoor_node.is_initialized():
        os_outdoor_node = outdoor_node.get()
        heat_ex.addToNode(os_outdoor_node)
    return heat_ex


def _add_humidifier(os_model, os_air_loop):
    """Add a humidifier to an air loop so it can meet humidification setpoints."""
    # create an electric humidifier
    humidifier = openstudio_model.HumidifierSteamElectric(os_model)
    humidifier.setName('{}_Humidifier Unit'.format(os_air_loop.nameString()))
    humid_control = openstudio_model.SetpointManagerMultiZoneHumidityMinimum(os_model)
    humid_control.setName('{}_Humidifier Controller'.format(os_air_loop.nameString()))

    # add the humidifier to the air loop
    supply_node = os_air_loop.supplyOutletNode()
    humidifier.addToNode(supply_node)
    humid_control.addToNode(supply_node)
    return humidifier
