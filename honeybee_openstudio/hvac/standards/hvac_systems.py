"""Module taken from OpenStudio-standards."""


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
    pass
