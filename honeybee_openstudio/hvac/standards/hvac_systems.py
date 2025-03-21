"""Module taken from OpenStudio-standards.

https://github.com/NREL/openstudio-standards/blob/master/lib/openstudio-standards/prototypes/common/objects/Prototype.hvac_systems.rb
"""


def model_get_or_add_chilled_water_loop():
    pass


def model_get_or_add_hot_water_loop():
    pass


def model_add_doas():
    pass


def model_add_doas_cold_supply():
    pass


def model_add_vav_reheat():
    pass


def model_add_pvav():
    pass


def model_add_pvav_pfp_boxes():
    pass


def model_add_psz_vav():
    pass


def model_add_psz_ac():
    pass


def model_add_minisplit_hp():
    pass


def model_add_ptac():
    pass


def model_add_pthp():
    pass


def model_add_unitheater():
    pass


def model_add_high_temp_radiant():
    pass


def model_add_evap_cooler():
    pass


def model_add_baseboard():
    pass


def model_add_vrf():
    pass


def model_add_four_pipe_fan_coil():
    pass


def model_add_low_temp_radiant():
    pass


def model_add_window_ac():
    pass


def model_add_furnace_central_ac():
    pass


def model_add_central_air_source_heat_pump():
    pass


def model_add_water_source_hp():
    pass


def model_add_zone_erv():
    pass


def model_add_residential_erv():
    pass


def model_add_ideal_air_loads():
    pass


def model_add_residential_ventilator():
    pass


def model_get_or_add_ambient_water_loop():
    pass


def model_get_or_add_ground_hx_loop():
    pass


def model_get_or_add_heat_pump_loop():
    pass


def rename_air_loop_nodes():
    pass


def rename_plant_loop_nodes():
    pass


def model_add_hvac_system(
        model, system_type, main_heat_fuel, zone_heat_fuel, cool_fuel, zones,
        hot_water_loop_type='HighTemperature',
        chilled_water_loop_cooling_type='WaterCooled',
        heat_pump_loop_cooling_type='EvaporativeFluidCooler',
        air_loop_heating_type='Water', air_loop_cooling_type='Water',
        zone_equipment_ventilation=True, fan_coil_capacity_control_method='CyclingFan'):
    """Add the a system type to the zones based on the specified template.

    For multi-zone system types, add one system per story.

    Args:
        model: [OpenStudio::Model::Model] OpenStudio model object.
        system_type: [String] The system type.
        main_heat_fuel: [String] Main heating fuel used for air loops and plant loops.
        zone_heat_fuel: [String] Zone heating fuel for zone hvac equipment and
            terminal units.
        cool_fuel: [String] Cooling fuel used for air loops, plant loops, and
            zone equipment.
        zones: [Array<OpenStudio::Model::ThermalZone>] array of thermal zones
            served by the system.
        hot_water_loop_type: [String] Archetype for hot water loops. Either
            HighTemperature (180F supply) (default) or LowTemperature (120F supply).
            Only used if HVAC system has a hot water loop.
        chilled_water_loop_cooling_type [String] Archetype for chilled water loops.
            Only used if HVAC system has a chilled water loop and cool_fuel
            is Electricity. Options are.

            * AirCooled
            * WaterCooled

        heat_pump_loop_cooling_type: [String] the type of cooling equipment for
            heat pump loops if not DistrictCooling. Valid options are.

            * CoolingTower
            * CoolingTowerSingleSpeed
            * CoolingTowerTwoSpeed
            * CoolingTowerVariableSpeed
            * FluidCooler
            * FluidCoolerSingleSpeed
            * FluidCoolerTwoSpeed
            * EvaporativeFluidCooler
            * EvaporativeFluidCoolerSingleSpeed
            * EvaporativeFluidCoolerTwoSpeed

        air_loop_heating_type: [String] type of heating coil serving main air loop.
            Options are.

            * Gas
            * DX
            * Water

        air_loop_cooling_type: [String] type of cooling coil serving main air loop.
            Options are.

            * DX
            * Water

        zone_equipment_ventilation: [Boolean] toggle whether to include outdoor air
            ventilation on zone equipment including as fan coil units, VRF terminals,
            or water source heat pumps.
        fan_coil_capacity_control_method: [String] Only applicable to Fan Coil
            system type. Capacity control method for the fan coil. If VariableFan,
            the fan will be VariableVolume. Options are.

            * ConstantFanVariableFlow
            * CyclingFan
            * VariableFanVariableFlow
            * VariableFanConstantFlow.

    Returns:
        Returns True if successful, False if not.
    """
    # enforce defaults if fields are None
    if hot_water_loop_type is None:
        hot_water_loop_type = 'HighTemperature'
    if chilled_water_loop_cooling_type is None:
        chilled_water_loop_cooling_type = 'WaterCooled'
    if heat_pump_loop_cooling_type is None:
        heat_pump_loop_cooling_type = 'EvaporativeFluidCooler'
    if air_loop_heating_type is None:
        air_loop_heating_type = 'Water'
    if air_loop_cooling_type is None:
        air_loop_cooling_type = 'Water'
    if zone_equipment_ventilation is None:
        zone_equipment_ventilation = True
    if fan_coil_capacity_control_method is None:
        fan_coil_capacity_control_method = 'CyclingFan'

    # don't do anything if there are no zones
    if len(zones) == 0:
        return True

    # add the different types of systems
    if system_type == 'PTAC':
        water_types = ('NaturalGas', 'DistrictHeating',
                       'DistrictHeatingWater', 'DistrictHeatingSteam')
        if main_heat_fuel in water_types:
            heating_type = 'Water'
            hot_water_loop = model_get_or_add_hot_water_loop(
                model, main_heat_fuel, hot_water_loop_type=hot_water_loop_type)
        elif main_heat_fuel == 'AirSourceHeatPump':
            heating_type = 'Water'
            hot_water_loop = model_get_or_add_hot_water_loop(
                model, main_heat_fuel, hot_water_loop_type='LowTemperature')
        elif main_heat_fuel == 'Electricity':
            heating_type = main_heat_fuel
            hot_water_loop = None
        else:
            heating_type = zone_heat_fuel
            hot_water_loop = None

        model_add_ptac(
            model, zones, cooling_type='Single Speed DX AC', heating_type=heating_type,
            hot_water_loop=hot_water_loop, fan_type='Cycling',
            ventilation=zone_equipment_ventilation)

    elif system_type == 'PTHP':
        model_add_pthp(
            model, zones, fan_type='Cycling', ventilation=zone_equipment_ventilation)

    elif system_type == 'PSZ-AC':
        if main_heat_fuel in ('NaturalGas', 'Gas'):
            heating_type = main_heat_fuel
            supplemental_heating_type = 'Electricity'
            if air_loop_heating_type == 'Water':
                hot_water_loop = model_get_or_add_hot_water_loop(
                    model, main_heat_fuel, hot_water_loop_type=hot_water_loop_type)
                heating_type = 'Water'
            else:
                hot_water_loop = None
        elif main_heat_fuel in ('DistrictHeating', 'DistrictHeatingWater', 'DistrictHeatingSteam'):
            heating_type = 'Water'
            supplemental_heating_type = 'Electricity'
            hot_water_loop = model_get_or_add_hot_water_loop(
                model, main_heat_fuel, hot_water_loop_type=hot_water_loop_type)
        elif main_heat_fuel in ('AirSourceHeatPump', 'ASHP'):
            heating_type = 'Water'
            supplemental_heating_type = 'Electricity'
            hot_water_loop = model_get_or_add_hot_water_loop(
                model, main_heat_fuel, hot_water_loop_type='LowTemperature')
        elif main_heat_fuel == 'Electricity':
            heating_type = main_heat_fuel
            supplemental_heating_type = 'Electricity'
        else:
            heating_type = zone_heat_fuel
            supplemental_heating_type = None
            hot_water_loop = None

        if cool_fuel == 'DistrictCooling':
            chilled_water_loop = model_get_or_add_chilled_water_loop(model, cool_fuel)
            cooling_type = 'Water'
        else:
            chilled_water_loop = None
            cooling_type = 'Single Speed DX AC'

        model_add_psz_ac(
            model, zones, cooling_type=cooling_type, chilled_water_loop=chilled_water_loop,
            hot_water_loop=hot_water_loop, heating_type=heating_type,
            supplemental_heating_type=supplemental_heating_type,
            fan_location='DrawThrough', fan_type='ConstantVolume')

    elif system_type == 'PSZ-HP':
        model_add_psz_ac(
            model, zones, system_name='PSZ-HP', cooling_type='Single Speed Heat Pump',
            heating_type='Single Speed Heat Pump', supplemental_heating_type='Electricity',
            fan_location='DrawThrough', fan_type='ConstantVolume')

    elif system_type == 'PSZ-VAV':
        supplemental_heating_type = None if main_heat_fuel is None else 'Electricity'
        model_add_psz_vav(
            model, zones, system_name='PSZ-VAV', heating_type=main_heat_fuel,
            supplemental_heating_type=supplemental_heating_type,
            hvac_op_sch=None, oa_damper_sch=None)

    elif system_type == 'VRF':
        model_add_vrf(model, zones, ventilation=zone_equipment_ventilation)

    elif system_type == 'Fan Coil':
        water_types = ('NaturalGas', 'DistrictHeating', 'DistrictHeatingWater',
                       'DistrictHeatingSteam', 'Electricity')
        if main_heat_fuel in water_types:
            hot_water_loop = model_get_or_add_hot_water_loop(
                model, main_heat_fuel, hot_water_loop_type=hot_water_loop_type)
        elif main_heat_fuel == 'AirSourceHeatPump':
            hot_water_loop = model_get_or_add_hot_water_loop(
                model, main_heat_fuel, hot_water_loop_type='LowTemperature')
        else:
            hot_water_loop = None

        if cool_fuel in ('Electricity', 'DistrictCooling'):
            chilled_water_loop = model_get_or_add_chilled_water_loop(
                model, cool_fuel,
                chilled_water_loop_cooling_type=chilled_water_loop_cooling_type)
        else:
            chilled_water_loop = None

        model_add_four_pipe_fan_coil(
            model, zones, chilled_water_loop, hot_water_loop=hot_water_loop,
            ventilation=zone_equipment_ventilation,
            capacity_control_method=fan_coil_capacity_control_method)

    elif system_type == 'Radiant Slab':
        water_types = ('NaturalGas', 'DistrictHeating', 'DistrictHeatingWater',
                       'DistrictHeatingSteam', 'Electricity')
        if main_heat_fuel in water_types:
            hot_water_loop = model_get_or_add_hot_water_loop(
                model, main_heat_fuel, hot_water_loop_type=hot_water_loop_type)
        elif main_heat_fuel == 'AirSourceHeatPump':
            hot_water_loop = model_get_or_add_hot_water_loop(
                model, main_heat_fuel, hot_water_loop_type='LowTemperature')
        else:
            hot_water_loop = None

        if cool_fuel in ('Electricity', 'DistrictCooling'):
            chilled_water_loop = model_get_or_add_chilled_water_loop(
                model, cool_fuel,
                chilled_water_loop_cooling_type=chilled_water_loop_cooling_type)
        else:
            chilled_water_loop = None

        model_add_low_temp_radiant(model, zones, hot_water_loop, chilled_water_loop)

    elif system_type == 'Baseboards':
        water_types = ('NaturalGas', 'DistrictHeating', 'DistrictHeatingWater',
                       'DistrictHeatingSteam')
        if main_heat_fuel in water_types:
            hot_water_loop = model_get_or_add_hot_water_loop(
                model, main_heat_fuel, hot_water_loop_type=hot_water_loop_type)
        elif main_heat_fuel == 'AirSourceHeatPump':
            hot_water_loop = model_get_or_add_hot_water_loop(
                model, main_heat_fuel, hot_water_loop_type='LowTemperature')
        elif main_heat_fuel == 'Electricity':
            hot_water_loop = None
        else:
            print('Baseboards must have heating_type specified.')
            return False

        model_add_baseboard(model, zones, hot_water_loop=hot_water_loop)

    elif system_type == 'Unit Heaters':
        model_add_unitheater(
            model, zones, hvac_op_sch=None, fan_control_type='ConstantVolume',
            fan_pressure_rise=0.2, heating_type=main_heat_fuel)

    elif system_type == 'High Temp Radiant':
        model_add_high_temp_radiant(
            model, zones, heating_type=main_heat_fuel, combustion_efficiency=0.8)

    elif system_type == 'Window AC':
        model_add_window_ac(model, zones)

    elif system_type == 'Residential AC':
        model_add_furnace_central_ac(
            model, zones, heating=False, cooling=True, ventilation=False)

    elif system_type == 'Forced Air Furnace':
        model_add_furnace_central_ac(
            model, zones, heating=True, cooling=False, ventilation=True)

    elif system_type == 'Residential Forced Air Furnace':
        model_add_furnace_central_ac(
            model, zones, heating=True, cooling=False, ventilation=False)

    elif system_type == 'Residential Forced Air Furnace with AC':
        model_add_furnace_central_ac(
            model, zones, heating=True, cooling=True, ventilation=False)

    elif system_type == 'Residential Air Source Heat Pump':
        heating = False if main_heat_fuel is None else True
        cooling = False if cool_fuel is None else True
        model_add_central_air_source_heat_pump(
            model, zones, heating=heating, cooling=cooling, ventilation=False)

    elif system_type == 'Residential Minisplit Heat Pumps':
        model_add_minisplit_hp(model, zones)

    elif system_type == 'VAV Reheat':
        water_types = ('NaturalGas', 'Gas', 'HeatPump', 'DistrictHeating',
                       'DistrictHeatingWater', 'DistrictHeatingSteam')
        if main_heat_fuel in water_types:
            heating_type = main_heat_fuel
            hot_water_loop = model_get_or_add_hot_water_loop(
                model, main_heat_fuel, hot_water_loop_type=hot_water_loop_type)
        elif main_heat_fuel == 'AirSourceHeatPump':
            heating_type = main_heat_fuel
            hot_water_loop = model_get_or_add_hot_water_loop(
                model, main_heat_fuel, hot_water_loop_type='LowTemperature')
        else:
            heating_type = 'Electricity'
            hot_water_loop = None

        if air_loop_cooling_type == 'Water':
            chilled_water_loop = model_get_or_add_chilled_water_loop(
                model, cool_fuel,
                chilled_water_loop_cooling_type=chilled_water_loop_cooling_type)
        else:
            chilled_water_loop = None

        if hot_water_loop is None:
            if zone_heat_fuel in ('NaturalGas', 'Gas'):
                reheat_type = 'NaturalGas'
            elif zone_heat_fuel == 'Electricity':
                reheat_type = 'Electricity'
            else:
                msg = 'zone_heat_fuel "{}" is not supported with main_heat_fuel "{}" ' \
                    'for a "VAV Reheat" system type.'.format(
                       zone_heat_fuel, main_heat_fuel)
                print(msg)
                return False
        else:
            reheat_type = 'Water'

        model_add_vav_reheat(
            model, zones, heating_type=heating_type, reheat_type=reheat_type,
            hot_water_loop=hot_water_loop, chilled_water_loop=chilled_water_loop,
            fan_efficiency=0.62, fan_motor_efficiency=0.9, fan_pressure_rise=4.0)

    elif system_type == 'VAV No Reheat':
        water_types = ('NaturalGas', 'Gas', 'HeatPump', 'DistrictHeating',
                       'DistrictHeatingWater', 'DistrictHeatingSteam')
        if main_heat_fuel in water_types:
            heating_type = main_heat_fuel
            hot_water_loop = model_get_or_add_hot_water_loop(
                model, main_heat_fuel, hot_water_loop_type=hot_water_loop_type)
        elif main_heat_fuel == 'AirSourceHeatPump':
            heating_type = main_heat_fuel
            hot_water_loop = model_get_or_add_hot_water_loop(
                model, main_heat_fuel, hot_water_loop_type='LowTemperature')
        else:
            heating_type = 'Electricity'
            hot_water_loop = None

        if air_loop_cooling_type == 'Water':
            chilled_water_loop = model_get_or_add_chilled_water_loop(
                model, cool_fuel,
                chilled_water_loop_cooling_type=chilled_water_loop_cooling_type)
        else:
            chilled_water_loop = None

        model_add_vav_reheat(
            model, zones, heating_type=heating_type, reheat_type=None,
            hot_water_loop=hot_water_loop, chilled_water_loop=chilled_water_loop,
            fan_efficiency=0.62, fan_motor_efficiency=0.9, fan_pressure_rise=4.0)

    elif system_type == 'VAV Gas Reheat':
        if air_loop_cooling_type == 'Water':
            chilled_water_loop = model_get_or_add_chilled_water_loop(
                model, cool_fuel,
                chilled_water_loop_cooling_type=chilled_water_loop_cooling_type)
        else:
            chilled_water_loop = None

        model_add_vav_reheat(
            model, zones, heating_type='NaturalGas', reheat_type='NaturalGas',
            chilled_water_loop=chilled_water_loop, fan_efficiency=0.62,
            fan_motor_efficiency=0.9, fan_pressure_rise=4.0)

    elif system_type == 'PVAV Reheat':
        if main_heat_fuel == 'AirSourceHeatPump':
            hot_water_loop = model_get_or_add_hot_water_loop(
                model, main_heat_fuel, hot_water_loop_type='LowTemperature')
        else:
            if air_loop_heating_type == 'Water':
                hot_water_loop = model_get_or_add_hot_water_loop(
                    model, main_heat_fuel, hot_water_loop_type=hot_water_loop_type)
            else:
                heating_type = main_heat_fuel

        if cool_fuel == 'Electricity':
            chilled_water_loop = None
        else:
            chilled_water_loop = model_get_or_add_chilled_water_loop(
                model, cool_fuel,
                chilled_water_loop_cooling_type=chilled_water_loop_cooling_type)

        electric_reheat = True if zone_heat_fuel == 'Electricity' else False

        model_add_pvav(
            model, zones,
            hot_water_loop=hot_water_loop, chilled_water_loop=chilled_water_loop,
            heating_type=heating_type, electric_reheat=electric_reheat)

    elif system_type == 'PVAV PFP Boxes':
        if cool_fuel == 'DistrictCooling':
            chilled_water_loop = model_get_or_add_chilled_water_loop(model, cool_fuel)
        else:
            chilled_water_loop = None
        model_add_pvav_pfp_boxes(
            model, zones, chilled_water_loop=chilled_water_loop,
            fan_efficiency=0.62, fan_motor_efficiency=0.9, fan_pressure_rise=4.0)

    elif system_type == 'VAV PFP Boxes':
        chilled_water_loop = model_get_or_add_chilled_water_loop(
            model, cool_fuel,
            chilled_water_loop_cooling_type=chilled_water_loop_cooling_type)
        model_add_pvav_pfp_boxes(
            model, zones, chilled_water_loop=chilled_water_loop,
            fan_efficiency=0.62, fan_motor_efficiency=0.9, fan_pressure_rise=4.0)

    elif system_type == 'Water Source Heat Pumps':
        if ('DistrictHeating' in main_heat_fuel and cool_fuel == 'DistrictCooling') or \
                (main_heat_fuel == 'AmbientLoop' and cool_fuel == 'AmbientLoop'):
            condenser_loop = model_get_or_add_ambient_water_loop(model)
        else:
            condenser_loop = model_get_or_add_heat_pump_loop(
                model, main_heat_fuel, cool_fuel,
                heat_pump_loop_cooling_type=heat_pump_loop_cooling_type)

        model_add_water_source_hp(
            model, zones, condenser_loop, ventilation=zone_equipment_ventilation)

    elif system_type == 'Ground Source Heat Pumps':
        condenser_loop = model_get_or_add_ground_hx_loop(model)
        model_add_water_source_hp(
            model, zones, condenser_loop, ventilation=zone_equipment_ventilation)

    elif system_type == 'DOAS Cold Supply':
        hot_water_loop = model_get_or_add_hot_water_loop(
            model, main_heat_fuel, hot_water_loop_type=hot_water_loop_type)
        chilled_water_loop = model_get_or_add_chilled_water_loop(
            model, cool_fuel,
            chilled_water_loop_cooling_type=chilled_water_loop_cooling_type)
        model_add_doas_cold_supply(
            model, zones,
            hot_water_loop=hot_water_loop, chilled_water_loop=chilled_water_loop)

    elif system_type == 'DOAS':
        if air_loop_heating_type == 'Water':
            if main_heat_fuel is None:
                hot_water_loop = None
            elif main_heat_fuel == 'AirSourceHeatPump':
                hot_water_loop = model_get_or_add_hot_water_loop(
                    model, main_heat_fuel, hot_water_loop_type='LowTemperature')
            elif main_heat_fuel == 'Electricity':
                msg = 'air_loop_heating_type "{}" is not supported with main_heat_fuel ' \
                    '"{}" for a "DOAS" system type.'.format(
                        air_loop_heating_type, main_heat_fuel)
                return False
            else:
                hot_water_loop = model_get_or_add_hot_water_loop(
                    model, main_heat_fuel, hot_water_loop_type=hot_water_loop_type)
        else:
            hot_water_loop = None

        if air_loop_cooling_type == 'Water':
            chilled_water_loop = model_get_or_add_chilled_water_loop(
                model, cool_fuel,
                chilled_water_loop_cooling_type=chilled_water_loop_cooling_type)
        else:
            chilled_water_loop = None

        model_add_doas(
            model, zones, hot_water_loop=hot_water_loop,
            chilled_water_loop=chilled_water_loop)

    elif system_type == 'DOAS with DCV':
        if air_loop_heating_type == 'Water':
            if main_heat_fuel is None:
                hot_water_loop = None
            elif main_heat_fuel == 'AirSourceHeatPump':
                hot_water_loop = model_get_or_add_hot_water_loop(
                    model, main_heat_fuel, hot_water_loop_type='LowTemperature')
            else:
                hot_water_loop = model_get_or_add_hot_water_loop(
                    model, main_heat_fuel, hot_water_loop_type=hot_water_loop_type)
        else:
            hot_water_loop = None

        if air_loop_cooling_type == 'Water':
            chilled_water_loop = model_get_or_add_chilled_water_loop(
                model, cool_fuel,
                chilled_water_loop_cooling_type=chilled_water_loop_cooling_type)
        else:
            chilled_water_loop = None

        model_add_doas(
            model, zones,
            hot_water_loop=hot_water_loop, chilled_water_loop=chilled_water_loop,
            doas_type='DOASVAV', demand_control_ventilation=True)

    elif system_type == 'DOAS with Economizing':
        if air_loop_heating_type == 'Water':
            if main_heat_fuel is None:
                hot_water_loop = None
            elif main_heat_fuel == 'AirSourceHeatPump':
                hot_water_loop = model_get_or_add_hot_water_loop(
                    model, main_heat_fuel, hot_water_loop_type='LowTemperature')
            else:
                hot_water_loop = model_get_or_add_hot_water_loop(
                    model, main_heat_fuel, hot_water_loop_type=hot_water_loop_type)
        else:
            hot_water_loop = None

        if air_loop_cooling_type == 'Water':
            chilled_water_loop = model_get_or_add_chilled_water_loop(
                model, cool_fuel,
                chilled_water_loop_cooling_type=chilled_water_loop_cooling_type)
        else:
            chilled_water_loop = None

        model_add_doas(
            model, zones,
            hot_water_loop=hot_water_loop, chilled_water_loop=chilled_water_loop,
            doas_type='DOASVAV', econo_ctrl_mthd='FixedDryBulb')

    elif system_type == 'ERVs':
        model_add_zone_erv(model, zones)

    elif system_type == 'Residential ERVs':
        model_add_residential_erv(model, zones)

    elif system_type == 'Residential Ventilators':
        model_add_residential_ventilator(model, zones)

    elif system_type == 'Evaporative Cooler':
        model_add_evap_cooler(model, zones)

    elif system_type == 'Ideal Air Loads':
        model_add_ideal_air_loads(model, zones)

    else:  # Combination Systems
        if 'with DOAS with DCV' in system_type:
            # add DOAS DCV system
            model_add_hvac_system(
                model, 'DOAS with DCV', main_heat_fuel, zone_heat_fuel, cool_fuel, zones,
                hot_water_loop_type=hot_water_loop_type,
                chilled_water_loop_cooling_type=chilled_water_loop_cooling_type,
                heat_pump_loop_cooling_type=heat_pump_loop_cooling_type,
                air_loop_heating_type=air_loop_heating_type,
                air_loop_cooling_type=air_loop_cooling_type,
                zone_equipment_ventilation=False,
                fan_coil_capacity_control_method=fan_coil_capacity_control_method)
            # add paired system type
            paired_system_type = system_type.replace(' with DOAS with DCV', '')
            model_add_hvac_system(
                model, paired_system_type, main_heat_fuel, zone_heat_fuel, cool_fuel, zones,
                hot_water_loop_type=hot_water_loop_type,
                chilled_water_loop_cooling_type=chilled_water_loop_cooling_type,
                heat_pump_loop_cooling_type=heat_pump_loop_cooling_type,
                air_loop_heating_type=air_loop_heating_type,
                air_loop_cooling_type=air_loop_cooling_type,
                zone_equipment_ventilation=False,
                fan_coil_capacity_control_method=fan_coil_capacity_control_method)
        elif 'with DOAS' in system_type:
            # add DOAS system
            model_add_hvac_system(
                model, 'DOAS', main_heat_fuel, zone_heat_fuel, cool_fuel, zones,
                hot_water_loop_type=hot_water_loop_type,
                chilled_water_loop_cooling_type=chilled_water_loop_cooling_type,
                heat_pump_loop_cooling_type=heat_pump_loop_cooling_type,
                air_loop_heating_type=air_loop_heating_type,
                air_loop_cooling_type=air_loop_cooling_type,
                zone_equipment_ventilation=False,
                fan_coil_capacity_control_method=fan_coil_capacity_control_method)
            # add paired system type
            paired_system_type = system_type.replace(' with DOAS', '')
            model_add_hvac_system(
                model, paired_system_type, main_heat_fuel, zone_heat_fuel, cool_fuel, zones,
                hot_water_loop_type=hot_water_loop_type,
                chilled_water_loop_cooling_type=chilled_water_loop_cooling_type,
                heat_pump_loop_cooling_type=heat_pump_loop_cooling_type,
                air_loop_heating_type=air_loop_heating_type,
                air_loop_cooling_type=air_loop_cooling_type,
                zone_equipment_ventilation=False,
                fan_coil_capacity_control_method=fan_coil_capacity_control_method)
        elif 'with ERVs' in system_type:
            # add DOAS system
            model_add_hvac_system(
                model, 'ERVs', main_heat_fuel, zone_heat_fuel, cool_fuel, zones,
                hot_water_loop_type=hot_water_loop_type,
                chilled_water_loop_cooling_type=chilled_water_loop_cooling_type,
                heat_pump_loop_cooling_type=heat_pump_loop_cooling_type,
                air_loop_heating_type=air_loop_heating_type,
                air_loop_cooling_type=air_loop_cooling_type,
                zone_equipment_ventilation=False,
                fan_coil_capacity_control_method=fan_coil_capacity_control_method)
            # add paired system type
            paired_system_type = system_type.replace(' with ERVs', '')
            model_add_hvac_system(
                model, paired_system_type, main_heat_fuel, zone_heat_fuel, cool_fuel, zones,
                hot_water_loop_type=hot_water_loop_type,
                chilled_water_loop_cooling_type=chilled_water_loop_cooling_type,
                heat_pump_loop_cooling_type=heat_pump_loop_cooling_type,
                air_loop_heating_type=air_loop_heating_type,
                air_loop_cooling_type=air_loop_cooling_type,
                zone_equipment_ventilation=False,
                fan_coil_capacity_control_method=fan_coil_capacity_control_method)
        else:
            print('HVAC system type "{}" not recognized'.format(system_type))
            return False

    # rename air loop and plant loop nodes for readability
    rename_air_loop_nodes(model)
    rename_plant_loop_nodes(model)
