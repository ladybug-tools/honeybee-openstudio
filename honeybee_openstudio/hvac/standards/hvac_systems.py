# coding=utf-8
"""Module taken from OpenStudio-standards.

https://github.com/NREL/openstudio-standards/blob/master/
lib/openstudio-standards/prototypes/common/objects/Prototype.hvac_systems.rb
"""
from __future__ import division

from ladybug.datatype.temperature import Temperature
from ladybug.datatype.temperaturedelta import TemperatureDelta
from ladybug.datatype.pressure import Pressure

from honeybee_openstudio.openstudio import openstudio, openstudio_model
from .schedule import create_constant_schedule_ruleset
from .central_air_source_heat_pump import create_central_air_source_heat_pump
from .boiler_hot_water import create_boiler_hot_water

TEMPERATURE = Temperature()
TEMP_DELTA = TemperatureDelta()
PRESSURE = Pressure()


def standard_design_sizing_temperatures():
    """Get a dictionary of design sizing temperatures for lookups."""
    dsgn_temps = {}
    dsgn_temps['prehtg_dsgn_sup_air_temp_f'] = 45.0
    dsgn_temps['preclg_dsgn_sup_air_temp_f'] = 55.0
    dsgn_temps['htg_dsgn_sup_air_temp_f'] = 55.0
    dsgn_temps['clg_dsgn_sup_air_temp_f'] = 55.0
    dsgn_temps['zn_htg_dsgn_sup_air_temp_f'] = 104.0
    dsgn_temps['zn_clg_dsgn_sup_air_temp_f'] = 55.0
    dsgn_temps_c = {} 
    for key, val in dsgn_temps.items():
        dsgn_temps_c['{}_c'.format(key[:-2])] = TEMPERATURE.to_unit([val], 'C', 'F')[0]
    dsgn_temps.update(dsgn_temps_c)
    return dsgn_temps


def model_add_hw_loop(
        model, boiler_fuel_type, ambient_loop=None, system_name='Hot Water Loop',
        dsgn_sup_wtr_temp=180.0, dsgn_sup_wtr_temp_delt=20.0, pump_spd_ctrl='Variable',
        pump_tot_hd=None, boiler_draft_type=None, boiler_eff_curve_temp_eval_var=None,
        boiler_lvg_temp_dsgn=None, boiler_out_temp_lmt=None,
        boiler_max_plr=None, boiler_sizing_factor=None):
    """Create a hot water loop with a boiler, district heat, or water-to-water heat pump.

    Args:
        model: [OpenStudio::Model::Model] OpenStudio model object
        boiler_fuel_type: [String] valid choices are Electricity, NaturalGas,
            Propane, PropaneGas, FuelOilNo1, FuelOilNo2, DistrictHeating,
            DistrictHeatingWater, DistrictHeatingSteam, HeatPump
        ambient_loop: [OpenStudio::Model::PlantLoop] The condenser loop for the
            heat pump. Only used when boiler_fuel_type is HeatPump.
        system_name: [String] the name of the system. If None, it will be defaulted.
        dsgn_sup_wtr_temp: [Double] design supply water temperature in degrees
            Fahrenheit, default 180F.
        dsgn_sup_wtr_temp_delt: [Double] design supply-return water temperature
            difference in degrees Rankine, default 20R.
        pump_spd_ctrl: [String] pump speed control type, Constant or Variable (default).
        pump_tot_hd: [Double] pump head in ft H2O.
        boiler_draft_type: [String] Boiler type Condensing, MechanicalNoncondensing,
            Natural (default).
        boiler_eff_curve_temp_eval_var: [String] LeavingBoiler or EnteringBoiler
            temperature for the boiler efficiency curve.
        boiler_lvg_temp_dsgn: [Double] boiler leaving design temperature in
            degrees Fahrenheit.
        boiler_out_temp_lmt: [Double] boiler outlet temperature limit in
            degrees Fahrenheit.
        boiler_max_plr: [Double] boiler maximum part load ratio.
        boiler_sizing_factor: [Double] boiler oversizing factor.
    
    Returns:
        [OpenStudio::Model::PlantLoop] the resulting hot water loop.
    """
    # create hot water loop
    hot_water_loop = openstudio_model.PlantLoop(model)
    if system_name is None:
        hot_water_loop.setName('Hot Water Loop')
    else:
        hot_water_loop.setName(system_name)

    # hot water loop sizing and controls
    dsgn_sup_wtr_temp = 180.0 if dsgn_sup_wtr_temp is None else dsgn_sup_wtr_temp
    dsgn_sup_wtr_temp_c = TEMPERATURE.to_unit([dsgn_sup_wtr_temp], 'C', 'F')[0]
    dsgn_sup_wtr_temp_delt = 20.0 if dsgn_sup_wtr_temp_delt is None \
        else dsgn_sup_wtr_temp_delt
    dsgn_sup_wtr_temp_delt_k = TEMP_DELTA.to_unit([dsgn_sup_wtr_temp_delt], 'dC', 'dF')[0]

    sizing_plant = hot_water_loop.sizingPlant()
    sizing_plant.setLoopType('Heating')
    sizing_plant.setDesignLoopExitTemperature(dsgn_sup_wtr_temp_c)
    sizing_plant.setLoopDesignTemperatureDifference(dsgn_sup_wtr_temp_delt_k)
    hot_water_loop.setMinimumLoopTemperature(10.0)
    hw_temp_sch = create_constant_schedule_ruleset(
        model, dsgn_sup_wtr_temp_c,
        name='{} Temp - {}F'.format(hot_water_loop.nameString(), int(dsgn_sup_wtr_temp)),
        schedule_type_limit='Temperature')
    hw_stpt_manager = openstudio_model.SetpointManagerScheduled(model, hw_temp_sch)
    hw_stpt_manager.setName('{} Setpoint Manager'.format(hot_water_loop.nameString()))
    hw_stpt_manager.addToNode(hot_water_loop.supplyOutletNode)

    # create hot water pump
    if pump_spd_ctrl == 'Constant':
        hw_pump = openstudio_model.PumpConstantSpeed(model)
    elif pump_spd_ctrl == 'Variable':
        hw_pump = openstudio_model.PumpVariableSpeed(model)
    else:
        hw_pump = openstudio_model.PumpVariableSpeed(model)
    hw_pump.setName('{} Pump'.format(hot_water_loop.nameString()))
    if pump_tot_hd is None:
        pump_tot_hd_pa = PRESSURE.to_unit([60 * 12], 'Pa', 'inH2O')[0]
    else:
        pump_tot_hd_pa = PRESSURE.to_unit([pump_tot_hd * 12], 'Pa', 'inH2O')[0]
    hw_pump.setRatedPumpHead(pump_tot_hd_pa)
    hw_pump.setMotorEfficiency(0.9)
    hw_pump.setPumpControlType('Intermittent')
    hw_pump.addToNode(hot_water_loop.supplyInletNode())

    # switch statement to handle district heating name change
    if model.version() < openstudio.VersionString('3.7.0'):
        if boiler_fuel_type == 'DistrictHeatingWater' or \
                boiler_fuel_type == 'DistrictHeatingSteam':
            boiler_fuel_type = 'DistrictHeating'
    else:
        if boiler_fuel_type == 'DistrictHeating':
            boiler_fuel_type = 'DistrictHeatingWater'

    # create boiler and add to loop
    # District Heating
    if boiler_fuel_type == 'DistrictHeating':
        district_heat = openstudio_model.DistrictHeating(model)
        district_heat.setName('{} District Heating'.format(hot_water_loop.nameString()))
        district_heat.autosizeNominalCapacity()
        hot_water_loop.addSupplyBranchForComponent(district_heat)
    elif boiler_fuel_type == 'DistrictHeatingWater':
        district_heat = openstudio_model.DistrictHeatingWater(model)
        district_heat.setName('{} District Heating'.format(hot_water_loop.nameString()))
        district_heat.autosizeNominalCapacity()
        hot_water_loop.addSupplyBranchForComponent(district_heat)
    elif boiler_fuel_type == 'DistrictHeatingSteam':
        district_heat = openstudio_model.DistrictHeatingSteam(model)
        district_heat.setName('{} District Heating'.format(hot_water_loop.nameString()))
        district_heat.autosizeNominalCapacity()
        hot_water_loop.addSupplyBranchForComponent(district_heat)
    elif boiler_fuel_type in ('HeatPump', 'AmbientLoop'):
        # Ambient Loop
        water_to_water_hp = openstudio_model.HeatPumpWaterToWaterEquationFitHeating(model)
        water_to_water_hp.setName(
            '{} Water to Water Heat Pump'.format(hot_water_loop.nameString()))
        hot_water_loop.addSupplyBranchForComponent(water_to_water_hp)
        # Get or add an ambient loop
        if ambient_loop is None:
            ambient_loop = model_get_or_add_ambient_water_loop(model)
        ambient_loop.addDemandBranchForComponent(water_to_water_hp)
    elif boiler_fuel_type in ('AirSourceHeatPump', 'ASHP'):
        # Central Air Source Heat Pump
        create_central_air_source_heat_pump(model, hot_water_loop)
      
    elif boiler_fuel_type in ('Electricity', 'Gas', 'NaturalGas', 'Propane',
                              'PropaneGas', 'FuelOilNo1', 'FuelOilNo2'):
        # Boiler
        lvg_temp_dsgn_f = dsgn_sup_wtr_temp if boiler_lvg_temp_dsgn is None \
            else boiler_lvg_temp_dsgn
        out_temp_lmt_f = 203.0 if boiler_out_temp_lmt is None else boiler_out_temp_lmt
        create_boiler_hot_water(
            model, hot_water_loop=hot_water_loop, fuel_type=boiler_fuel_type,
            draft_type=boiler_draft_type, nominal_thermal_efficiency=0.78,
            eff_curve_temp_eval_var=boiler_eff_curve_temp_eval_var,
            lvg_temp_dsgn_f=lvg_temp_dsgn_f, out_temp_lmt_f=out_temp_lmt_f,
            max_plr=boiler_max_plr, sizing_factor=boiler_sizing_factor)
    else:
        msg = 'Boiler fuel type {} is not valid, no boiler will be added.'.format(
            boiler_fuel_type)
        print(msg)

    # add hot water loop pipes
    supply_equipment_bypass_pipe = openstudio_model.PipeAdiabatic(model)
    supply_equipment_bypass_pipe.setName(
        '{} Supply Equipment Bypass'.format(hot_water_loop.nameString()))
    hot_water_loop.addSupplyBranchForComponent(supply_equipment_bypass_pipe)

    coil_bypass_pipe = openstudio_model.PipeAdiabatic(model)
    coil_bypass_pipe.setName('{} Coil Bypass'.format(hot_water_loop.nameString()))
    hot_water_loop.addDemandBranchForComponent(coil_bypass_pipe)

    supply_outlet_pipe = openstudio_model.PipeAdiabatic(model)
    supply_outlet_pipe.setName('{} Supply Outlet'.format(hot_water_loop.nameString()))
    supply_outlet_pipe.addToNode(hot_water_loop.supplyOutletNode())

    demand_inlet_pipe = openstudio_model.PipeAdiabatic(model)
    demand_inlet_pipe.setName('{} Demand Inlet'.format(hot_water_loop.nameString()))
    demand_inlet_pipe.addToNode(hot_water_loop.demandInletNode())

    demand_outlet_pipe = openstudio_model.PipeAdiabatic(model)
    demand_outlet_pipe.setName('{} Demand Outlet'.format(hot_water_loop.nameString()))
    demand_outlet_pipe.addToNode(hot_water_loop.demandOutletNode())

    return hot_water_loop


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
