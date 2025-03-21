# coding=utf-8
"""OpenStudio translators for template HVAC systems."""
from __future__ import division

from .standards import hvac_systems as standard


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

    # add the HVAC system equipment using the equipment type
    # system type naming convention:
    # [ventilation strategy] [cooling system and plant] [heating system and plant]
    equip = hvac.equipment_type
    if equip == 'ElectricBaseboard':
        standard.model_add_hvac_system(os_model, 'Baseboards', 'Electricity',
                                       None, None, heated_zones)

    elif equip == 'BoilerBaseboard':
        standard.model_add_hvac_system(os_model, 'Baseboards', 'NaturalGas',
                                       None, None, heated_zones)

    elif equip == 'ASHPBaseboard':
        standard.model_add_hvac_system(os_model, 'Baseboards', 'AirSourceHeatPump',
                                       None, None, heated_zones)

    elif equip == 'DHWBaseboard':
        standard.model_add_hvac_system(os_model, 'Baseboards', 'DistrictHeating',
                                       None, None, heated_zones)

    elif equip == 'EvapCoolers_ElectricBaseboard':
        standard.model_add_hvac_system(os_model, 'Baseboards', 'Electricity',
                                       None, None, heated_zones)
        standard.model_add_hvac_system(os_model, 'Evaporative Cooler',
                                       None, None, 'Electricity', cooled_zones)

    elif equip == 'EvapCoolers_BoilerBaseboard':
        standard.model_add_hvac_system(os_model, 'Baseboards', 'NaturalGas',
                                       None, None, heated_zones)
        standard.model_add_hvac_system(os_model, 'Evaporative Cooler', None, None,
                                       'Electricity', cooled_zones)

    elif equip == 'EvapCoolers_ASHPBaseboard':
        standard.model_add_hvac_system(os_model, 'Baseboards', 'AirSourceHeatPump',
                                       None, None, heated_zones)
        standard.model_add_hvac_system(os_model, 'Evaporative Cooler', None, None,
                                       'Electricity', cooled_zones)

    elif equip == 'EvapCoolers_DHWBaseboard':
        standard.model_add_hvac_system(os_model, 'Baseboards', 'DistrictHeating',
                                       None, None, heated_zones)
        standard.model_add_hvac_system(os_model, 'Evaporative Cooler', None, None,
                                       'Electricity', cooled_zones)

    elif equip == 'EvapCoolers_Furnace':
        # use unit heater to represent forced air furnace to limit to one air loop per zone
        standard.model_add_hvac_system(os_model, 'Unit Heaters', 'NaturalGas',
                                       None, None, heated_zones)
        standard.model_add_hvac_system(os_model, 'Evaporative Cooler', None, None,
                                       'Electricity', cooled_zones)

    elif equip == 'EvapCoolers_UnitHeaters':
        standard.model_add_hvac_system(os_model, 'Unit Heaters', 'NaturalGas',
                                       None, None, heated_zones)
        standard.model_add_hvac_system(os_model, 'Evaporative Cooler', None, None,
                                       'Electricity', cooled_zones)

    elif equip == 'EvapCoolers':
        standard.model_add_hvac_system(os_model, 'Evaporative Cooler', None, None,
                                       'Electricity', cooled_zones)

    elif equip == 'DOAS_FCU_Chiller_Boiler':
        standard.model_add_hvac_system(os_model, doas_type, 'NaturalGas', None,
                                       'Electricity', zones)
        standard.model_add_hvac_system(os_model, 'Fan Coil', 'NaturalGas', None,
                                       'Electricity', zones,
                                       zone_equipment_ventilation=False)

    elif equip == 'DOAS_FCU_Chiller_ASHP':
        standard.model_add_hvac_system(os_model, doas_type, 'AirSourceHeatPump',
                                       None, 'Electricity', zones)
        standard.model_add_hvac_system(os_model, 'Fan Coil', 'AirSourceHeatPump',
                                       None, 'Electricity', zones,
                                       zone_equipment_ventilation=False)

    elif equip == 'DOAS_FCU_Chiller_DHW':
        standard.model_add_hvac_system(os_model, doas_type, 'DistrictHeating',
                                       None, 'Electricity', zones)
        standard.model_add_hvac_system(os_model, 'Fan Coil', 'DistrictHeating',
                                       None, 'Electricity', zones,
                                       zone_equipment_ventilation=False)

    elif equip == 'DOAS_FCU_Chiller_ElectricBaseboard':
        standard.model_add_hvac_system(os_model, doas_type, None, None,
                                       'Electricity', zones)
        standard.model_add_hvac_system(os_model, 'Fan Coil', None, None,
                                       'Electricity', zones,
                                       zone_equipment_ventilation=False)
        standard.model_add_hvac_system(os_model, 'Baseboards', 'Electricity',
                                       None, None, heated_zones)

    elif equip == 'DOAS_FCU_Chiller_GasHeaters':
        standard.model_add_hvac_system(os_model, doas_type, None, None,
                                       'Electricity', zones)
        standard.model_add_hvac_system(os_model, 'Fan Coil', None, None,
                                       'Electricity', zones,
                                       zone_equipment_ventilation=False)
        standard.model_add_hvac_system(os_model, 'Unit Heaters', 'NaturalGas',
                                       None, None, heated_zones)

    elif equip == 'DOAS_FCU_Chiller':
        standard.model_add_hvac_system(os_model, doas_type, None, None,
                                       'Electricity', zones)
        standard.model_add_hvac_system(os_model, 'Fan Coil', None, None,
                                       'Electricity', zones,
                                       zone_equipment_ventilation=False)

    elif equip == 'DOAS_FCU_ACChiller_Boiler':
        standard.model_add_hvac_system(os_model, doas_type, 'NaturalGas', None,
                                       'Electricity', zones,
                                       chilled_water_loop_cooling_type='AirCooled')
        standard.model_add_hvac_system(os_model, 'Fan Coil', 'NaturalGas', None,
                                       'Electricity', zones,
                                       chilled_water_loop_cooling_type='AirCooled',
                                       zone_equipment_ventilation=False)

    elif equip == 'DOAS_FCU_ACChiller_ASHP':
        standard.model_add_hvac_system(os_model, doas_type, 'AirSourceHeatPump', None,
                                       'Electricity', zones,
                                       chilled_water_loop_cooling_type='AirCooled')
        standard.model_add_hvac_system(os_model, 'Fan Coil', 'AirSourceHeatPump', None,
                                       'Electricity', zones,
                                       chilled_water_loop_cooling_type='AirCooled',
                                       zone_equipment_ventilation=False)

    elif equip == 'DOAS_FCU_ACChiller_DHW':
        standard.model_add_hvac_system(os_model, doas_type, 'DistrictHeating', None,
                                       'Electricity', zones,
                                       chilled_water_loop_cooling_type='AirCooled')
        standard.model_add_hvac_system(os_model, 'Fan Coil', 'DistrictHeating', None,
                                       'Electricity', zones,
                                       chilled_water_loop_cooling_type='AirCooled',
                                       zone_equipment_ventilation=False)

    elif equip == 'DOAS_FCU_ACChiller_ElectricBaseboard':
        standard.model_add_hvac_system(os_model, doas_type, None, None,
                                       'Electricity', zones,
                                       chilled_water_loop_cooling_type='AirCooled')
        standard.model_add_hvac_system(os_model, 'Fan Coil', None, None,
                                       'Electricity', zones,
                                       chilled_water_loop_cooling_type='AirCooled',
                                       zone_equipment_ventilation=False)
        standard.model_add_hvac_system(os_model, 'Baseboards', 'Electricity',
                                       None, None, heated_zones)

    elif equip == 'DOAS_FCU_ACChiller_GasHeaters':
        standard.model_add_hvac_system(os_model, doas_type, None, None,
                                       'Electricity', zones,
                                       chilled_water_loop_cooling_type='AirCooled')
        standard.model_add_hvac_system(os_model, 'Fan Coil', None, None,
                                       'Electricity', zones,
                                       chilled_water_loop_cooling_type='AirCooled',
                                       zone_equipment_ventilation=False)
        standard.model_add_hvac_system(os_model, 'Unit Heaters', 'NaturalGas',
                                       None, None, heated_zones)

    elif equip == 'DOAS_FCU_ACChiller':
        standard.model_add_hvac_system(os_model, doas_type, None, None,
                                       'Electricity', zones,
                                       chilled_water_loop_cooling_type='AirCooled')
        standard.model_add_hvac_system(os_model, 'Fan Coil', None, None,
                                       'Electricity', zones,
                                       chilled_water_loop_cooling_type='AirCooled',
                                       zone_equipment_ventilation=False)

    elif equip == 'DOAS_FCU_DCW_Boiler':
        standard.model_add_hvac_system(os_model, doas_type, 'NaturalGas', None,
                                       'DistrictCooling', zones)
        standard.model_add_hvac_system(os_model, 'Fan Coil', 'NaturalGas', None,
                                       'DistrictCooling', zones,
                                       zone_equipment_ventilation=False)

    elif equip == 'DOAS_FCU_DCW_ASHP':
        standard.model_add_hvac_system(os_model, doas_type, 'AirSourceHeatPump',
                                       None, 'DistrictCooling', zones)
        standard.model_add_hvac_system(os_model, 'Fan Coil', 'AirSourceHeatPump',
                                       None, 'DistrictCooling', zones,
                                       zone_equipment_ventilation=False)

    elif equip == 'DOAS_FCU_DCW_DHW':
        standard.model_add_hvac_system(os_model, doas_type, 'DistrictHeating',
                                       None, 'DistrictCooling', zones)
        standard.model_add_hvac_system(os_model, 'Fan Coil', 'DistrictHeating',
                                       None, 'DistrictCooling', zones,
                                       zone_equipment_ventilation=False)

    elif equip == 'DOAS_FCU_DCW_ElectricBaseboard':
        standard.model_add_hvac_system(os_model, doas_type, None, None,
                                       'DistrictCooling', zones)
        standard.model_add_hvac_system(os_model, 'Fan Coil', None, None,
                                       'DistrictCooling', zones,
                                       zone_equipment_ventilation=False)
        standard.model_add_hvac_system(os_model, 'Baseboards', 'Electricity',
                                       None, None, heated_zones)

    elif equip == 'DOAS_FCU_DCW_GasHeaters':
        standard.model_add_hvac_system(os_model, doas_type, None, None,
                                       'DistrictCooling', zones)
        standard.model_add_hvac_system(os_model, 'Fan Coil', None, None,
                                       'DistrictCooling', zones,
                                       zone_equipment_ventilation=False)
        standard.model_add_hvac_system(os_model, 'Unit Heaters', 'NaturalGas',
                                       None, None, heated_zones)

    elif equip == 'DOAS_FCU_DCW':
        standard.model_add_hvac_system(os_model, doas_type, None, None,
                                       'DistrictCooling', zones)
        standard.model_add_hvac_system(os_model, 'Fan Coil', None, None,
                                       'DistrictCooling', zones,
                                       zone_equipment_ventilation=False)

    elif equip == 'DOAS_VRF':
        standard.model_add_hvac_system(os_model, doas_type, 'Electricity',
                                       None, 'Electricity', zones,
                                       air_loop_heating_type='DX',
                                       air_loop_cooling_type='DX')
        standard.model_add_hvac_system(os_model, 'VRF', 'Electricity',
                                       None, 'Electricity', zones)

    elif equip == 'DOAS_WSHP_FluidCooler_Boiler':
        standard.model_add_hvac_system(os_model, doas_type, 'NaturalGas', None,
                                       'Electricity', zones)
        standard.model_add_hvac_system(os_model, 'Water Source Heat Pumps', 'NaturalGas',
                                       None, 'Electricity', zones,
                                       heat_pump_loop_cooling_type='FluidCooler',
                                       zone_equipment_ventilation=False)

    elif equip == 'DOAS_WSHP_CoolingTower_Boiler':
        standard.model_add_hvac_system(os_model, doas_type, 'NaturalGas', None,
                                       'Electricity', zones)
        standard.model_add_hvac_system(os_model, 'Water Source Heat Pumps', 'NaturalGas',
                                       None, 'Electricity', zones,
                                       heat_pump_loop_cooling_type='CoolingTower',
                                       zone_equipment_ventilation=False)

    elif equip == 'DOAS_WSHP_GSHP':
        standard.model_add_hvac_system(os_model, doas_type, 'Electricity', None,
                                       'Electricity', zones, air_loop_heating_type='DX',
                                       air_loop_cooling_type='DX')
        standard.model_add_hvac_system(os_model, 'Ground Source Heat Pumps',
                                       'Electricity', None, 'Electricity', zones,
                                       zone_equipment_ventilation=False)

    elif equip == 'DOAS_WSHP_DCW_DHW':
        standard.model_add_hvac_system(os_model, doas_type, 'DistrictHeating', None,
                                       'DistrictCooling', zones)
        standard.model_add_hvac_system(os_model, 'Water Source Heat Pumps',
                                       'DistrictHeating', None, 'DistrictCooling', zones,
                                       zone_equipment_ventilation=False)

    # ventilation provided by zone fan coil unit in fan coil systems
    elif equip == 'FCU_Chiller_Boiler':
        standard.model_add_hvac_system(os_model, 'Fan Coil', 'NaturalGas', None,
                                       'Electricity', zones)

    elif equip == 'FCU_Chiller_ASHP':
        standard.model_add_hvac_system(os_model, 'Fan Coil', 'AirSourceHeatPump',
                                       None, 'Electricity', zones)

    elif equip == 'FCU_Chiller_DHW':
        standard.model_add_hvac_system(os_model, 'Fan Coil', 'DistrictHeating',
                                       None, 'Electricity', zones)

    elif equip == 'FCU_Chiller_ElectricBaseboard':
        standard.model_add_hvac_system(os_model, 'Fan Coil', None, None,
                                       'Electricity', zones)
        standard.model_add_hvac_system(os_model, 'Baseboards', 'Electricity',
                                       None, None, heated_zones)

    elif equip == 'FCU_Chiller_GasHeaters':
        standard.model_add_hvac_system(os_model, 'Fan Coil', None, None,
                                       'Electricity', zones)
        standard.model_add_hvac_system(os_model, 'Unit Heaters', 'NaturalGas',
                                       None, None, heated_zones)

    elif equip == 'FCU_Chiller':
        standard.model_add_hvac_system(os_model, 'Fan Coil', None, None,
                                       'Electricity', zones)

    elif equip == 'FCU_ACChiller_Boiler':
        standard.model_add_hvac_system(os_model, 'Fan Coil', 'NaturalGas', None,
                                       'Electricity', zones,
                                       chilled_water_loop_cooling_type='AirCooled')

    elif equip == 'FCU_ACChiller_ASHP':
        standard.model_add_hvac_system(os_model, 'Fan Coil', 'AirSourceHeatPump',
                                       None, 'Electricity', zones,
                                       chilled_water_loop_cooling_type='AirCooled')

    elif equip == 'FCU_ACChiller_DHW':
        standard.model_add_hvac_system(os_model, 'Fan Coil', 'DistrictHeating', None,
                                       'Electricity', zones,
                                       chilled_water_loop_cooling_type='AirCooled')

    elif equip == 'FCU_ACChiller_ElectricBaseboard':
        standard.model_add_hvac_system(os_model, 'Fan Coil', None, None,
                                       'Electricity', zones,
                                       chilled_water_loop_cooling_type='AirCooled')
        standard.model_add_hvac_system(os_model, 'Baseboards', 'Electricity',
                                       None, None, heated_zones)

    elif equip == 'FCU_ACChiller_GasHeaters':
        standard.model_add_hvac_system(os_model, 'Fan Coil', None, None,
                                       'Electricity', zones,
                                       chilled_water_loop_cooling_type='AirCooled')
        standard.model_add_hvac_system(os_model, 'Unit Heaters', 'NaturalGas',
                                       None, None, heated_zones)

    elif equip == 'FCU_ACChiller':
        standard.model_add_hvac_system(os_model, 'Fan Coil', None, None,
                                       'Electricity', zones,
                                       chilled_water_loop_cooling_type='AirCooled')

    elif equip == 'FCU_DCW_Boiler':
        standard.model_add_hvac_system(os_model, 'Fan Coil ', 'NaturalGas', None,
                                       'DistrictCooling', zones)

    elif equip == 'FCU_DCW_ASHP':
        standard.model_add_hvac_system(os_model, 'Fan Coil', 'AirSourceHeatPump',
                                       None, 'DistrictCooling', zones)

    elif equip == 'FCU_DCW_DHW':
        standard.model_add_hvac_system(os_model, 'Fan Coil', 'DistrictHeating',
                                       None, 'DistrictCooling', zones)

    elif equip == 'FCU_DCW_ElectricBaseboard':
        standard.model_add_hvac_system(os_model, 'Fan Coil', None, None,
                                       'DistrictCooling', zones)
        standard.model_add_hvac_system(os_model, 'Baseboards', 'Electricity',
                                       None, None, heated_zones)

    elif equip == 'FCU_DCW_GasHeaters':
        standard.model_add_hvac_system(os_model, 'Fan Coil', None, None,
                                       'DistrictCooling', zones)
        standard.model_add_hvac_system(os_model, 'Unit Heaters', 'NaturalGas',
                                       None, None, heated_zones)

    elif equip == 'FCU_DCW':
        standard.model_add_hvac_system(os_model, 'Fan Coil', None, None,
                                       'DistrictCooling', zones)

    elif equip == 'Furnace':
        # includes ventilation, whereas residential forced air furnace does not.
        standard.model_add_hvac_system(os_model, 'Forced Air Furnace', 'NaturalGas',
                                       None, None, heated_zones)

    elif equip == 'Furnace_Electric':
        # includes ventilation, whereas residential forced air furnace does not.
        standard.model_add_hvac_system(os_model, 'Forced Air Furnace', 'Electricity',
                                       None, None, heated_zones)

    elif equip == 'GasHeaters':
        standard.model_add_hvac_system(os_model, 'Unit Heaters', 'NaturalGas',
                                       None, None, heated_zones)

    elif equip == 'PTAC_ElectricBaseboard':
        standard.model_add_hvac_system(os_model, 'PTAC', None, None, 'Electricity',
                                       system_zones)
        standard.model_add_hvac_system(os_model, 'Baseboards', 'Electricity',
                                       None, None, heated_zones)

    elif equip == 'PTAC_BoilerBaseboard':
        standard.model_add_hvac_system(os_model, 'PTAC', None, None, 'Electricity',
                                       system_zones)
        standard.model_add_hvac_system(os_model, 'Baseboards', 'NaturalGas',
                                       None, None, heated_zones)

    elif equip == 'PTAC_DHWBaseboard':
        standard.model_add_hvac_system(os_model, 'PTAC', None, None, 'Electricity',
                                       system_zones)
        standard.model_add_hvac_system(os_model, 'Baseboards', 'DistrictHeating',
                                       None, None, heated_zones)

    elif equip == 'PTAC_GasHeaters':
        standard.model_add_hvac_system(os_model, 'PTAC', None, None, 'Electricity',
                                       system_zones)
        standard.model_add_hvac_system(os_model, 'Unit Heaters', 'NaturalGas',
                                       None, None, heated_zones)

    elif equip == 'PTAC_ElectricCoil':
        standard.model_add_hvac_system(os_model, 'PTAC', None, 'Electricity',
                                       'Electricity', system_zones)
        # use 'Baseboard electric' for heated only zones
        standard.model_add_hvac_system(os_model, 'Baseboards', 'Electricity',
                                       None, None, heated_only_zones)

    elif equip == 'PTAC_GasCoil':
        standard.model_add_hvac_system(os_model, 'PTAC', None, 'NaturalGas',
                                       'Electricity', system_zones)
        # use 'Baseboard electric' for heated only zones
        standard.model_add_hvac_system(os_model, 'Baseboards', 'Electricity',
                                       None, None, heated_only_zones)

    elif equip == 'PTAC_Boiler':
        standard.model_add_hvac_system(os_model, 'PTAC', 'NaturalGas', None,
                                       'Electricity', system_zones)
        # use 'Baseboard gas boiler' for heated only zones
        standard.model_add_hvac_system(os_model, 'Baseboards', 'NaturalGas',
                                       None, None, heated_only_zones)

    elif equip == 'PTAC_ASHP':
        standard.model_add_hvac_system(os_model, 'PTAC', 'AirSourceHeatPump',
                                       None, 'Electricity', system_zones)
        # use 'Baseboard central air source heat pump' for heated only zones
        standard.model_add_hvac_system(os_model, 'Baseboards', 'AirSourceHeatPump',
                                       None, None, heated_only_zones)

    elif equip == 'PTAC_DHW':
        standard.model_add_hvac_system(os_model, 'PTAC', 'DistrictHeating', None,
                                       'Electricity', system_zones)
        # use 'Baseboard district hot water heat' for heated only zones
        standard.model_add_hvac_system(os_model, 'Baseboards', 'DistrictHeating',
                                       None, None, heated_only_zones)

    elif equip == 'PTAC':
        standard.model_add_hvac_system(os_model, 'PTAC', None, None, 'Electricity',
                                       system_zones)

    elif equip == 'PTHP':
        standard.model_add_hvac_system(os_model, 'PTHP', 'Electricity', None,
                                       'Electricity', system_zones)
        # use 'Baseboard electric' for heated only zones
        standard.model_add_hvac_system(os_model, 'Baseboards', 'Electricity',
                                       None, None, heated_only_zones)

    elif equip == 'PSZAC_ElectricBaseboard':
        standard.model_add_hvac_system(os_model, 'PSZ-AC', None, None, 'Electricity',
                                       system_zones)
        standard.model_add_hvac_system(os_model, 'Baseboards', 'Electricity',
                                       None, None, heated_zones)

    elif equip == 'PSZAC_BoilerBaseboard':
        standard.model_add_hvac_system(os_model, 'PSZ-AC', None, None, 'Electricity',
                                       system_zones)
        standard.model_add_hvac_system(os_model, 'Baseboards', 'NaturalGas',
                                       None, None, heated_zones)

    elif equip == 'PSZAC_DHWBaseboard':
        standard.model_add_hvac_system(os_model, 'PSZ-AC', None, None, 'Electricity',
                                       system_zones)
        standard.model_add_hvac_system(os_model, 'Baseboards', 'DistrictHeating',
                                       None, None, heated_zones)

    elif equip == 'PSZAC_GasHeaters':
        standard.model_add_hvac_system(os_model, 'PSZ-AC', None, None, 'Electricity',
                                       system_zones)
        standard.model_add_hvac_system(os_model, 'Unit Heaters', 'NaturalGas',
                                       None, None, heated_zones)

    elif equip == 'PSZAC_ElectricCoil':
        standard.model_add_hvac_system(os_model, 'PSZ-AC', None, 'Electricity',
                                       'Electricity', system_zones)
        # use 'Baseboard electric' for heated only zones
        standard.model_add_hvac_system(os_model, 'Baseboards', 'Electricity',
                                       None, None, heated_only_zones)

    elif equip == 'PSZAC_GasCoil':
        standard.model_add_hvac_system(os_model, 'PSZ-AC', None, 'NaturalGas',
                                       'Electricity', system_zones)
        # use 'Baseboard electric' for heated only zones
        standard.model_add_hvac_system(os_model, 'Baseboards', 'Electricity',
                                       None, None, heated_only_zones)

    elif equip == 'PSZAC_Boiler':
        standard.model_add_hvac_system(os_model, 'PSZ-AC', 'NaturalGas', None,
                                       'Electricity', system_zones)
        # use 'Baseboard gas boiler' for heated only zones
        standard.model_add_hvac_system(os_model, 'Baseboards', 'NaturalGas',
                                       None, None, heated_only_zones)

    elif equip == 'PSZAC_ASHP':
        standard.model_add_hvac_system(os_model, 'PSZ-AC', 'AirSourceHeatPump',
                                       None, 'Electricity', system_zones)
        # use 'Baseboard central air source heat pump' for heated only zones
        standard.model_add_hvac_system(os_model, 'Baseboards', 'AirSourceHeatPump',
                                       None, None, heated_only_zones)

    elif equip == 'PSZAC_DHW':
        standard.model_add_hvac_system(os_model, 'PSZ-AC', 'DistrictHeating',
                                       None, 'Electricity', system_zones)
        # use 'Baseboard district hot water' for heated only zones
        standard.model_add_hvac_system(os_model, 'Baseboards', 'DistrictHeating',
                                       None, None, heated_only_zones)

    elif equip == 'PSZAC':
        standard.model_add_hvac_system(os_model, 'PSZ-AC', None, None,
                                       'Electricity', cooled_zones)

    elif equip == 'PSZAC_DCW_ElectricBaseboard':
        standard.model_add_hvac_system(os_model, 'PSZ-AC', None, None,
                                       'DistrictCooling', system_zones)
        standard.model_add_hvac_system(os_model, 'Baseboards', 'Electricity',
                                       None, None, heated_zones)

    elif equip == 'PSZAC_DCW_BoilerBaseboard':
        standard.model_add_hvac_system(os_model, 'PSZ-AC', None, None,
                                       'DistrictCooling', system_zones)
        standard.model_add_hvac_system(os_model, 'Baseboards', 'NaturalGas',
                                       None, None, heated_zones)

    elif equip == 'PSZAC_DCW_GasHeaters':
        standard.model_add_hvac_system(os_model, 'PSZ-AC', None, None,
                                       'DistrictCooling', system_zones)
        standard.model_add_hvac_system(os_model, 'Unit Heaters', 'NaturalGas',
                                       None, None, heated_zones)

    elif equip == 'PSZAC_DCW_ElectricCoil':
        standard.model_add_hvac_system(os_model, 'PSZ-AC', None, 'Electricity',
                                       'DistrictCooling', system_zones)
        # use 'Baseboard electric' for heated only zones
        standard.model_add_hvac_system(os_model, 'Baseboards', 'Electricity',
                                       None, None, heated_only_zones)

    elif equip == 'PSZAC_DCW_GasCoil':
        standard.model_add_hvac_system(os_model, 'PSZ-AC', None, 'NaturalGas',
                                       'DistrictCooling', system_zones)
        # use 'Baseboard electric' for heated only zones
        standard.model_add_hvac_system(os_model, 'Baseboards', 'Electricity',
                                       None, None, heated_only_zones)

    elif equip == 'PSZAC_DCW_Boiler':
        standard.model_add_hvac_system(os_model, 'PSZ-AC', 'NaturalGas', None,
                                       'DistrictCooling', system_zones)
        # use 'Baseboard gas boiler' for heated only zones
        standard.model_add_hvac_system(os_model, 'Baseboards', 'NaturalGas',
                                       None, None, heated_only_zones)

    elif equip == 'PSZAC_DCW_ASHP':
        standard.model_add_hvac_system(os_model, 'PSZ-AC', 'AirSourceHeatPump',
                                       None, 'DistrictCooling', system_zones)
        # use 'Baseboard central air source heat pump' for heated only zones
        standard.model_add_hvac_system(os_model, 'Baseboards', 'AirSourceHeatPump',
                                       None, None, heated_only_zones)

    elif equip == 'PSZAC_DCW_DHW':
        standard.model_add_hvac_system(os_model, 'PSZ-AC', 'DistrictHeating',
                                       None, 'DistrictCooling', system_zones)
        # use 'Baseboard district hot water' for heated only zones
        standard.model_add_hvac_system(os_model, 'Baseboards', 'DistrictHeating',
                                       None, None, heated_only_zones)

    elif equip == 'PSZAC_DCW':
        standard.model_add_hvac_system(os_model, 'PSZ-AC', None, None,
                                       'DistrictCooling', cooled_zones)

    elif equip == 'PSZHP':
        standard.model_add_hvac_system(os_model, 'PSZ-HP', 'Electricity', None,
                                       'Electricity', system_zones)
        # use 'Baseboard electric' for heated only zones
        standard.model_add_hvac_system(os_model, 'Baseboards', 'Electricity',
                                       None, None, heated_only_zones)

    # PVAV systems by default use a DX coil for cooling
    elif equip == 'PVAV_Boiler':
        standard.model_add_hvac_system(os_model, 'PVAV Reheat', 'NaturalGas',
                                       'NaturalGas', 'Electricity', zones)

    elif equip == 'PVAV_ASHP':
        standard.model_add_hvac_system(os_model, 'PVAV Reheat', 'AirSourceHeatPump',
                                       'AirSourceHeatPump', 'Electricity', zones)

    elif equip == 'PVAV_DHW':
        standard.model_add_hvac_system(os_model, 'PVAV Reheat', 'DistrictHeating',
                                       'DistrictHeating', 'Electricity', zones)

    elif equip == 'PVAV_PFP':
        standard.model_add_hvac_system(os_model, 'PVAV PFP Boxes', 'Electricity',
                                       'Electricity', 'Electricity', zones)

    elif equip == 'PVAV_BoilerElectricReheat':
        standard.model_add_hvac_system(os_model, 'PVAV Reheat', 'Gas', 'Electricity',
                                       'Electricity', zones)

    # all residential systems do not have ventilation
    elif equip == 'ResidentialAC_ElectricBaseboard':
        standard.model_add_hvac_system(os_model, 'Residential AC', None, None,
                                       None, cooled_zones)
        standard.model_add_hvac_system(os_model, 'Baseboards', 'Electricity',
                                       None, None, heated_zones)

    elif equip == 'ResidentialAC_BoilerBaseboard':
        standard.model_add_hvac_system(os_model, 'Residential AC', None, None,
                                       None, cooled_zones)
        standard.model_add_hvac_system(os_model, 'Baseboards', 'NaturalGas',
                                       None, None, heated_zones)

    elif equip == 'ResidentialAC_ASHPBaseboard':
        standard.model_add_hvac_system(os_model, 'Residential AC', None, None,
                                       None, cooled_zones)
        standard.model_add_hvac_system(os_model, 'Baseboards', 'AirSourceHeatPump',
                                       None, None, heated_zones)

    elif equip == 'ResidentialAC_DHWBaseboard':
        standard.model_add_hvac_system(os_model, 'Residential AC', None, None,
                                       None, cooled_zones)
        standard.model_add_hvac_system(os_model, 'Baseboards', 'DistrictHeating',
                                       None, None, heated_zones)

    elif equip == 'ResidentialAC_ResidentialFurnace':
        standard.model_add_hvac_system(os_model, 'Residential Forced Air Furnace with AC',
                                       None, None, None, zones)

    elif equip == 'ResidentialAC':
        standard.model_add_hvac_system(os_model, 'Residential AC', None, None,
                                       None, cooled_zones)

    elif equip == 'ResidentialHP':
        standard.model_add_hvac_system(os_model, 'Residential Air Source Heat Pump',
                                       'Electricity', None, 'Electricity', zones)

    elif equip == 'ResidentialHPNoCool':
        standard.model_add_hvac_system(os_model, 'Residential Air Source Heat Pump',
                                       'Electricity', None, None, heated_zones)

    elif equip == 'ResidentialFurnace':
        standard.model_add_hvac_system(os_model, 'Residential Forced Air Furnace',
                                       'NaturalGas', None, None, zones)

    elif equip == 'VAV_Chiller_Boiler':
        standard.model_add_hvac_system(os_model, 'VAV Reheat', 'NaturalGas',
                                       'NaturalGas', 'Electricity', zones)

    elif equip == 'VAV_Chiller_ASHP':
        standard.model_add_hvac_system(os_model, 'VAV Reheat', 'AirSourceHeatPump',
                                       'AirSourceHeatPump', 'Electricity', zones)

    elif equip == 'VAV_Chiller_DHW':
        standard.model_add_hvac_system(os_model, 'VAV Reheat', 'DistrictHeating',
                                       'DistrictHeating', 'Electricity', zones)

    elif equip == 'VAV_Chiller_PFP':
        standard.model_add_hvac_system(os_model, 'VAV PFP Boxes', 'NaturalGas',
                                       'NaturalGas', 'Electricity', zones)

    elif equip == 'VAV_Chiller_GasCoil':
        standard.model_add_hvac_system(os_model, 'VAV Gas Reheat', 'NaturalGas',
                                       'NaturalGas', 'Electricity', zones)

    elif equip == 'VAV_ACChiller_Boiler':
        standard.model_add_hvac_system(os_model, 'VAV Reheat', 'NaturalGas',
                                       'NaturalGas', 'Electricity', zones,
                                       chilled_water_loop_cooling_type='AirCooled')

    elif equip == 'VAV_ACChiller_ASHP':
        standard.model_add_hvac_system(os_model, 'VAV Reheat', 'AirSourceHeatPump',
                                       'AirSourceHeatPump', 'Electricity', zones,
                                       chilled_water_loop_cooling_type='AirCooled')

    elif equip == 'VAV_ACChiller_DHW':
        standard.model_add_hvac_system(os_model, 'VAV Reheat', 'DistrictHeating',
                                       'DistrictHeating', 'Electricity', zones,
                                       chilled_water_loop_cooling_type='AirCooled')

    elif equip == 'VAV_ACChiller_PFP':
        standard.model_add_hvac_system(os_model, 'VAV PFP Boxes', 'NaturalGas',
                                       'NaturalGas', 'Electricity', zones,
                                       chilled_water_loop_cooling_type='AirCooled')

    elif equip == 'VAV_ACChiller_GasCoil':
        standard.model_add_hvac_system(os_model, 'VAV Gas Reheat', 'NaturalGas',
                                       'NaturalGas', 'Electricity', zones,
                                       chilled_water_loop_cooling_type='AirCooled')

    elif equip == 'VAV_DCW_Boiler':
        standard.model_add_hvac_system(os_model, 'VAV Reheat', 'NaturalGas',
                                       'NaturalGas', 'DistrictCooling', zones)

    elif equip == 'VAV_DCW_ASHP':
        standard.model_add_hvac_system(os_model, 'VAV Reheat', 'AirSourceHeatPump',
                                       'AirSourceHeatPump', 'DistrictCooling', zones)

    elif equip == 'VAV_DCW_DHW':
        standard.model_add_hvac_system(os_model, 'VAV Reheat', 'DistrictHeating',
                                       'DistrictHeating', 'DistrictCooling', zones)

    elif equip == 'VAV_DCW_PFP':
        standard.model_add_hvac_system(os_model, 'VAV PFP Boxes', 'NaturalGas',
                                       'NaturalGas', 'DistrictCooling', zones)

    elif equip == 'VAV_DCW_GasCoil':
        standard.model_add_hvac_system(os_model, 'VAV Gas Reheat', 'NaturalGas',
                                       'NaturalGas', 'DistrictCooling', zones)

    elif equip == 'VRF':
        standard.model_add_hvac_system(os_model, 'VRF', 'Electricity', None,
                                       'Electricity', zones)

    elif equip == 'WSHP_FluidCooler_Boiler':
        standard.model_add_hvac_system(os_model, 'Water Source Heat Pumps',
                                       'NaturalGas', None, 'Electricity', zones,
                                       heat_pump_loop_cooling_type='FluidCooler')

    elif equip == 'WSHP_CoolingTower_Boiler':
        standard.model_add_hvac_system(os_model, 'Water Source Heat Pumps',
                                       'NaturalGas', None, 'Electricity', zones,
                                       heat_pump_loop_cooling_type='CoolingTower')

    elif equip == 'WSHP_GSHP':
        standard.model_add_hvac_system(os_model, 'Ground Source Heat Pumps',
                                       'Electricity', None, 'Electricity', zones)

    elif equip == 'WSHP_DCW_DHW':
        standard.model_add_hvac_system(os_model, 'Water Source Heat Pumps',
                                       'DistrictHeating', None, 'DistrictCooling', zones)

    elif equip == 'WindowAC_ElectricBaseboard':
        standard.model_add_hvac_system(os_model, 'Window AC', None, None,
                                       'Electricity', cooled_zones)
        standard.model_add_hvac_system(os_model, 'Baseboards', 'Electricity',
                                       None, None, heated_zones)

    elif equip == 'WindowAC_BoilerBaseboard':
        standard.model_add_hvac_system(os_model, 'Window AC', None, None,
                                       'Electricity', cooled_zones)
        standard.model_add_hvac_system(os_model, 'Baseboards', 'NaturalGas',
                                       None, None, heated_zones)

    elif equip == 'WindowAC_ASHPBaseboard':
        standard.model_add_hvac_system(os_model, 'Window AC', None, None,
                                       'Electricity', cooled_zones)
        standard.model_add_hvac_system(os_model, 'Baseboards', 'AirSourceHeatPump',
                                       None, None, heated_zones)

    elif equip == 'WindowAC_DHWBaseboard':
        standard.model_add_hvac_system(os_model, 'Window AC', None, None,
                                       'Electricity', cooled_zones)
        standard.model_add_hvac_system(os_model, 'Baseboards', 'DistrictHeating',
                                       None, None, heated_zones)

    elif equip == 'WindowAC_Furnace':
        standard.model_add_hvac_system(os_model, 'Window AC', None, None,
                                       'Electricity', cooled_zones)
        standard.model_add_hvac_system(os_model, 'Forced Air Furnace', 'NaturalGas',
                                       None, None, heated_zones)

    elif equip == 'WindowAC_GasHeaters':
        standard.model_add_hvac_system(os_model, 'Window AC', None, None,
                                       'Electricity', cooled_zones)
        standard.model_add_hvac_system(os_model, 'Unit Heaters', 'NaturalGas',
                                       None, None, heated_zones)

    elif equip == 'WindowAC':
        standard.model_add_hvac_system(os_model, 'Window AC', None, None,
                                       'Electricity', cooled_zones)

    else:
        print('HVAC system type "{}" not recognized'.format(equip))
