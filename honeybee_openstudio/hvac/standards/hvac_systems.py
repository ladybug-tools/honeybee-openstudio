# coding=utf-8
"""Module taken from OpenStudio-standards.

https://github.com/NREL/openstudio-standards/blob/master/
lib/openstudio-standards/prototypes/common/objects/Prototype.hvac_systems.rb
"""
from __future__ import division

from ladybug.datatype.temperature import Temperature
from ladybug.datatype.temperaturedelta import TemperatureDelta
from ladybug.datatype.pressure import Pressure
from ladybug.datatype.volumeflowrate import VolumeFlowRate

from honeybee_openstudio.openstudio import openstudio, openstudio_model, os_vector_len
from .utilities import kw_per_ton_to_cop, ems_friendly_name, \
    rename_air_loop_nodes, rename_plant_loop_nodes
from .schedule import create_constant_schedule_ruleset, model_add_schedule
from .thermal_zone import thermal_zone_get_outdoor_airflow_rate

from .central_air_source_heat_pump import create_central_air_source_heat_pump
from .boiler_hot_water import create_boiler_hot_water
from .plant_loop import chw_sizing_control, plant_loop_set_chw_pri_sec_configuration
from .pump_variable_speed import pump_variable_speed_set_control_type
from .cooling_tower import prototype_apply_condenser_water_temperatures
from .fan import create_fan_by_name
from .coil_heating import create_coil_heating_electric, create_coil_heating_gas, \
    create_coil_heating_water, create_coil_heating_dx_single_speed, \
    create_coil_heating_water_to_air_heat_pump_equation_fit
from .coil_cooling import create_coil_cooling_water, create_coil_cooling_dx_single_speed, \
    create_coil_cooling_water_to_air_heat_pump_equation_fit, \
    create_coil_cooling_dx_two_speed
from .heat_recovery import create_hx_air_to_air_sensible_and_latent
from .sizing_system import adjust_sizing_system

TEMPERATURE = Temperature()
TEMP_DELTA = TemperatureDelta()
PRESSURE = Pressure()
FLOW_RATE = VolumeFlowRate()


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
    hw_stpt_manager.addToNode(hot_water_loop.supplyOutletNode())

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


def model_add_chw_loop(
        model, system_name='Chilled Water Loop', cooling_fuel='Electricity',
        dsgn_sup_wtr_temp=44.0, dsgn_sup_wtr_temp_delt=10.1, chw_pumping_type=None,
        chiller_cooling_type=None, chiller_condenser_type=None,
        chiller_compressor_type=None, num_chillers=1,
        condenser_water_loop=None, waterside_economizer='none'):
    """Create a chilled water loop and adds it to the model.

    Args:
        model: [OpenStudio::Model::Model] OpenStudio model object.
        system_name: [String] the name of the system, or None in which case
            it will be defaulted.
        cooling_fuel: [String] cooling fuel. Valid choices are: Electricity,
            DistrictCooling.
        dsgn_sup_wtr_temp: [Double] design supply water temperature in degrees
            Fahrenheit, default 44F.
        dsgn_sup_wtr_temp_delt: [Double] design supply-return water temperature
            difference in degrees Rankine, default 10 dF.
        chw_pumping_type: [String] valid choices are const_pri, const_pri_var_sec.
        chiller_cooling_type: [String] valid choices are AirCooled, WaterCooled.
        chiller_condenser_type: [String] valid choices are WithCondenser,
            WithoutCondenser, None.
        chiller_compressor_type: [String] valid choices are Centrifugal,
            Reciprocating, Rotary Screw, Scroll, None.
        num_chillers: [Integer] the number of chillers.
        condenser_water_loop: [OpenStudio::Model::PlantLoop] optional condenser
            water loop for water-cooled chillers. If None, the chillers will
            be air cooled.
        waterside_economizer: [String] Options are none, integrated, non-integrated.
            If integrated will add a heat exchanger to the supply inlet of the
            chilled water loop to provide waterside economizing whenever wet
            bulb temperatures allow. Non-integrated will add a heat exchanger
            in parallel with the chiller that will operate only when it can
            meet cooling demand exclusively with the waterside economizing.

    Returns:
        [OpenStudio::Model::PlantLoop] the resulting chilled water loop.
    """
    # create chilled water loop
    chilled_water_loop = openstudio_model.PlantLoop(model)
    if system_name is None:
        chilled_water_loop.setName('Chilled Water Loop')
    else:
        chilled_water_loop.setName(system_name)
    dsgn_sup_wtr_temp = 44 if dsgn_sup_wtr_temp is None else dsgn_sup_wtr_temp

    # chilled water loop sizing and controls
    chw_sizing_control(model, chilled_water_loop, dsgn_sup_wtr_temp, dsgn_sup_wtr_temp_delt)

    # create chilled water pumps
    if chw_pumping_type == 'const_pri':
        # primary chilled water pump
        pri_chw_pump = openstudio_model.PumpVariableSpeed(model)
        pri_chw_pump.setName('{} Pump'.format(chilled_water_loop.nameString()))
        pri_chw_pump.setRatedPumpHead(PRESSURE.to_unit([60 * 12], 'Pa', 'inH2O')[0])
        pri_chw_pump.setMotorEfficiency(0.9)
        # flat pump curve makes it behave as a constant speed pump
        pri_chw_pump.setFractionofMotorInefficienciestoFluidStream(0)
        pri_chw_pump.setCoefficient1ofthePartLoadPerformanceCurve(0)
        pri_chw_pump.setCoefficient2ofthePartLoadPerformanceCurve(1)
        pri_chw_pump.setCoefficient3ofthePartLoadPerformanceCurve(0)
        pri_chw_pump.setCoefficient4ofthePartLoadPerformanceCurve(0)
        pri_chw_pump.setPumpControlType('Intermittent')
        pri_chw_pump.addToNode(chilled_water_loop.supplyInletNode())
    elif chw_pumping_type == 'const_pri_var_sec':
        pri_sec_config = plant_loop_set_chw_pri_sec_configuration(model)

        if pri_sec_config == 'common_pipe':
            # primary chilled water pump
            pri_chw_pump = openstudio_model.PumpConstantSpeed(model)
            pri_chw_pump.setName('{} Primary Pump'.format(chilled_water_loop.nameString()))
            pri_chw_pump.setRatedPumpHead(PRESSURE.to_unit([15 * 12], 'Pa', 'inH2O')[0])
            pri_chw_pump.setMotorEfficiency(0.9)
            pri_chw_pump.setPumpControlType('Intermittent')
            pri_chw_pump.addToNode(chilled_water_loop.supplyInletNode())
            # secondary chilled water pump
            sec_chw_pump = openstudio_model.PumpVariableSpeed(model)
            sec_chw_pump.setName('{} Secondary Pump'.format(chilled_water_loop.nameString()))
            sec_chw_pump.setRatedPumpHead(PRESSURE.to_unit([45 * 12], 'Pa', 'inH2O')[0])
            sec_chw_pump.setMotorEfficiency(0.9)
            # curve makes it perform like variable speed pump
            sec_chw_pump.setFractionofMotorInefficienciestoFluidStream(0)
            sec_chw_pump.setCoefficient1ofthePartLoadPerformanceCurve(0)
            sec_chw_pump.setCoefficient2ofthePartLoadPerformanceCurve(0.0205)
            sec_chw_pump.setCoefficient3ofthePartLoadPerformanceCurve(0.4101)
            sec_chw_pump.setCoefficient4ofthePartLoadPerformanceCurve(0.5753)
            sec_chw_pump.setPumpControlType('Intermittent')
            sec_chw_pump.addToNode(chilled_water_loop.demandInletNode())
            # Change the chilled water loop to have a two-way common pipes
            chilled_water_loop.setCommonPipeSimulation('CommonPipe')
        elif pri_sec_config == 'heat_exchanger':
            # Check number of chillers
            if num_chillers > 3:
                msg = 'EMS Code for multiple chiller pump has not been written for ' \
                    'greater than 3 chillers. This has {} chillers'.format(num_chillers)
                print(msg)
            # NOTE: PRECONDITIONING for `const_pri_var_sec` pump type is only applicable
            # for PRM routine and only applies to System Type 7 and System Type 8
            # See: model_add_prm_baseline_system under Model object.
            # In this scenario, we will need to create a primary and secondary configuration:
            # chilled_water_loop is the primary loop
            # Primary: demand: heat exchanger, supply: chillers, name: Chilled Water Loop_Primary
            # Secondary: demand: Coils, supply: heat exchanger, name: Chilled Water Loop
            secondary_chilled_water_loop = openstudio_model.PlantLoop(model)
            secondary_loop_name = 'Chilled Water Loop' if system_name is None \
                else system_name
            # Reset primary loop name
            chilled_water_loop.setName('{}_Primary'.format(secondary_loop_name))
            secondary_chilled_water_loop.setName(secondary_loop_name)
            chw_sizing_control(model, secondary_chilled_water_loop,
                               dsgn_sup_wtr_temp, dsgn_sup_wtr_temp_delt)
            chilled_water_loop.additionalProperties.setFeature('is_primary_loop', True)
            chilled_water_loop.additionalProperties.setFeature(
                'secondary_loop_name', secondary_chilled_water_loop.nameString())
            secondary_chilled_water_loop.additionalProperties.setFeature(
                'is_secondary_loop', True)
            # primary chilled water pumps are added when adding chillers
            # Add Constant pump, in plant loop, the number of chiller adjustment
            # will assign pump to each chiller
            pri_chw_pump = openstudio_model.PumpVariableSpeed(model)
            pump_variable_speed_set_control_type(
                pri_chw_pump, control_type='Riding Curve')
            # This pump name is important for function
            # add_ems_for_multiple_chiller_pumps_w_secondary_plant
            # If you update it here, you must update the logic there to account for this
            pri_chw_pump.setName('{} Primary Pump'.format(chilled_water_loop.nameString()))
            # Will need to adjust the pump power after a sizing run
            pri_chw_pump.setRatedPumpHead(
                PRESSURE.to_unit([15 * 12], 'Pa', 'inH2O')[0] / num_chillers)
            pri_chw_pump.setMotorEfficiency(0.9)
            pri_chw_pump.setPumpControlType('Intermittent')
            pri_chw_pump.addToNode(chilled_water_loop.supplyInletNode())

            # secondary chilled water pump
            sec_chw_pump = openstudio_model.PumpVariableSpeed(model)
            sec_chw_pump.setName('{} Pump'.format(secondary_chilled_water_loop.nameString()))
            sec_chw_pump.setRatedPumpHead(PRESSURE.to_unit([45 * 12], 'Pa', 'inH2O')[0])
            sec_chw_pump.setMotorEfficiency(0.9)
            # curve makes it perform like variable speed pump
            sec_chw_pump.setFractionofMotorInefficienciestoFluidStream(0)
            sec_chw_pump.setCoefficient1ofthePartLoadPerformanceCurve(0)
            sec_chw_pump.setCoefficient2ofthePartLoadPerformanceCurve(0.0205)
            sec_chw_pump.setCoefficient3ofthePartLoadPerformanceCurve(0.4101)
            sec_chw_pump.setCoefficient4ofthePartLoadPerformanceCurve(0.5753)
            sec_chw_pump.setPumpControlType('Intermittent')
            sec_chw_pump.addToNode(secondary_chilled_water_loop.demandInletNode())

            # Add HX to connect secondary and primary loop
            heat_exchanger = openstudio_model.HeatExchangerFluidToFluid(model)
            secondary_chilled_water_loop.addSupplyBranchForComponent(heat_exchanger)
            chilled_water_loop.addDemandBranchForComponent(heat_exchanger)

            # Clean up connections
            hx_bypass_pipe = openstudio_model.PipeAdiabatic(model)
            hx_bypass_pipe.setName(
                '{} HX Bypass'.format(secondary_chilled_water_loop.nameString()))
            secondary_chilled_water_loop.addSupplyBranchForComponent(hx_bypass_pipe)
            outlet_pipe = openstudio_model.PipeAdiabatic(model)
            outlet_pipe.setName(
                '{} Supply Outlet'.format(secondary_chilled_water_loop.nameString()))
            outlet_pipe.addToNode(secondary_chilled_water_loop.supplyOutletNode())
        else:
            msg = 'No primary/secondary configuration specified for chilled water loop.'
            print(msg)
    else:
        print('No pumping type specified for the chilled water loop.')

    # check for existence of condenser_water_loop if WaterCooled
    if chiller_cooling_type == 'WaterCooled' and condenser_water_loop is None:
        print('Requested chiller is WaterCooled but no condenser loop specified.')

    # check for non-existence of condenser_water_loop if AirCooled
    if chiller_cooling_type == 'AirCooled' and condenser_water_loop is not None:
        print('Requested chiller is AirCooled but condenser loop specified.')

    if cooling_fuel == 'DistrictCooling':
        # DistrictCooling
        dist_clg = openstudio_model.DistrictCooling(model)
        dist_clg.setName('Purchased Cooling')
        dist_clg.autosizeNominalCapacity()
        chilled_water_loop.addSupplyBranchForComponent(dist_clg)
    else:
        # use default efficiency from 90.1-2019
        # 1.188 kw/ton for a 150 ton AirCooled chiller
        # 0.66 kw/ton for a 150 ton Water Cooled positive displacement chiller
        if chiller_cooling_type == 'AirCooled':
            default_cop = kw_per_ton_to_cop(1.188)
        elif chiller_cooling_type == 'WaterCooled':
            default_cop = kw_per_ton_to_cop(0.66)
        else:
            default_cop = kw_per_ton_to_cop(0.66)

        # make the correct type of chiller based these properties
        chiller_sizing_factor = round(1.0 / num_chillers, 2)

        # Create chillers and set plant operation scheme
        for i in range(num_chillers):
            chiller = openstudio_model.ChillerElectricEIR(model)
            ch_name = 'ASHRAE 90.1 {} {} {} Chiller {}'.format(
                chiller_cooling_type, chiller_condenser_type, chiller_compressor_type, i)
            chiller.setName(ch_name)
            chilled_water_loop.addSupplyBranchForComponent(chiller)
            dsgn_sup_wtr_temp_c = TEMPERATURE.to_unit([dsgn_sup_wtr_temp], 'C', 'F')[0]
            chiller.setReferenceLeavingChilledWaterTemperature(dsgn_sup_wtr_temp_c)
            lcw_ltl = TEMPERATURE.to_unit([36.0], 'C', 'F')[0]
            chiller.setLeavingChilledWaterLowerTemperatureLimit(lcw_ltl)
            rec_ft = TEMPERATURE.to_unit([95.0], 'C', 'F')[0]
            chiller.setReferenceEnteringCondenserFluidTemperature(rec_ft)
            chiller.setMinimumPartLoadRatio(0.15)
            chiller.setMaximumPartLoadRatio(1.0)
            chiller.setOptimumPartLoadRatio(1.0)
            chiller.setMinimumUnloadingRatio(0.25)
            chiller.setChillerFlowMode('ConstantFlow')
            chiller.setSizingFactor(chiller_sizing_factor)
            chiller.setReferenceCOP(default_cop)

            # connect the chiller to the condenser loop if one was supplied
            if condenser_water_loop is None:
                chiller.setCondenserType('AirCooled')
            else:
                condenser_water_loop.addDemandBranchForComponent(chiller)
                chiller.setCondenserType('WaterCooled')

    # enable waterside economizer if requested
    if condenser_water_loop is not None:
        if waterside_economizer == 'integrated':
            model_add_waterside_economizer(
                model, chilled_water_loop, condenser_water_loop, integrated=True)
        elif waterside_economizer == 'non-integrated':
            model_add_waterside_economizer(
                model, chilled_water_loop, condenser_water_loop, integrated=False)

    # chilled water loop pipes
    chiller_bypass_pipe = openstudio_model.PipeAdiabatic(model)
    chiller_bypass_pipe.setName('{} Chiller Bypass'.format(chilled_water_loop.nameString()))
    chilled_water_loop.addSupplyBranchForComponent(chiller_bypass_pipe)

    coil_bypass_pipe = openstudio_model.PipeAdiabatic(model)
    coil_bypass_pipe.setName('{} Coil Bypass'.format(chilled_water_loop.nameString()))
    chilled_water_loop.addDemandBranchForComponent(coil_bypass_pipe)

    supply_outlet_pipe = openstudio_model.PipeAdiabatic(model)
    supply_outlet_pipe.setName('{} Supply Outlet'.format(chilled_water_loop.nameString()))
    supply_outlet_pipe.addToNode(chilled_water_loop.supplyOutletNode())

    demand_inlet_pipe = openstudio_model.PipeAdiabatic(model)
    demand_inlet_pipe.setName('{} Demand Inlet'.format(chilled_water_loop.nameString()))
    demand_inlet_pipe.addToNode(chilled_water_loop.demandInletNode())

    demand_outlet_pipe = openstudio_model.PipeAdiabatic(model)
    demand_outlet_pipe.setName('{} Demand Outlet'.format(chilled_water_loop.nameString()))
    demand_outlet_pipe.addToNode(chilled_water_loop.demandOutletNode())

    return chilled_water_loop


def model_add_vsd_twr_fan_curve(model):
    """Add a curve to be used for cooling tower fans."""
    # check for the existing curve
    exist_curve = model.getCurveCubicByName('VSD-TWR-FAN-FPLR')
    if exist_curve.is_initialized():
        return exist_curve.get()
    # create the curve
    curve = openstudio_model.CurveCubic(model)
    curve.setName('VSD-TWR-FAN-FPLR')
    curve.setCoefficient1Constant(0.33162901)
    curve.setCoefficient2x(-0.88567609)
    curve.setCoefficient3xPOW2(0.60556507)
    curve.setCoefficient4xPOW3(0.9484823)
    curve.setMinimumValueofx(0.0)
    curve.setMaximumValueofx(1.0)
    return curve


def model_add_cw_loop(
        model, system_name='Condenser Water Loop', cooling_tower_type='Open Cooling Tower',
        cooling_tower_fan_type='Propeller or Axial',
        cooling_tower_capacity_control='TwoSpeed Fan',
        number_of_cells_per_tower=1, number_cooling_towers=1, use_90_1_design_sizing=True,
        sup_wtr_temp=70.0, dsgn_sup_wtr_temp=85.0, dsgn_sup_wtr_temp_delt=10.0,
        wet_bulb_approach=7.0, pump_spd_ctrl='Constant', pump_tot_hd=49.7):
    """Creates a condenser water loop and adds it to the model.

    Args:
        model: [OpenStudio::Model::Model] OpenStudio model object
        system_name: [String] the name of the system, or None in which case it
            will be defaulted.
        cooling_tower_type: [String] valid choices are Open Cooling Tower,
            Closed Cooling Tower.
        cooling_tower_fan_type: [String] valid choices are Centrifugal, "Propeller or Axial."
        cooling_tower_capacity_control: [String] valid choices are Fluid Bypass,
            Fan Cycling, TwoSpeed Fan, Variable Speed Fan.
        number_of_cells_per_tower: [Integer] the number of discrete cells per tower.
        number_cooling_towers: [Integer] the number of cooling towers to be
            added (in parallel).
        use_90_1_design_sizing: [Boolean] will determine the design sizing
            temperatures based on the 90.1 Appendix G approach. Overrides sup_wtr_temp,
            dsgn_sup_wtr_temp, dsgn_sup_wtr_temp_delt, and wet_bulb_approach if True.
        sup_wtr_temp: [Double] supply water temperature in degrees
            Fahrenheit, default 70F.
        dsgn_sup_wtr_temp: [Double] design supply water temperature in degrees
            Fahrenheit, default 85F.
        dsgn_sup_wtr_temp_delt: [Double] design water range temperature in
            degrees Rankine (aka. dF), default 10R.
        wet_bulb_approach: [Double] design wet bulb approach temperature, default 7R.
        pump_spd_ctrl: [String] pump speed control type, Constant or Variable (default).
        pump_tot_hd: [Double] pump head in ft H2O.

    Returns:
        [OpenStudio::Model::PlantLoop] the resulting condenser water plant loop
    """
    # create condenser water loop
    condenser_water_loop = openstudio_model.PlantLoop(model)
    system_name = 'Condenser Water Loop' if system_name is None else system_name
    condenser_water_loop.setName(system_name)

    # condenser water loop sizing and controls
    sup_wtr_temp = 70.0 if sup_wtr_temp is None else sup_wtr_temp
    sup_wtr_temp_c = TEMPERATURE.to_unit([sup_wtr_temp], 'C', 'F')[0]
    dsgn_sup_wtr_temp = 85.0 if dsgn_sup_wtr_temp is None else dsgn_sup_wtr_temp
    dsgn_sup_wtr_temp_c = TEMPERATURE.to_unit([dsgn_sup_wtr_temp], 'C', 'F')[0]
    dsgn_sup_wtr_temp_delt = 10.0 if dsgn_sup_wtr_temp_delt is None \
        else dsgn_sup_wtr_temp_delt
    dsgn_sup_wtr_temp_delt_k = TEMP_DELTA.to_unit([dsgn_sup_wtr_temp_delt], 'dC', 'dF')[0]
    wet_bulb_approach = 7.0 if wet_bulb_approach is None else wet_bulb_approach
    wet_bulb_approach_k = TEMP_DELTA.to_unit([wet_bulb_approach], 'dC', 'dF')[0]

    condenser_water_loop.setMinimumLoopTemperature(5.0)
    condenser_water_loop.setMaximumLoopTemperature(80.0)
    sizing_plant = condenser_water_loop.sizingPlant()
    sizing_plant.setLoopType('Condenser')
    sizing_plant.setDesignLoopExitTemperature(dsgn_sup_wtr_temp_c)
    sizing_plant.setLoopDesignTemperatureDifference(dsgn_sup_wtr_temp_delt_k)
    sizing_plant.setSizingOption('Coincident')
    sizing_plant.setZoneTimestepsinAveragingWindow(6)
    sizing_plant.setCoincidentSizingFactorMode('GlobalCoolingSizingFactor')

    # follow outdoor air wetbulb with given approach temperature
    cw_stpt_manager = openstudio_model.SetpointManagerFollowOutdoorAirTemperature(model)
    s_pt_name = '{} Setpoint Manager Follow OATwb with {}F Approach'.format(
        condenser_water_loop.nameString(), wet_bulb_approach)
    cw_stpt_manager.setName(s_pt_name)
    cw_stpt_manager.setReferenceTemperatureType('OutdoorAirWetBulb')
    cw_stpt_manager.setMaximumSetpointTemperature(dsgn_sup_wtr_temp_c)
    cw_stpt_manager.setMinimumSetpointTemperature(sup_wtr_temp_c)
    cw_stpt_manager.setOffsetTemperatureDifference(wet_bulb_approach_k)
    cw_stpt_manager.addToNode(condenser_water_loop.supplyOutletNode())

    # create condenser water pump
    if pump_spd_ctrl == 'Constant':
        cw_pump = openstudio_model.PumpConstantSpeed(model)
    elif pump_spd_ctrl == 'Variable':
        cw_pump = openstudio_model.PumpVariableSpeed(model)
    elif pump_spd_ctrl == 'HeaderedVariable':
        cw_pump = openstudio_model.HeaderedPumpsVariableSpeed(model)
        cw_pump.setNumberofPumpsinBank(2)
    elif pump_spd_ctrl == 'HeaderedConstant':
        cw_pump = openstudio_model.HeaderedPumpsConstantSpeed(model)
        cw_pump.setNumberofPumpsinBank(2)
    else:
        cw_pump = openstudio_model.PumpConstantSpeed(model)
    cw_pump.setName('{} {} Pump'.format(condenser_water_loop.nameString(), pump_spd_ctrl))
    cw_pump.setPumpControlType('Intermittent')

    pump_tot_hd = 49.7 if pump_tot_hd is None else pump_tot_hd
    pump_tot_hd_pa = PRESSURE.to_unit([pump_tot_hd * 12], 'Pa', 'inH2O')[0]
    cw_pump.setRatedPumpHead(pump_tot_hd_pa)
    cw_pump.addToNode(condenser_water_loop.supplyInletNode())

    # Cooling towers
    # Per PNNL PRM Reference Manual
    for _ in range(number_cooling_towers):
        # Tower object depends on the control type
        cooling_tower = None
        if cooling_tower_capacity_control in ('Fluid Bypass', 'Fan Cycling'):
            cooling_tower = openstudio_model.CoolingTowerSingleSpeed(model)
            if cooling_tower_capacity_control == 'Fluid Bypass':
                cooling_tower.setCellControl('FluidBypass')
            else:
                cooling_tower.setCellControl('FanCycling')
        elif cooling_tower_capacity_control == 'TwoSpeed Fan':
            cooling_tower = openstudio_model.CoolingTowerTwoSpeed(model)
        elif cooling_tower_capacity_control == 'Variable Speed Fan':
            cooling_tower = openstudio_model.CoolingTowerVariableSpeed(model)
            cooling_tower.setDesignRangeTemperature(dsgn_sup_wtr_temp_delt_k)
            cooling_tower.setDesignApproachTemperature(wet_bulb_approach_k)
            cooling_tower.setFractionofTowerCapacityinFreeConvectionRegime(0.125)
            twr_fan_curve = model_add_vsd_twr_fan_curve(model)
            cooling_tower.setFanPowerRatioFunctionofAirFlowRateRatioCurve(twr_fan_curve)
        else:
            msg = '{} is not a valid choice of cooling tower capacity control. ' \
                'Valid choices are Fluid Bypass, Fan Cycling, TwoSpeed Fan, Variable ' \
                'Speed Fan.'.format(cooling_tower_capacity_control)
            print(msg)

        # Set the properties that apply to all tower types and attach to the condenser loop.
        if cooling_tower is not None:
            twr_name = '{} {} {}'.format(
                cooling_tower_fan_type, cooling_tower_capacity_control,
                cooling_tower_type)
            cooling_tower.setName(twr_name)
            cooling_tower.setSizingFactor(1 / number_cooling_towers)
            cooling_tower.setNumberofCells(number_of_cells_per_tower)
            condenser_water_loop.addSupplyBranchForComponent(cooling_tower)

    # apply 90.1 sizing temperatures
    if use_90_1_design_sizing:
        # use the formulation in 90.1-2010 G3.1.3.11 to set the approach temperature
        # first, look in the model design day objects for sizing information
        summer_oat_wbs_f = []
        for dd in model.getDesignDays():
            if dd.dayType != 'SummerDesignDay':
                continue
            if 'WB=>MDB' not in dd.nameString():
                continue

            if model.version() < openstudio.VersionString('3.3.0'):
                if dd.humidityIndicatingType == 'Wetbulb':
                    summer_oat_wb_c = dd.humidityIndicatingConditionsAtMaximumDryBulb()
                    summer_oat_wbs_f.append(TEMPERATURE.to_unit([summer_oat_wb_c], 'F', 'C')[0])
                else:
                    msg = 'For {}, humidity is specified as {}; cannot determine Twb.'.format(
                        dd.nameString, dd.humidityIndicatingType())
                    print(msg)
            else:
                if dd.humidityConditionType() == 'Wetbulb' and \
                        dd.wetBulbOrDewPointAtMaximumDryBulb().is_initialized():
                    wb_mdbt = dd.wetBulbOrDewPointAtMaximumDryBulb().get()
                    summer_oat_wbs_f.append(TEMPERATURE.to_unit([wb_mdbt], 'F', 'C')[0])
                else:
                    msg = 'For {}, humidity is specified as {}; cannot determine Twb.'.format(
                        dd.nameString(), dd.humidityConditionType())
                    print(msg)

        # if values are still absent, use the CTI rating condition 78F
        design_oat_wb_f = None
        if len(summer_oat_wbs_f) == 0:
            design_oat_wb_f = 78.0
        else:
            design_oat_wb_f = max(summer_oat_wbs_f)  # Take worst case condition
        design_oat_wb_c = TEMPERATURE.to_unit([design_oat_wb_f], 'C', 'F')[0]

        # call method to apply design sizing to the condenser water loop
        prototype_apply_condenser_water_temperatures(
            condenser_water_loop, design_wet_bulb_c=design_oat_wb_c)

    # Condenser water loop pipes
    cooling_tower_bypass_pipe = openstudio_model.PipeAdiabatic(model)
    pipe_name = '{} Cooling Tower Bypass'.format(condenser_water_loop.nameString())
    cooling_tower_bypass_pipe.setName(pipe_name)
    condenser_water_loop.addSupplyBranchForComponent(cooling_tower_bypass_pipe)

    chiller_bypass_pipe = openstudio_model.PipeAdiabatic(model)
    pipe_name = '{} Chiller Bypass'.format(condenser_water_loop.nameString())
    chiller_bypass_pipe.setName(pipe_name)
    condenser_water_loop.addDemandBranchForComponent(chiller_bypass_pipe)

    supply_outlet_pipe = openstudio_model.PipeAdiabatic(model)
    supply_outlet_pipe.setName('{} Supply Outlet'.format(condenser_water_loop.nameString()))
    supply_outlet_pipe.addToNode(condenser_water_loop.supplyOutletNode())

    demand_inlet_pipe = openstudio_model.PipeAdiabatic(model)
    demand_inlet_pipe.setName('{} Demand Inlet'.format(condenser_water_loop.nameString()))
    demand_inlet_pipe.addToNode(condenser_water_loop.demandInletNode())

    demand_outlet_pipe = openstudio_model.PipeAdiabatic(model)
    demand_outlet_pipe.setName('{} Demand Outlet'.format(condenser_water_loop.nameString()))
    demand_outlet_pipe.addToNode(condenser_water_loop.demandOutletNode())

    return condenser_water_loop


def model_add_hp_loop(
        model, heating_fuel='NaturalGas', cooling_fuel='Electricity',
        cooling_type='EvaporativeFluidCooler', system_name='Heat Pump Loop',
        sup_wtr_high_temp=87.0, sup_wtr_low_temp=67.0,
        dsgn_sup_wtr_temp=102.2, dsgn_sup_wtr_temp_delt=19.8):
    """Creates a heat pump loop which has a boiler and fluid cooler.

    Args:
        model [OpenStudio::Model::Model] OpenStudio model object.
        heating_fuel: [String]
        cooling_fuel: [String] cooling fuel. Valid options are: Electricity,
            DistrictCooling.
        cooling_type: [String] cooling type if not DistrictCooling.
            Valid options are: CoolingTower, CoolingTowerSingleSpeed,
            CoolingTowerTwoSpeed, CoolingTowerVariableSpeed, FluidCooler,
            FluidCoolerSingleSpeed, FluidCoolerTwoSpeed, EvaporativeFluidCooler,
            EvaporativeFluidCoolerSingleSpeed, EvaporativeFluidCoolerTwoSpeed
        system_name: [String] the name of the system, or None in which case it
            will be defaulted
        sup_wtr_high_temp: [Double] target supply water temperature to enable
            cooling in degrees Fahrenheit, default 65.0F
        sup_wtr_low_temp: [Double] target supply water temperature to enable
            heating in degrees Fahrenheit, default 41.0F
        dsgn_sup_wtr_temp: [Double] design supply water temperature in degrees
            Fahrenheit, default 102.2F
        dsgn_sup_wtr_temp_delt: [Double] design supply-return water temperature
            difference in degrees Rankine, default 19.8R.

    Returns:
        [OpenStudio::Model::PlantLoop] the resulting plant loop.
    """
    # create heat pump loop
    heat_pump_water_loop = openstudio_model.PlantLoop(model)
    heat_pump_water_loop.setLoadDistributionScheme('SequentialLoad')
    if system_name is None:
        heat_pump_water_loop.setName('Heat Pump Loop')
    else:
        heat_pump_water_loop.setName(system_name)

    # hot water loop sizing and controls
    sup_wtr_high_temp = 87.0 if sup_wtr_high_temp is None else sup_wtr_high_temp
    sup_wtr_high_temp_c = TEMPERATURE.to_unit([sup_wtr_high_temp], 'C', 'F')[0]
    sup_wtr_low_temp = 67.0 if sup_wtr_low_temp is None else sup_wtr_low_temp
    sup_wtr_low_temp_c = TEMPERATURE.to_unit([sup_wtr_low_temp], 'C', 'F')[0]
    dsgn_sup_wtr_temp = 102.2 if dsgn_sup_wtr_temp is None else dsgn_sup_wtr_temp
    dsgn_sup_wtr_temp_c = TEMPERATURE.to_unit([dsgn_sup_wtr_temp], 'C', 'F')[0]
    dsgn_sup_wtr_temp_delt = 19.8 if dsgn_sup_wtr_temp_delt is None \
        else dsgn_sup_wtr_temp_delt
    dsgn_sup_wtr_temp_delt_k = TEMP_DELTA.to_unit([dsgn_sup_wtr_temp_delt], 'dC', 'dF')[0]

    sizing_plant = heat_pump_water_loop.sizingPlant()
    sizing_plant.setLoopType('Heating')
    heat_pump_water_loop.setMinimumLoopTemperature(10.0)
    heat_pump_water_loop.setMaximumLoopTemperature(35.0)
    sizing_plant.setDesignLoopExitTemperature(dsgn_sup_wtr_temp_c)
    sizing_plant.setLoopDesignTemperatureDifference(dsgn_sup_wtr_temp_delt_k)
    loop_name = heat_pump_water_loop.nameString()
    hp_high_temp_sch = create_constant_schedule_ruleset(
        model, sup_wtr_high_temp_c,
        name='{} High Temp - {}F'.format(loop_name, int(sup_wtr_high_temp)),
        schedule_type_limit='Temperature')
    hp_low_temp_sch = create_constant_schedule_ruleset(
        model, sup_wtr_low_temp_c,
        name='{} Low Temp - {}F'.format(loop_name, int(sup_wtr_low_temp)),
        schedule_type_limit='Temperature')
    hp_stpt_manager = openstudio_model.SetpointManagerScheduledDualSetpoint(model)
    hp_stpt_manager.setName('{} Scheduled Dual Setpoint'.format(loop_name))
    hp_stpt_manager.setHighSetpointSchedule(hp_high_temp_sch)
    hp_stpt_manager.setLowSetpointSchedule(hp_low_temp_sch)
    hp_stpt_manager.addToNode(heat_pump_water_loop.supplyOutletNode())

    # create pump
    hp_pump = openstudio_model.PumpConstantSpeed(model)
    hp_pump.setName('{} Pump'.format(loop_name))
    hp_pump.setRatedPumpHead(PRESSURE.to_unit([60.0 * 12], 'Pa', 'inH2O')[0])
    hp_pump.setPumpControlType('Intermittent')
    hp_pump.addToNode(heat_pump_water_loop.supplyInletNode())

    # add setpoint to cooling outlet so correct plant operation scheme is generated
    cooling_equipment_stpt_manager = \
        openstudio_model.SetpointManagerScheduledDualSetpoint(model)
    cooling_equipment_stpt_manager.setHighSetpointSchedule(hp_high_temp_sch)
    cooling_equipment_stpt_manager.setLowSetpointSchedule(hp_low_temp_sch)

    # create cooling equipment and add to the loop
    if cooling_fuel == 'DistrictCooling':
        cooling_equipment = openstudio_model.DistrictCooling(model)
        cooling_equipment.setName('{} District Cooling'.format(loop_name))
        cooling_equipment.autosizeNominalCapacity()
        heat_pump_water_loop.addSupplyBranchForComponent(cooling_equipment)
        cooling_equipment_stpt_manager.setName(
            '{} District Cooling Scheduled Dual Setpoint'.format(loop_name))
    else:
        if cooling_type in ('CoolingTower', 'CoolingTowerTwoSpeed'):
            cooling_equipment = openstudio_model.CoolingTowerTwoSpeed(model)
            cooling_equipment.setName('{} CoolingTowerTwoSpeed'.format(loop_name))
            heat_pump_water_loop.addSupplyBranchForComponent(cooling_equipment)
            cooling_equipment_stpt_manager.setName(
                '{} Cooling Tower Scheduled Dual Setpoint'.format(loop_name))
        elif cooling_type == 'CoolingTowerSingleSpeed':
            cooling_equipment = openstudio_model.CoolingTowerSingleSpeed(model)
            cooling_equipment.setName('{} CoolingTowerSingleSpeed'.format(loop_name))
            heat_pump_water_loop.addSupplyBranchForComponent(cooling_equipment)
            cooling_equipment_stpt_manager.setName(
                '{} Cooling Tower Scheduled Dual Setpoint'.format(loop_name))
        elif cooling_type == 'CoolingTowerVariableSpeed':
            cooling_equipment = openstudio_model.CoolingTowerVariableSpeed(model)
            cooling_equipment.setName('{} CoolingTowerVariableSpeed'.format(loop_name))
            heat_pump_water_loop.addSupplyBranchForComponent(cooling_equipment)
            cooling_equipment_stpt_manager.setName(
                '{} Cooling Tower Scheduled Dual Setpoint'.format(loop_name))
        elif cooling_type in ('FluidCooler', 'FluidCoolerSingleSpeed'):
            cooling_equipment = openstudio_model.FluidCoolerSingleSpeed(model)
            cooling_equipment.setName('{} FluidCoolerSingleSpeed'.format(loop_name))
            heat_pump_water_loop.addSupplyBranchForComponent(cooling_equipment)
            cooling_equipment_stpt_manager.setName(
                '{} Fluid Cooler Scheduled Dual Setpoint'.format(loop_name))
            # Remove hard coded default values
            cooling_equipment.setPerformanceInputMethod(
                'UFactorTimesAreaAndDesignWaterFlowRate')
            cooling_equipment.autosizeDesignWaterFlowRate()
            cooling_equipment.autosizeDesignAirFlowRate()
        elif cooling_type == 'FluidCoolerTwoSpeed':
            cooling_equipment = openstudio_model.FluidCoolerTwoSpeed(model)
            cooling_equipment.setName('{} FluidCoolerTwoSpeed'.format(loop_name))
            heat_pump_water_loop.addSupplyBranchForComponent(cooling_equipment)
            cooling_equipment_stpt_manager.setName(
                '{} Fluid Cooler Scheduled Dual Setpoint'.format(loop_name))
            # Remove hard coded default values
            cooling_equipment.setPerformanceInputMethod(
                'UFactorTimesAreaAndDesignWaterFlowRate')
            cooling_equipment.autosizeDesignWaterFlowRate()
            cooling_equipment.autosizeHighFanSpeedAirFlowRate()
            cooling_equipment.autosizeLowFanSpeedAirFlowRate()
        elif cooling_type in ('EvaporativeFluidCooler', 'EvaporativeFluidCoolerSingleSpeed'):
            cooling_equipment = openstudio_model.EvaporativeFluidCoolerSingleSpeed(model)
            cooling_equipment.setName(
                '{} EvaporativeFluidCoolerSingleSpeed'.format(loop_name))
            cooling_equipment.setDesignSprayWaterFlowRate(0.002208)  # Based on HighRiseApartment
            cooling_equipment.setPerformanceInputMethod(
                'UFactorTimesAreaAndDesignWaterFlowRate')
            heat_pump_water_loop.addSupplyBranchForComponent(cooling_equipment)
            cooling_equipment_stpt_manager.setName(
                '{} Fluid Cooler Scheduled Dual Setpoint'.format(loop_name))
        elif cooling_type == 'EvaporativeFluidCoolerTwoSpeed':
            cooling_equipment = openstudio_model.EvaporativeFluidCoolerTwoSpeed(model)
            cooling_equipment.setName('{} EvaporativeFluidCoolerTwoSpeed'.format(loop_name))
            cooling_equipment.setDesignSprayWaterFlowRate(0.002208)  # Based on HighRiseApartment
            cooling_equipment.setPerformanceInputMethod(
                'UFactorTimesAreaAndDesignWaterFlowRate')
            heat_pump_water_loop.addSupplyBranchForComponent(cooling_equipment)
            cooling_equipment_stpt_manager.setName(
                '{} Fluid Cooler Scheduled Dual Setpoint'.format(loop_name))
        else:
            msg = 'Cooling fuel type {} is not a valid option, no cooling ' \
                'equipment will be added.'.format(cooling_type)
            print(msg)
            return False
    equip_out_node = cooling_equipment.outletModelObject().get().to_Node().get()
    cooling_equipment_stpt_manager.addToNode(equip_out_node)

    # add setpoint to heating outlet so correct plant operation scheme is generated
    heating_equipment_stpt_manager = \
        openstudio_model.SetpointManagerScheduledDualSetpoint(model)
    heating_equipment_stpt_manager.setHighSetpointSchedule(hp_high_temp_sch)
    heating_equipment_stpt_manager.setLowSetpointSchedule(hp_low_temp_sch)

    # switch statement to handle district heating name change
    if model.version() < openstudio.VersionString('3.7.0'):
        if heating_fuel == 'DistrictHeatingWater' or \
                heating_fuel == 'DistrictHeatingSteam':
            heating_fuel = 'DistrictHeating'
    else:
        if heating_fuel == 'DistrictHeating':
            heating_fuel = 'DistrictHeatingWater'

    # create heating equipment and add to the loop
    if heating_fuel == 'DistrictHeating':
        heating_equipment = openstudio_model.DistrictHeating(model)
        heating_equipment.setName('{} District Heating'.format(loop_name))
        heating_equipment.autosizeNominalCapacity()
        heat_pump_water_loop.addSupplyBranchForComponent(heating_equipment)
        heating_equipment_stpt_manager.setName(
            '{} District Heating Scheduled Dual Setpoint'.format(loop_name))
    elif heating_fuel == 'DistrictHeatingWater':
        heating_equipment = openstudio_model.DistrictHeatingWater(model)
        heating_equipment.setName('{} District Heating'.format(loop_name))
        heating_equipment.autosizeNominalCapacity()
        heat_pump_water_loop.addSupplyBranchForComponent(heating_equipment)
        heating_equipment_stpt_manager.setName(
            '{} District Heating Scheduled Dual Setpoint'.format(loop_name))
    elif heating_fuel == 'DistrictHeatingSteam':
        heating_equipment = openstudio_model.DistrictHeatingSteam(model)
        heating_equipment.setName('{} District Heating'.format(loop_name))
        heating_equipment.autosizeNominalCapacity()
        heat_pump_water_loop.addSupplyBranchForComponent(heating_equipment)
        heating_equipment_stpt_manager.setName(
            '{} District Heating Scheduled Dual Setpoint'.format(loop_name))
    elif heating_fuel in ('AirSourceHeatPump', 'ASHP'):
        heating_equipment = create_central_air_source_heat_pump(
            model, heat_pump_water_loop)
        heating_equipment_stpt_manager.setName(
            '{} ASHP Scheduled Dual Setpoint'.format(loop_name))
    elif heating_fuel in ('Electricity', 'Gas', 'NaturalGas', 'Propane',
                          'PropaneGas', 'FuelOilNo1', 'FuelOilNo2'):
        heating_equipment = create_boiler_hot_water(
            model, hot_water_loop=heat_pump_water_loop,
            name='{} Supplemental Boiler'.format(loop_name), fuel_type=heating_fuel,
            flow_mode='ConstantFlow',
            lvg_temp_dsgn_f=86.0, min_plr=0.0, max_plr=1.2, opt_plr=1.0)
        heating_equipment_stpt_manager.setName(
            '{} Boiler Scheduled Dual Setpoint'.format(loop_name))
    else:
        print('Boiler fuel type {} is not valid, no heating equipment '
              'will be added.'.format(heating_fuel))
        return False
    equip_out_node = heating_equipment.outletModelObject().get().to_Node().get()
    heating_equipment_stpt_manager.addToNode(equip_out_node)

    # add heat pump water loop pipes
    supply_bypass_pipe = openstudio_model.PipeAdiabatic(model)
    supply_bypass_pipe.setName('{} Supply Bypass'.format(loop_name))
    heat_pump_water_loop.addSupplyBranchForComponent(supply_bypass_pipe)

    demand_bypass_pipe = openstudio_model.PipeAdiabatic(model)
    demand_bypass_pipe.setName('{} Demand Bypass'.format(loop_name))
    heat_pump_water_loop.addDemandBranchForComponent(demand_bypass_pipe)

    supply_outlet_pipe = openstudio_model.PipeAdiabatic(model)
    supply_outlet_pipe.setName('{} Supply Outlet'.format(loop_name))
    supply_outlet_pipe.addToNode(heat_pump_water_loop.supplyOutletNode)

    demand_inlet_pipe = openstudio_model.PipeAdiabatic(model)
    demand_inlet_pipe.setName('{} Demand Inlet'.format(loop_name))
    demand_inlet_pipe.addToNode(heat_pump_water_loop.demandInletNode)

    demand_outlet_pipe = openstudio_model.PipeAdiabatic(model)
    demand_outlet_pipe.setName('{} Demand Outlet'.format(loop_name))
    demand_outlet_pipe.addToNode(heat_pump_water_loop.demandOutletNode)

    return heat_pump_water_loop


def model_add_ground_hx_loop(model, system_name='Ground HX Loop'):
    """Creates loop that roughly mimics a properly sized ground heat exchanger.

    Args:
        model: [OpenStudio::Model::Model] OpenStudio model object
        system_name: [String] the name of the system, or None in which case
            it will be defaulted.

    Returns:
        [OpenStudio::Model::PlantLoop] the resulting plant loop.
    """
    # create ground hx loop
    ground_hx_loop = openstudio_model.PlantLoop(model)
    system_name = 'Ground HX Loop' if system_name is None else system_name
    ground_hx_loop.setName(system_name)
    loop_name = ground_hx_loop.nameString()

    # ground hx loop sizing and controls
    ground_hx_loop.setMinimumLoopTemperature(5.0)
    ground_hx_loop.setMaximumLoopTemperature(80.0)
    # temp change at high and low entering condition
    delta_t_k = TEMP_DELTA.to_unit([12.0], 'dC', 'dF')[0]
    # low entering condition
    min_inlet_c = TEMPERATURE.to_unit([30.0], 'C', 'F')[0]
    # high entering condition
    max_inlet_c = TEMPERATURE.to_unit([90.0], 'C', 'F')[0]

    # calculate the linear formula that defines outlet temperature
    # based on inlet temperature of the ground hx
    min_outlet_c = min_inlet_c + delta_t_k
    max_outlet_c = max_inlet_c - delta_t_k
    slope_c_per_c = (max_outlet_c - min_outlet_c) / (max_inlet_c - min_inlet_c)
    intercept_c = min_outlet_c - (slope_c_per_c * min_inlet_c)

    sizing_plant = ground_hx_loop.sizingPlant
    sizing_plant.setLoopType('Heating')
    sizing_plant.setDesignLoopExitTemperature(max_outlet_c)
    sizing_plant.setLoopDesignTemperatureDifference(delta_t_k)

    # create pump
    pump = openstudio_model.PumpConstantSpeed(model)
    pump.setName('{} Pump'.format(loop_name))
    pump.setRatedPumpHead(PRESSURE.to_unit([60.0 * 12], 'Pa', 'inH2O')[0])
    pump.setPumpControlType('Intermittent')
    pump.addToNode(ground_hx_loop.supplyInletNode())

    # use EMS and a PlantComponentTemperatureSource
    # to mimic the operation of the ground heat exchanger

    # schedule to actuate ground HX outlet temperature
    hx_temp_sch = openstudio_model.ScheduleConstant(model)
    hx_temp_sch.setName('Ground HX Temp Sch')
    hx_temp_sch.setValue(24.0)

    ground_hx = openstudio_model.PlantComponentTemperatureSource(model)
    ground_hx.setName('Ground HX')
    ground_hx.setTemperatureSpecificationType('Scheduled')
    ground_hx.setSourceTemperatureSchedule(hx_temp_sch)
    ground_hx_loop.addSupplyBranchForComponent(ground_hx)

    hx_stpt_manager = openstudio_model.SetpointManagerScheduled(model, hx_temp_sch)
    hx_stpt_manager.setName('{} Supply Outlet Setpoint'.format(ground_hx.nameString()))
    hx_stpt_manager.addToNode(ground_hx.outletModelObject().get().to_Node().get())

    loop_stpt_manager = openstudio_model.SetpointManagerScheduled(model, hx_temp_sch)
    loop_stpt_manager.setName('{} Supply Outlet Setpoint'.format(ground_hx_loop.nameString()))
    loop_stpt_manager.addToNode(ground_hx_loop.supplyOutletNode())

    # edit name to be EMS friendly
    ground_hx_ems_name = ems_friendly_name(ground_hx.nameString())

    # sensor to read supply inlet temperature
    inlet_temp_sensor = openstudio_model.EnergyManagementSystemSensor(
        model, 'System Node Temperature')
    inlet_temp_sensor.setName('{} Inlet Temp Sensor'.format(ground_hx_ems_name))
    inlet_temp_sensor.setKeyName(ground_hx_loop.supplyInletNode().handle().to_s())

    # actuator to set supply outlet temperature
    outlet_temp_actuator = openstudio_model.EnergyManagementSystemActuator(
        hx_temp_sch, 'Schedule:Constant', 'Schedule Value')
    outlet_temp_actuator.setName('{} Outlet Temp Actuator'.format(ground_hx_ems_name))

    # program to control outlet temperature
    # adjusts delta-t based on calculation of slope and intercept from control temperatures
    program = openstudio_model.EnergyManagementSystemProgram(model)
    program.setName('{} Temperature Control'.format(ground_hx_ems_name))
    program_body = \
        'SET Tin = {inlet_temp_sensor_handle}\n' \
        'SET Tout = {slope_c_per_c} * Tin + {intercept_c}\n' \
        'SET {outlet_temp_actuator_handle} = Tout'.format(
            inlet_temp_sensor_handle=inlet_temp_sensor.handle(),
            slope_c_per_c=round(slope_c_per_c, 2), intercept_c=round(intercept_c, 2),
            outlet_temp_actuator_handle=outlet_temp_actuator.handle()
        )
    program.setBody(program_body)

    # program calling manager
    pcm = openstudio_model.EnergyManagementSystemProgramCallingManager(model)
    pcm.setName('{} Calling Manager'.format(program.nameString()))
    pcm.setCallingPoint('InsideHVACSystemIterationLoop')
    pcm.addProgram(program)

    return ground_hx_loop


def model_add_district_ambient_loop(model, system_name='Ambient Loop'):
    """Adds an ambient condenser water loop that represents a district system.

    It connects buildings as a shared sink/source for heat pumps.

    Args:
        model: [OpenStudio::Model::Model] OpenStudio model object.
        system_name: [String] the name of the system, or None in which case it
            will be defaulted.

    Returns:
        [OpenStudio::Model::PlantLoop] the ambient loop.
    """
    # create ambient loop
    ambient_loop = openstudio_model.PlantLoop(model)
    system_name = 'Ambient Loop' if system_name is None else system_name
    ambient_loop.setName(system_name)
    loop_name = ambient_loop.nameString()

    # ambient loop sizing and controls
    ambient_loop.setMinimumLoopTemperature(5.0)
    ambient_loop.setMaximumLoopTemperature(80.0)

    amb_high_temp_f = 90  # Supplemental cooling below 65F
    amb_low_temp_f = 41  # Supplemental heat below 41F
    amb_temp_sizing_f = 102.2  # CW sized to deliver 102.2F
    amb_delta_t_r = 19.8  # 19.8F delta-T
    amb_high_temp_c = TEMPERATURE.to_unit([amb_high_temp_f], 'C', 'F')[0]
    amb_low_temp_c = TEMPERATURE.to_unit([amb_low_temp_f], 'C', 'F')[0]
    amb_temp_sizing_c = TEMPERATURE.to_unit([amb_temp_sizing_f], 'C', 'F')[0]
    amb_delta_t_k = TEMP_DELTA.to_unit([amb_delta_t_r], 'dC', 'dF')[0]

    amb_high_temp_sch = create_constant_schedule_ruleset(
        model, amb_high_temp_c,
        name='Ambient Loop High Temp - {}F'.format(amb_high_temp_f),
        schedule_type_limit='Temperature')
    amb_low_temp_sch = create_constant_schedule_ruleset(
        model, amb_low_temp_c,
        name='Ambient Loop Low Temp - {}F'.format(amb_low_temp_f),
        schedule_type_limit='Temperature')

    amb_stpt_manager = openstudio_model.SetpointManagerScheduledDualSetpoint(model)
    amb_stpt_manager.setName('{} Supply Water Setpoint Manager'.format(loop_name))
    amb_stpt_manager.setHighSetpointSchedule(amb_high_temp_sch)
    amb_stpt_manager.setLowSetpointSchedule(amb_low_temp_sch)
    amb_stpt_manager.addToNode(ambient_loop.supplyOutletNode())

    sizing_plant = ambient_loop.sizingPlant()
    sizing_plant.setLoopType('Heating')
    sizing_plant.setDesignLoopExitTemperature(amb_temp_sizing_c)
    sizing_plant.setLoopDesignTemperatureDifference(amb_delta_t_k)

    # create pump
    pump = openstudio_model.PumpVariableSpeed(model)
    pump.setName('{} Pump'.format(loop_name))
    pump.setRatedPumpHead(PRESSURE.to_unit([60.0 * 12], 'Pa', 'inH2O')[0])
    pump.setPumpControlType('Intermittent')
    pump.addToNode(ambient_loop.supplyInletNode())

    # cooling
    district_cooling = openstudio_model.DistrictCooling(model)
    district_cooling.setNominalCapacity(1000000000000)  # large number; no autosizing
    ambient_loop.addSupplyBranchForComponent(district_cooling)

    # heating
    if model.version() < openstudio.VersionString('3.7.0'):
        district_heating = openstudio_model.DistrictHeating(model)
    else:
        district_heating = openstudio_model.DistrictHeatingWater(model)
    district_heating.setNominalCapacity(1000000000000)  # large number; no autosizing
    ambient_loop.addSupplyBranchForComponent(district_heating)

    # add ambient water loop pipes
    supply_bypass_pipe = openstudio_model.PipeAdiabatic(model)
    supply_bypass_pipe.setName('{} Supply Bypass'.format(loop_name))
    ambient_loop.addSupplyBranchForComponent(supply_bypass_pipe)

    demand_bypass_pipe = openstudio_model.PipeAdiabatic(model)
    demand_bypass_pipe.setName('{} Demand Bypass'.format(loop_name))
    ambient_loop.addDemandBranchForComponent(demand_bypass_pipe)

    supply_outlet_pipe = openstudio_model.PipeAdiabatic(model)
    supply_outlet_pipe.setName('{} Supply Outlet'.format(loop_name))
    supply_outlet_pipe.addToNode(ambient_loop.supplyOutletNode)

    demand_inlet_pipe = openstudio_model.PipeAdiabatic(model)
    demand_inlet_pipe.setName('{} Demand Inlet'.format(loop_name))
    demand_inlet_pipe.addToNode(ambient_loop.demandInletNode)

    demand_outlet_pipe = openstudio_model.PipeAdiabatic(model)
    demand_outlet_pipe.setName('{} Demand Outlet'.format(loop_name))
    demand_outlet_pipe.addToNode(ambient_loop.demandOutletNode)

    return ambient_loop


def model_add_doas_cold_supply(
        model, thermal_zones, system_name=None, hot_water_loop=None,
        chilled_water_loop=None, hvac_op_sch=None, min_oa_sch=None, min_frac_oa_sch=None,
        fan_maximum_flow_rate=None, econo_ctrl_mthd='FixedDryBulb',
        energy_recovery=False, doas_control_strategy='NeutralSupplyAir',
        clg_dsgn_sup_air_temp=55.0, htg_dsgn_sup_air_temp=60.0):
    """Creates a DOAS system with cold supply and terminal units for each zone.

    This is the default DOAS system for DOE prototype buildings.
    Use model_add_doas for other DOAS systems.

    Args:
        model: [OpenStudio::Model::Model] OpenStudio model object.
        thermal_zones: [Array<OpenStudio::Model::ThermalZone>] array of zones
            to connect to this system.
        system_name: [String] the name of the system, or None in which case it
            will be defaulted.
        hot_water_loop: [OpenStudio::Model::PlantLoop] hot water loop to connect
            to heating and zone fan coils.
        chilled_water_loop: [OpenStudio::Model::PlantLoop] chilled water loop to
            connect to cooling coil.
        hvac_op_sch: [String] name of the HVAC operation schedule, default is always on.
        min_oa_sch: [String] name of the minimum outdoor air schedule, default
            is always on.
        min_frac_oa_sch: [String] name of the minimum fraction of outdoor air
            schedule, default is always on.
        fan_maximum_flow_rate: [Double] fan maximum flow rate in cfm, default
            is autosize.
        econo_ctrl_mthd: [String] economizer control type, default is Fixed Dry Bulb.
        energy_recovery: [Boolean] if true, an ERV will be added to the system.
        doas_control_strategy: [String] DOAS control strategy.
        clg_dsgn_sup_air_temp: [Double] design cooling supply air temperature
            in degrees Fahrenheit, default 65F.
        htg_dsgn_sup_air_temp: [Double] design heating supply air temperature
            in degrees Fahrenheit, default 75F.

    Returns:
        [OpenStudio::Model::AirLoopHVAC] the resulting DOAS air loop.
    """
    # Check the total OA requirement for all zones on the system
    tot_oa_req = 0
    for zone in thermal_zones:
        tot_oa_req += thermal_zone_get_outdoor_airflow_rate(zone)
        if tot_oa_req > 0:
            break

    # If the total OA requirement is zero do not add the DOAS system
    # because the simulations will fail
    if tot_oa_req == 0:
        return False

    # create a DOAS air loop
    air_loop = openstudio_model.AirLoopHVAC(model)
    system_name = '{} Zone DOAS'.format(len(thermal_zones)) \
        if system_name is None else system_name
    air_loop.setName(system_name)
    loop_name = air_loop.nameString()

    # set availability schedule
    hvac_op_sch = model_add_schedule(model, hvac_op_sch)

    # DOAS design temperatures
    clg_dsgn_sup_air_temp = 55.0 if clg_dsgn_sup_air_temp is None \
        else clg_dsgn_sup_air_temp
    clg_dsgn_sup_air_temp_c = TEMPERATURE.to_unit([clg_dsgn_sup_air_temp], 'C', 'F')[0]
    htg_dsgn_sup_air_temp = 60.0 if htg_dsgn_sup_air_temp is None \
        else htg_dsgn_sup_air_temp
    htg_dsgn_sup_air_temp_c = TEMPERATURE.to_unit([htg_dsgn_sup_air_temp], 'C', 'F')[0]

    # modify system sizing properties
    sizing_system = air_loop.sizingSystem()
    sizing_system.setTypeofLoadtoSizeOn('VentilationRequirement')
    sizing_system.setAllOutdoorAirinCooling(True)
    sizing_system.setAllOutdoorAirinHeating(True)
    # set minimum airflow ratio to 1.0 to avoid under-sizing heating coil
    if model.version() < openstudio.VersionString('2.7.0'):
        sizing_system.setMinimumSystemAirFlowRatio(1.0)
    else:
        sizing_system.setCentralHeatingMaximumSystemAirFlowRatio(1.0)

    sizing_system.setSizingOption('Coincident')
    sizing_system.setCentralCoolingDesignSupplyAirTemperature(clg_dsgn_sup_air_temp_c)
    sizing_system.setCentralHeatingDesignSupplyAirTemperature(htg_dsgn_sup_air_temp_c)

    # create supply fan
    supply_fan = create_fan_by_name(
        model, 'Constant_DOAS_Fan', fan_name='DOAS Supply Fan',
        end_use_subcategory='DOAS Fans')
    supply_fan.setAvailabilitySchedule(model.alwaysOnDiscreteSchedule())
    if fan_maximum_flow_rate is not None:
        fan_max_fr = FLOW_RATE.to_unit([fan_maximum_flow_rate], 'm3/s', 'cfm')[0]
        supply_fan.setMaximumFlowRate(fan_max_fr)
    supply_fan.addToNode(air_loop.supplyInletNode())

    # create heating coil
    if hot_water_loop is None:
        # electric backup heating coil
        create_coil_heating_electric(model, air_loop_node=air_loop.supplyInletNode(),
                                     name='{} Backup Htg Coil'.format(loop_name))
        # heat pump coil
        create_coil_heating_dx_single_speed(model, air_loop_node=air_loop.supplyInletNode(),
                                            name='{} Htg Coil'.format(loop_name))
    else:
        create_coil_heating_water(
            model, hot_water_loop, air_loop_node=air_loop.supplyInletNode(),
            name='{} Htg Coil'.format(loop_name), controller_convergence_tolerance=0.0001)

    # create cooling coil
    if chilled_water_loop is None:
        create_coil_cooling_dx_two_speed(
            model, air_loop_node=air_loop.supplyInletNode(),
            name='{} 2spd DX Clg Coil'.format(loop_name), type='OS default')
    else:
        create_coil_cooling_water(
            model, chilled_water_loop, air_loop_node=air_loop.supplyInletNode(),
            name='{} Clg Coil'.format(loop_name))

    # minimum outdoor air schedule
    if min_oa_sch is None:
        min_oa_sch = model.alwaysOnDiscreteSchedule()
    else:
        min_oa_sch = model_add_schedule(model, min_oa_sch)

    # minimum outdoor air fraction schedule
    if min_frac_oa_sch is None:
        min_frac_oa_sch = model.alwaysOnDiscreteSchedule()
    else:
        min_frac_oa_sch = model_add_schedule(model, min_frac_oa_sch)

    # create controller outdoor air
    controller_oa = openstudio_model.ControllerOutdoorAir(model)
    controller_oa.setName('{} OA Controller'.format(loop_name))
    controller_oa.setEconomizerControlType(econo_ctrl_mthd)
    controller_oa.setMinimumLimitType('FixedMinimum')
    controller_oa.autosizeMinimumOutdoorAirFlowRate()
    controller_oa.setMinimumOutdoorAirSchedule(min_oa_sch)
    controller_oa.setMinimumFractionofOutdoorAirSchedule(min_frac_oa_sch)
    controller_oa.resetEconomizerMaximumLimitDryBulbTemperature()
    controller_oa.resetEconomizerMaximumLimitEnthalpy()
    controller_oa.resetMaximumFractionofOutdoorAirSchedule()
    controller_oa.resetEconomizerMinimumLimitDryBulbTemperature()
    controller_oa.setHeatRecoveryBypassControlType('BypassWhenWithinEconomizerLimits')

    # create outdoor air system
    oa_system = openstudio_model.AirLoopHVACOutdoorAirSystem(model, controller_oa)
    oa_system.setName('{} OA System'.format(loop_name))
    oa_system.addToNode(air_loop.supplyInletNode())

    # create a setpoint manager
    sat_oa_reset = openstudio_model.SetpointManagerOutdoorAirReset(model)
    sat_oa_reset.setName('{} SAT Reset'.format(loop_name))
    sat_oa_reset.setControlVariable('Temperature')
    sat_oa_reset.setSetpointatOutdoorLowTemperature(htg_dsgn_sup_air_temp_c)
    sat_oa_reset.setOutdoorLowTemperature(TEMPERATURE.to_unit([60.0], 'C', 'F')[0])
    sat_oa_reset.setSetpointatOutdoorHighTemperature(clg_dsgn_sup_air_temp_c)
    sat_oa_reset.setOutdoorHighTemperature(TEMPERATURE.to_unit([70.0], 'C', 'F')[0])
    sat_oa_reset.addToNode(air_loop.supplyOutletNode())

    # set air loop availability controls and night cycle manager, after oa system added
    air_loop.setAvailabilitySchedule(hvac_op_sch)
    air_loop.setNightCycleControlType('CycleOnAny')

    # add energy recovery if requested
    if energy_recovery:
        # Get the OA system and its outboard OA node
        oa_system = air_loop.airLoopHVACOutdoorAirSystem.get

        # create the ERV and set its properties
        erv = create_hx_air_to_air_sensible_and_latent(
            model, name='{} ERV HX'.format(loop_name),
            type="Rotary", economizer_lockout=True,
            sensible_heating_100_eff=0.76, sensible_heating_75_eff=0.81,
            latent_heating_100_eff=0.68, latent_heating_75_eff=0.73,
            sensible_cooling_100_eff=0.76, sensible_cooling_75_eff=0.81,
            latent_cooling_100_eff=0.68, latent_cooling_75_eff=0.73)
        erv.addToNode(oa_system.outboardOANode().get())

        # increase fan static pressure to account for ERV
        erv_pressure_rise = PRESSURE.to_unit([1.0], 'Pa', 'inH2O')[0]
        new_pressure_rise = supply_fan.pressureRise() + erv_pressure_rise
        supply_fan.setPressureRise(new_pressure_rise)

    # add thermal zones to airloop
    for zone in thermal_zones:
        # make an air terminal for the zone
        air_terminal = openstudio_model.AirTerminalSingleDuctUncontrolled(
            model, model.alwaysOnDiscreteSchedule())
        air_terminal.setName('{} Air Terminal'.format(zone.nameString()))

        # attach new terminal to the zone and to the airloop
        air_loop.multiAddBranchForZone(zone, air_terminal.to_HVACComponent().get())

        # DOAS sizing
        sizing_zone = zone.sizingZone()
        sizing_zone.setAccountforDedicatedOutdoorAirSystem(True)
        sizing_zone.setDedicatedOutdoorAirSystemControlStrategy('ColdSupplyAir')
        sizing_zone.setDedicatedOutdoorAirLowSetpointTemperatureforDesign(clg_dsgn_sup_air_temp_c)
        sizing_zone.setDedicatedOutdoorAirHighSetpointTemperatureforDesign(htg_dsgn_sup_air_temp_c)

    return air_loop


def model_add_doas(
        model, thermal_zones, system_name=None, doas_type='DOASCV',
        hot_water_loop=None, chilled_water_loop=None, hvac_op_sch=None,
        min_oa_sch=None, min_frac_oa_sch=None, fan_maximum_flow_rate=None,
        econo_ctrl_mthd='NoEconomizer', include_exhaust_fan=True,
        demand_control_ventilation=False, doas_control_strategy='NeutralSupplyAir',
        clg_dsgn_sup_air_temp=60.0, htg_dsgn_sup_air_temp=70.0):
    """Creates a DOAS system with terminal units for each zone.

    Args:
        model: [OpenStudio::Model::Model] OpenStudio model object.
        thermal_zones: [Array<OpenStudio::Model::ThermalZone>] array of zones
            to connect to this system.
        system_name: [String] the name of the system, or None in which case it
            will be defaulted.
        doas_type: [String] DOASCV or DOASVAV, determines whether the DOAS is
            operated at scheduled, constant flow rate, or airflow is variable to
            allow for economizing or demand controlled ventilation.
        doas_control_strategy: [String] DOAS control strategy.
        hot_water_loop: [OpenStudio::Model::PlantLoop] hot water loop to connect
            to heating and zone fan coils.
        chilled_water_loop: [OpenStudio::Model::PlantLoop] chilled water loop to
            connect to cooling coil.
        hvac_op_sch: [String] name of the HVAC operation schedule, default is
            always on.
        min_oa_sch: [String] name of the minimum outdoor air schedule, default is
            always on.
        min_frac_oa_sch: [String] name of the minimum fraction of outdoor air
            schedule, default is always on.
        fan_maximum_flow_rate: [Double] fan maximum flow rate in cfm, default
            is autosize.
        econo_ctrl_mthd: [String] economizer control type, default is Fixed Dry Bulb.
            If enabled, the DOAS will be sized for twice the ventilation minimum
            to allow economizing.
        include_exhaust_fan: [Boolean] if true, include an exhaust fan.
        clg_dsgn_sup_air_temp: [Double] design cooling supply air temperature in
            degrees Fahrenheit, default 65F.
        htg_dsgn_sup_air_temp: [Double] design heating supply air temperature in
            degrees Fahrenheit, default 75F.
    """
    # Check the total OA requirement for all zones on the system
    tot_oa_req = 0
    for zone in thermal_zones:
        tot_oa_req += thermal_zone_get_outdoor_airflow_rate(zone)
        if tot_oa_req > 0:
            break

    # If the total OA requirement is zero do not add the DOAS system
    # because the simulations will fail
    if tot_oa_req == 0:
        return False

    # create a DOAS air loop
    air_loop = openstudio_model.AirLoopHVAC(model)
    system_name = '{} Zone DOAS'.format(len(thermal_zones)) \
        if system_name is None else system_name
    air_loop.setName(system_name)
    loop_name = air_loop.nameString()

    # set availability schedule
    hvac_op_sch = model_add_schedule(model, hvac_op_sch)

    # DOAS design temperatures
    clg_dsgn_sup_air_temp = 60.0 if clg_dsgn_sup_air_temp is None \
        else clg_dsgn_sup_air_temp
    clg_dsgn_sup_air_temp_c = TEMPERATURE.to_unit([clg_dsgn_sup_air_temp], 'C', 'F')[0]
    htg_dsgn_sup_air_temp = 70.0 if htg_dsgn_sup_air_temp is None \
        else htg_dsgn_sup_air_temp
    htg_dsgn_sup_air_temp_c = TEMPERATURE.to_unit([htg_dsgn_sup_air_temp], 'C', 'F')[0]

    # modify system sizing properties
    sizing_system = air_loop.sizingSystem()
    sizing_system.setTypeofLoadtoSizeOn('VentilationRequirement')
    sizing_system.setAllOutdoorAirinCooling(True)
    sizing_system.setAllOutdoorAirinHeating(True)
    # set minimum airflow ratio to 1.0 to avoid under-sizing heating coil
    if model.version() < openstudio.VersionString('2.7.0'):
        sizing_system.setMinimumSystemAirFlowRatio(1.0)
    else:
        sizing_system.setCentralHeatingMaximumSystemAirFlowRatio(1.0)

    sizing_system.setSizingOption('Coincident')
    sizing_system.setCentralCoolingDesignSupplyAirTemperature(clg_dsgn_sup_air_temp_c)
    sizing_system.setCentralHeatingDesignSupplyAirTemperature(htg_dsgn_sup_air_temp_c)

    if doas_type == 'DOASCV':
        supply_fan = create_fan_by_name(model, 'Constant_DOAS_Fan',
                                        fan_name='DOAS Supply Fan',
                                        end_use_subcategory='DOAS Fans')
    else:  # DOASVAV
        supply_fan = create_fan_by_name(model, 'Variable_DOAS_Fan',
                                        fan_name='DOAS Supply Fan',
                                        end_use_subcategory='DOAS Fans')

    supply_fan.setAvailabilitySchedule(model.alwaysOnDiscreteSchedule())
    if fan_maximum_flow_rate is not None:
        fan_max_fr = FLOW_RATE.to_unit([fan_maximum_flow_rate], 'm3/s', 'cfm')[0]
        supply_fan.setMaximumFlowRate(fan_max_fr)
    supply_fan.addToNode(air_loop.supplyInletNode())

    # create heating coil
    if hot_water_loop is None:
        # electric backup heating coil
        create_coil_heating_electric(model, air_loop_node=air_loop.supplyInletNode(),
                                     name='{} Backup Htg Coil'.format(loop_name))
        # heat pump coil
        create_coil_heating_dx_single_speed(model, air_loop_node=air_loop.supplyInletNode(),
                                            name='{} Htg Coil'.format(loop_name))
    else:
        create_coil_heating_water(
            model, hot_water_loop, air_loop_node=air_loop.supplyInletNode(),
            name='{} Htg Coil'.format(loop_name),
            controller_convergence_tolerance=0.0001)

    # create cooling coil
    if chilled_water_loop is None:
        create_coil_cooling_dx_two_speed(
            model, air_loop_node=air_loop.supplyInletNode(),
            name='{} 2spd DX Clg Coil'.format(loop_name), type='OS default')
    else:
        create_coil_cooling_water(
            model, chilled_water_loop, air_loop_node=air_loop.supplyInletNode(),
            name='{} Clg Coil'.format(loop_name))

    # minimum outdoor air schedule
    if min_oa_sch is None:
        min_oa_sch = model_add_schedule(model, min_oa_sch)

    # minimum outdoor air fraction schedule
    if min_frac_oa_sch is None:
        min_frac_oa_sch = model.alwaysOnDiscreteSchedule()
    else:
        min_frac_oa_sch = model_add_schedule(model, min_frac_oa_sch)

    # create controller outdoor air
    controller_oa = openstudio_model.ControllerOutdoorAir(model)
    controller_oa.setName('{} Outdoor Air Controller'.format(loop_name))
    controller_oa.setEconomizerControlType(econo_ctrl_mthd)
    controller_oa.setMinimumLimitType('FixedMinimum')
    controller_oa.autosizeMinimumOutdoorAirFlowRate()
    controller_oa.setMinimumOutdoorAirSchedule(min_oa_sch)
    if min_oa_sch is not None:
        controller_oa.setMinimumFractionofOutdoorAirSchedule(min_frac_oa_sch)
    controller_oa.resetEconomizerMinimumLimitDryBulbTemperature()
    controller_oa.resetEconomizerMaximumLimitDryBulbTemperature()
    controller_oa.resetEconomizerMaximumLimitEnthalpy()
    controller_oa.resetMaximumFractionofOutdoorAirSchedule()
    controller_oa.setHeatRecoveryBypassControlType('BypassWhenWithinEconomizerLimits')
    controller_mech_vent = controller_oa.controllerMechanicalVentilation()
    controller_mech_vent.setName('{} Mechanical Ventilation Controller'.format(loop_name))
    if demand_control_ventilation:
        controller_mech_vent.setDemandControlledVentilation(True)
    controller_mech_vent.setSystemOutdoorAirMethod('ZoneSum')

    # create outdoor air system
    oa_system = openstudio_model.AirLoopHVACOutdoorAirSystem(model, controller_oa)
    oa_system.setName('{} OA System'.format(loop_name))
    oa_system.addToNode(air_loop.supplyInletNode())

    # create an exhaust fan
    if include_exhaust_fan:
        if doas_type == 'DOASCV':
            exhaust_fan = create_fan_by_name(model, 'Constant_DOAS_Fan',
                                             fan_name='DOAS Exhaust Fan',
                                             end_use_subcategory='DOAS Fans')
        else:  # 'DOASVAV'
            exhaust_fan = create_fan_by_name(model, 'Variable_DOAS_Fan',
                                             fan_name='DOAS Exhaust Fan',
                                             end_use_subcategory='DOAS Fans')
        # set pressure rise 1.0 inH2O lower than supply fan, 1.0 inH2O minimum
        in_h20 = PRESSURE.to_unit([1.0], 'Pa', 'inH2O')[0]
        exhaust_fan_pressure_rise = supply_fan.pressureRise() - in_h20
        if exhaust_fan_pressure_rise < in_h20:
            exhaust_fan_pressure_rise = in_h20
        exhaust_fan.setPressureRise(exhaust_fan_pressure_rise)
        exhaust_fan.addToNode(air_loop.supplyInletNode())

    # create a setpoint manager
    sat_oa_reset = openstudio_model.SetpointManagerOutdoorAirReset(model)
    sat_oa_reset.setName('{} SAT Reset'.format(loop_name))
    sat_oa_reset.setControlVariable('Temperature')
    sat_oa_reset.setSetpointatOutdoorLowTemperature(htg_dsgn_sup_air_temp_c)
    sat_oa_reset.setOutdoorLowTemperature(TEMPERATURE.to_unit([55.0], 'C', 'F')[0])
    sat_oa_reset.setSetpointatOutdoorHighTemperature(clg_dsgn_sup_air_temp_c)
    sat_oa_reset.setOutdoorHighTemperature(TEMPERATURE.to_unit([70.0], 'C', 'F')[0])
    sat_oa_reset.addToNode(air_loop.supplyOutletNode())

    # set air loop availability controls and night cycle manager, after oa system added
    air_loop.setAvailabilitySchedule(hvac_op_sch)
    air_loop.setNightCycleControlType('CycleOnAnyZoneFansOnly')

    # add thermal zones to airloop
    for zone in thermal_zones:
        # skip zones with no outdoor air flow rate
        if thermal_zone_get_outdoor_airflow_rate(zone) == 0:
            continue
        zone_name = zone.nameString()

        # make an air terminal for the zone
        if doas_type == 'DOASCV':
            air_terminal = openstudio_model.AirTerminalSingleDuctUncontrolled(
                model, model.alwaysOnDiscreteSchedule())
        elif doas_type == 'DOASVAVReheat':
            # Reheat coil
            if hot_water_loop is None:
                rht_coil = create_coil_heating_electric(
                    model, name='{} Electric Reheat Coil'.format(zone_name))
            else:
                rht_coil = create_coil_heating_water(
                    model, hot_water_loop, name='{} Reheat Coil'.format(zone_name))

            # VAV reheat terminal
            air_terminal = openstudio_model.AirTerminalSingleDuctVAVReheat(
                model, model.alwaysOnDiscreteSchedule(), rht_coil)
            if model.version() < openstudio.VersionString('3.0.1'):
                air_terminal.setZoneMinimumAirFlowMethod('Constant')
            else:
                air_terminal.setZoneMinimumAirFlowInputMethod('Constant')
            if demand_control_ventilation:
                air_terminal.setControlForOutdoorAir(True)
        else:  # DOASVAV
            air_terminal = openstudio_model.AirTerminalSingleDuctVAVNoReheat(
                model, model.alwaysOnDiscreteSchedule())
            if model.version() < openstudio.VersionString('3.0.1'):
                air_terminal.setZoneMinimumAirFlowMethod('Constant')
            else:
                air_terminal.setZoneMinimumAirFlowInputMethod('Constant')
            air_terminal.setConstantMinimumAirFlowFraction(0.1)
            if demand_control_ventilation:
                air_terminal.setControlForOutdoorAir(True)
        air_terminal.setName('{} Air Terminal'.format(zone_name))

        # attach new terminal to the zone and to the airloop
        air_loop.multiAddBranchForZone(zone, air_terminal.to_HVACComponent().get())

        # ensure the DOAS takes priority, so ventilation load is included when
        # treated by other zonal systems
        zone.setCoolingPriority(air_terminal.to_ModelObject().get(), 1)
        zone.setHeatingPriority(air_terminal.to_ModelObject().get(), 1)

        # set the cooling and heating fraction to zero so that if DCV is enabled,
        # the system will lower the ventilation rate rather than trying to meet
        # the heating or cooling load.
        if model.version() < openstudio.VersionString('2.8.0'):
            if demand_control_ventilation:
                msg = 'Unable to add DOAS with DCV to model because the ' \
                    'setSequentialCoolingFraction method is not available in ' \
                    'OpenStudio versions less than 2.8.0.'
                print(msg)
        else:
            zone.setSequentialCoolingFraction(air_terminal.to_ModelObject().get(), 0.0)
            zone.setSequentialHeatingFraction(air_terminal.to_ModelObject().get(), 0.0)
            # if economizing, override to meet cooling load first with doas supply
            if econo_ctrl_mthd != 'NoEconomizer':
                zone.setSequentialCoolingFraction(air_terminal.to_ModelObject().get(), 1.0)

        # DOAS sizing
        sizing_zone = zone.sizingZone()
        sizing_zone.setAccountforDedicatedOutdoorAirSystem(True)
        sizing_zone.setDedicatedOutdoorAirSystemControlStrategy(doas_control_strategy)
        sizing_zone.setDedicatedOutdoorAirLowSetpointTemperatureforDesign(clg_dsgn_sup_air_temp_c)
        sizing_zone.setDedicatedOutdoorAirHighSetpointTemperatureforDesign(htg_dsgn_sup_air_temp_c)

    return air_loop


def model_add_vav_reheat(
        model, thermal_zones, system_name=None, return_plenum=None, heating_type=None,
        reheat_type=None, hot_water_loop=None, chilled_water_loop=None,
        hvac_op_sch=None, oa_damper_sch=None,
        fan_efficiency=0.62, fan_motor_efficiency=0.9, fan_pressure_rise=4.0,
        min_sys_airflow_ratio=0.3, vav_sizing_option='Coincident', econo_ctrl_mthd=None):
    """Creates a VAV system and adds it to the model.

    Args:
        model: [OpenStudio::Model::Model] OpenStudio model object.
        thermal_zones: [Array<OpenStudio::Model::ThermalZone>] array of zones
            to connect to this system.
        system_name: [String] the name of the system, or None in which case it
            will be defaulted.
        return_plenum: [OpenStudio::Model::ThermalZone] the zone to attach as
            the supply plenum, or None, in which case no return plenum will be used.
        heating_type: [String] main heating coil fuel type. valid choices are
            NaturalGas, Gas, Electricity, HeatPump, DistrictHeating,
            DistrictHeatingWater, DistrictHeatingSteam, or None (defaults to NaturalGas).
        reheat_type: [String] valid options are NaturalGas, Gas, Electricity
            Water, None (no heat).
        hot_water_loop: [OpenStudio::Model::PlantLoop] hot water loop to connect
            heating and reheat coils to.
        chilled_water_loop: [OpenStudio::Model::PlantLoop] chilled water loop
            to connect cooling coil to.
        hvac_op_sch: [String] name of the HVAC operation schedule or None in
            which case will be defaulted to always on.
        oa_damper_sch: [String] name of the oa damper schedule, or None in
            which case will be defaulted to always open.
        fan_efficiency: [Double] fan total efficiency, including motor and impeller.
        fan_motor_efficiency: [Double] fan motor efficiency.
        fan_pressure_rise: [Double] fan pressure rise, inH2O.
        min_sys_airflow_ratio: [Double] minimum system airflow ratio.
        vav_sizing_option: [String] air system sizing option, Coincident or NonCoincident.
        econo_ctrl_mthd: [String] economizer control type.
    """
    # create air handler
    air_loop = openstudio_model.AirLoopHVAC(model)
    system_name = '{} Zone VAV'.format(len(thermal_zones)) \
        if system_name is None else system_name
    air_loop.setName(system_name)
    loop_name = air_loop.nameString()

    # set availability schedule
    hvac_op_sch = model_add_schedule(model, hvac_op_sch)

    # oa damper schedule
    if oa_damper_sch is not None:
        oa_damper_sch = model_add_schedule(model, oa_damper_sch)

    # default design temperatures and settings used across all air loops
    dsgn_temps = standard_design_sizing_temperatures()
    sizing_system = adjust_sizing_system(air_loop, dsgn_temps)
    if min_sys_airflow_ratio is not None:
        if model.version() < openstudio.VersionString('2.7.0'):
            sizing_system.setMinimumSystemAirFlowRatio(min_sys_airflow_ratio)
        else:
            sizing_system.setCentralHeatingMaximumSystemAirFlowRatio(min_sys_airflow_ratio)
    if vav_sizing_option is not None:
        sizing_system.setSizingOption(vav_sizing_option)
    if hot_water_loop is not None:
        hw_temp_c = hot_water_loop.sizingPlant.designLoopExitTemperature()
        hw_delta_t_k = hot_water_loop.sizingPlant.loopDesignTemperatureDifference()

    # air handler controls
    sa_temp_sch = create_constant_schedule_ruleset(
        model, dsgn_temps['clg_dsgn_sup_air_temp_c'],
        name='Supply Air Temp - {}F'.format(dsgn_temps['clg_dsgn_sup_air_temp_f']),
        schedule_type_limit='Temperature')
    sa_stpt_manager = openstudio_model.SetpointManagerScheduled(model, sa_temp_sch)
    sa_stpt_manager.setName('{} Supply Air Setpoint Manager'.format(loop_name))
    sa_stpt_manager.addToNode(air_loop.supplyOutletNode())

    # create fan
    fan = create_fan_by_name(
        model, 'VAV_System_Fan', fan_name='{} Fan'.format(loop_name),
        fan_efficiency=fan_efficiency, pressure_rise=fan_pressure_rise,
        motor_efficiency=fan_motor_efficiency, end_use_subcategory='VAV System Fans')
    fan.setAvailabilitySchedule(model.alwaysOnDiscreteSchedule)
    fan.addToNode(air_loop.supplyInletNode)

    # create heating coil
    if hot_water_loop is None:
        if heating_type == 'Electricity':
            create_coil_heating_electric(
                model, air_loop_node=air_loop.supplyInletNode(),
                name='{} Main Electric Htg Coil'.format(loop_name))
        else:  # default to NaturalGas
            create_coil_heating_gas(
                model, air_loop_node=air_loop.supplyInletNode(),
                name='{} Main Gas Htg Coil'.format(loop_name))
    else:
        create_coil_heating_water(
            model, hot_water_loop, air_loop_node=air_loop.supplyInletNode(),
            name='{} Main Htg Coil'.format(loop_name),
            rated_inlet_water_temperature=hw_temp_c,
            rated_outlet_water_temperature=hw_temp_c - hw_delta_t_k,
            rated_inlet_air_temperature=dsgn_temps['prehtg_dsgn_sup_air_temp_c'],
            rated_outlet_air_temperature=dsgn_temps['htg_dsgn_sup_air_temp_c'])

    # create cooling coil
    if chilled_water_loop is None:
        create_coil_cooling_dx_two_speed(model, air_loop_node=air_loop.supplyInletNode(),
                                         name='{} 2spd DX Clg Coil'.format(loop_name),
                                         type='OS default')
    else:
        create_coil_cooling_water(model, chilled_water_loop,
                                  air_loop_node=air_loop.supplyInletNode(),
                                  name='{} Clg Coil'.format(loop_name))

    # outdoor air intake system
    oa_intake_controller = openstudio_model.ControllerOutdoorAir(model)
    oa_intake_controller.setName('{} OA Controller'.format(loop_name))
    oa_intake_controller.setMinimumLimitType('FixedMinimum')
    oa_intake_controller.autosizeMinimumOutdoorAirFlowRate()
    oa_intake_controller.resetMaximumFractionofOutdoorAirSchedule()
    oa_intake_controller.resetEconomizerMinimumLimitDryBulbTemperature()
    if econo_ctrl_mthd is not None:
        oa_intake_controller.setEconomizerControlType(econo_ctrl_mthd)
    if oa_damper_sch is not None:
        oa_intake_controller.setMinimumOutdoorAirSchedule(oa_damper_sch)
    controller_mv = oa_intake_controller.controllerMechanicalVentilation()
    controller_mv.setName('{} Vent Controller'.format(loop_name))
    controller_mv.setSystemOutdoorAirMethod('ZoneSum')
    oa_intake = openstudio_model.AirLoopHVACOutdoorAirSystem(model, oa_intake_controller)
    oa_intake.setName('{} OA System'.format(loop_name))
    oa_intake.addToNode(air_loop.supplyInletNode())

    # set air loop availability controls and night cycle manager, after oa system added
    air_loop.setAvailabilitySchedule(hvac_op_sch)
    air_loop.setNightCycleControlType('CycleOnAny')

    if model.version() < openstudio.VersionString('3.5.0'):
        avail_mgr = air_loop.availabilityManager()
        if avail_mgr.is_initialized():
            avail_mgr = avail_mgr.get()
        else:
            avail_mgr = None
    else:
        avail_mgr = air_loop.availabilityManagers()[0]

    if avail_mgr is not None and \
            avail_mgr.to_AvailabilityManagerNightCycle().is_initialized():
        avail_mgr = avail_mgr.to_AvailabilityManagerNightCycle().get()
        avail_mgr.setCyclingRunTime(1800)

    # hook the VAV system to each zone
    for zone in thermal_zones:
        # create reheat coil
        zone_name = zone.nameString()
        if reheat_type in ('NaturalGas', 'Gas'):
            rht_coil = create_coil_heating_gas(
                model, name='{} Gas Reheat Coil'.format(zone_name))
        elif reheat_type == 'Electricity':
            rht_coil = create_coil_heating_electric(
                model, name='{} Electric Reheat Coil'.format(zone_name))
        elif reheat_type == 'Water':
            rht_coil = create_coil_heating_water(
                model, hot_water_loop, name='{} Reheat Coil'.format(zone_name),
                rated_inlet_water_temperature=hw_temp_c,
                rated_outlet_water_temperature=(hw_temp_c - hw_delta_t_k),
                rated_inlet_air_temperature=dsgn_temps['htg_dsgn_sup_air_temp_c'],
                rated_outlet_air_temperature=dsgn_temps['zn_htg_dsgn_sup_air_temp_c'])
        else:
            pass  # no reheat

        # set zone reheat temperatures depending on reheat
        if reheat_type in ('NaturalGas', 'Gas', 'Electricity', 'Water'):
            # create vav terminal
            terminal = openstudio_model.AirTerminalSingleDuctVAVReheat(
                model, model.alwaysOnDiscreteSchedule(), rht_coil)
            terminal.setName('{} VAV Terminal'.format(zone_name))
            if model.version() < openstudio.VersionString('3.0.1'):
                terminal.setZoneMinimumAirFlowMethod('Constant')
            else:
                terminal.setZoneMinimumAirFlowInputMethod('Constant')
            # default to single maximum control logic
            terminal.setDamperHeatingAction('Normal')
            terminal.setMaximumReheatAirTemperature(
                dsgn_temps['zn_htg_dsgn_sup_air_temp_c'])
            air_loop.multiAddBranchForZone(zone, terminal.to_HVACComponent().get())
            # air_terminal_single_duct_vav_reheat_apply_initial_prototype_damper_position
            min_damper_position = 0.3
            terminal.setConstantMinimumAirFlowFraction(min_damper_position)
            # zone sizing
            sizing_zone = zone.sizingZone()
            sizing_zone.setCoolingDesignAirFlowMethod('DesignDayWithLimit')
            sizing_zone.setHeatingDesignAirFlowMethod('DesignDay')
            sizing_zone.setZoneCoolingDesignSupplyAirTemperature(
                dsgn_temps['zn_clg_dsgn_sup_air_temp_c'])
            sizing_zone.setZoneHeatingDesignSupplyAirTemperature(
                dsgn_temps['zn_htg_dsgn_sup_air_temp_c'])
        else:  # no reheat
            # create vav terminal
            terminal = openstudio_model.AirTerminalSingleDuctVAVNoReheat(
                model, model.alwaysOnDiscreteSchedule())
            terminal.setName('{} VAV Terminal'.format(zone_name))
            if model.version() < openstudio.VersionString('3.0.1'):
                terminal.setZoneMinimumAirFlowMethod('Constant')
            else:
                terminal.setZoneMinimumAirFlowInputMethod('Constant')
            air_loop.multiAddBranchForZone(zone, terminal.to_HVACComponent().get())
            # air_terminal_single_duct_vav_reheat_apply_initial_prototype_damper_position
            min_damper_position = 0.3
            terminal.setConstantMinimumAirFlowFraction(min_damper_position)
            # zone sizing
            sizing_zone = zone.sizingZone()
            sizing_zone.setCoolingDesignAirFlowMethod('DesignDayWithLimit')
            sizing_zone.setZoneCoolingDesignSupplyAirTemperature(
                dsgn_temps['zn_clg_dsgn_sup_air_temp_c'])
        if return_plenum is not None:
            zone.setReturnPlenum(return_plenum)

    return air_loop


def model_add_vav_pfp_boxes(
        model, thermal_zones, system_name=None, chilled_water_loop=None,
        hvac_op_sch=None, oa_damper_sch=None,
        fan_efficiency=0.62, fan_motor_efficiency=0.9, fan_pressure_rise=4.0):
    """Creates a VAV system with parallel fan powered boxes and adds it to the model.

    Args:
        model: [OpenStudio::Model::Model] OpenStudio model object.
        thermal_zones: [Array<OpenStudio::Model::ThermalZone>] array of zones to
            connect to this system.
        system_name: [String] the name of the system, or None in which case it
            will be defaulted.
        chilled_water_loop: [OpenStudio::Model::PlantLoop] chilled water loop to
            connect to the cooling coil.
        hvac_op_sch: [String] name of the HVAC operation schedule or None in which
            case will be defaulted to always on.
        oa_damper_sch: [String] name of the oa damper schedule or None in which
            case will be defaulted to always open.
        fan_efficiency: [Double] fan total efficiency, including motor and impeller.
        fan_motor_efficiency: [Double] fan motor efficiency.
        fan_pressure_rise: [Double] fan pressure rise, inH2O.
    """
    # create air handler
    air_loop = openstudio_model.AirLoopHVAC(model)
    system_name = '{} Zone VAV with PFP Boxes and Reheat'.format(len(thermal_zones)) \
        if system_name is None else system_name
    air_loop.setName(system_name)
    loop_name = air_loop.nameString()

    # hvac operation schedule
    hvac_op_sch = model_add_schedule(model, hvac_op_sch)

    # oa damper schedule
    oa_damper_sch = model_add_schedule(model, oa_damper_sch)

    # default design temperatures and settings used across all air loops
    dsgn_temps = standard_design_sizing_temperatures()
    adjust_sizing_system(air_loop, dsgn_temps)

    # air handler controls
    sa_temp_sch = create_constant_schedule_ruleset(
        model, dsgn_temps['clg_dsgn_sup_air_temp_c'],
        name='Supply Air Temp - {}F'.format(dsgn_temps['clg_dsgn_sup_air_temp_f']),
        schedule_type_limit='Temperature')
    sa_stpt_manager = openstudio_model.SetpointManagerScheduled(model, sa_temp_sch)
    sa_stpt_manager.setName('{} Supply Air Setpoint Manager'.format(loop_name))
    sa_stpt_manager.addToNode(air_loop.supplyOutletNode())

    # create fan
    fan = create_fan_by_name(
        model, 'VAV_System_Fan', fan_name='{} Fan'.format(loop_name),
        fan_efficiency=fan_efficiency, pressure_rise=fan_pressure_rise,
        motor_efficiency=fan_motor_efficiency, end_use_subcategory='VAV System Fans')
    fan.setAvailabilitySchedule(model.alwaysOnDiscreteSchedule())
    fan.addToNode(air_loop.supplyInletNode())

    # create heating coil
    create_coil_heating_electric(
        model, air_loop_node=air_loop.supplyInletNode(),
        name='{} Htg Coil'.format(loop_name))

    # create cooling coil
    create_coil_cooling_water(
        model, chilled_water_loop, air_loop_node=air_loop.supplyInletNode(),
        name='{} Clg Coil'.format(loop_name))

    # create outdoor air intake system
    oa_intake_controller = openstudio_model.ControllerOutdoorAir(model)
    oa_intake_controller.setName('{} OA Controller'.format(loop_name))
    oa_intake_controller.setMinimumLimitType('FixedMinimum')
    oa_intake_controller.autosizeMinimumOutdoorAirFlowRate()
    oa_intake_controller.resetEconomizerMinimumLimitDryBulbTemperature()
    controller_mv = oa_intake_controller.controllerMechanicalVentilation()
    controller_mv.setName('{} Vent Controller'.format(loop_name))
    controller_mv.setSystemOutdoorAirMethod('ZoneSum')
    oa_intake = openstudio_model.AirLoopHVACOutdoorAirSystem(model, oa_intake_controller)
    oa_intake.setName('{} OA System'.format(loop_name))
    oa_intake.addToNode(air_loop.supplyInletNode())

    # set air loop availability controls and night cycle manager, after oa system added
    air_loop.setAvailabilitySchedule(hvac_op_sch)
    air_loop.setNightCycleControlType('CycleOnAny')

    # attach the VAV system to each zone
    for zone in thermal_zones:
        # create reheat coil
        zone_name = zone.nameString()
        rht_coil = create_coil_heating_electric(
            model, name='{} Electric Reheat Coil'.format(zone_name))

        # create terminal fan
        pfp_fan = create_fan_by_name(
            model, 'PFP_Fan', fan_name='{} PFP Term Fan'.format(zone_name))
        pfp_fan.setAvailabilitySchedule(model.alwaysOnDiscreteSchedule())

        # create parallel fan powered terminal
        pfp_terminal = openstudio_model.AirTerminalSingleDuctParallelPIUReheat(
            model, model.alwaysOnDiscreteSchedule(), pfp_fan, rht_coil)
        pfp_terminal.setName('{} PFP Term'.format(zone_name))
        air_loop.multiAddBranchForZone(zone, pfp_terminal.to_HVACComponent().get())

        # zone sizing
        sizing_zone = zone.sizingZone()
        sizing_zone.setCoolingDesignAirFlowMethod('DesignDay')
        sizing_zone.setHeatingDesignAirFlowMethod('DesignDay')
        sizing_zone.setZoneCoolingDesignSupplyAirTemperature(
            dsgn_temps['zn_clg_dsgn_sup_air_temp_c'])
        sizing_zone.setZoneHeatingDesignSupplyAirTemperature(
            dsgn_temps['zn_htg_dsgn_sup_air_temp_c'])

    return air_loop


def model_add_pvav(
        model, thermal_zones, system_name=None, return_plenum=None,
        hot_water_loop=None, chilled_water_loop=None, heating_type=None,
        electric_reheat=False, hvac_op_sch=None, oa_damper_sch=None,
        econo_ctrl_mthd=None):
    """Creates a packaged VAV system and adds it to the model.

    Args:
        model: [OpenStudio::Model::Model] OpenStudio model object.
        thermal_zones: [Array<OpenStudio::Model::ThermalZone>] array of zones to
            connect to this system.
        system_name: [String] the name of the system, or None in which case it
            will be defaulted.
        return_plenum: [OpenStudio::Model::ThermalZone] the zone to attach as
            the supply plenum, or None, in which case no return plenum will be used.
        hot_water_loop: [OpenStudio::Model::PlantLoop] hot water loop to connect
            heating and reheat coils to. If None, will be electric heat and electric reheat.
        chilled_water_loop: [OpenStudio::Model::PlantLoop] chilled water loop
            to connect cooling coils to. If None, will be DX cooling.
        heating_type: [String] main heating coil fuel type. Valid choices are
            NaturalGas, Electricity, Water, or None (defaults to NaturalGas).
        electric_reheat: [Boolean] if true electric reheat coils, if false the
            reheat coils served by hot_water_loop.
        hvac_op_sch: [String] name of the HVAC operation schedule or None in
            which case will be defaulted to always on.
        oa_damper_sch: [String] name of the oa damper schedule or None in which
            case will be defaulted to always open.
        econo_ctrl_mthd: [String] economizer control type.
    """
    # create air handler
    air_loop = openstudio_model.AirLoopHVAC(model)
    system_name = '{} Zone PVAV'.format(len(thermal_zones)) \
        if system_name is None else system_name
    air_loop.setName(system_name)
    loop_name = air_loop.nameString()

    # hvac operation schedule
    hvac_op_sch = model_add_schedule(model, hvac_op_sch)

    # oa damper schedule
    oa_damper_sch = model_add_schedule(model, oa_damper_sch)

    # default design temperatures used across all air loops
    dsgn_temps = standard_design_sizing_temperatures()
    if hot_water_loop is not None:
        hw_temp_c = hot_water_loop.sizingPlant().designLoopExitTemperature()
        hw_delta_t_k = hot_water_loop.sizingPlant().loopDesignTemperatureDifference()

    # adjusted zone design heating temperature for pvav unless it would cause
    # a temperature higher than reheat water supply temperature
    if hot_water_loop is not None and hw_temp_c < TEMPERATURE.to_unit([140.0], 'C', 'F')[0]:
        dsgn_temps['zn_htg_dsgn_sup_air_temp_f'] = 122.0
        dsgn_temps['zn_htg_dsgn_sup_air_temp_c'] = \
            TEMPERATURE.to_unit([dsgn_temps['zn_htg_dsgn_sup_air_temp_f']], 'C', 'F')[0]

    # default design settings used across all air loops
    adjust_sizing_system(air_loop, dsgn_temps)

    # air handler controls
    sa_temp_sch = create_constant_schedule_ruleset(
        model, dsgn_temps['clg_dsgn_sup_air_temp_c'],
        name='Supply Air Temp - {}F'.format(dsgn_temps['clg_dsgn_sup_air_temp_f']),
        schedule_type_limit='Temperature')
    sa_stpt_manager = openstudio_model.SetpointManagerScheduled(model, sa_temp_sch)
    sa_stpt_manager.setName('{} Supply Air Setpoint Manager'.format(loop_name))
    sa_stpt_manager.addToNode(air_loop.supplyOutletNode())

    # create fan
    fan = create_fan_by_name(model, 'VAV_default', fan_name='{} Fan'.format(loop_name))
    fan.setAvailabilitySchedule(model.alwaysOnDiscreteSchedule())
    fan.addToNode(air_loop.supplyInletNode())

    # create heating coil
    if hot_water_loop is None:
        if heating_type == 'Electricity':
            create_coil_heating_electric(
                model, air_loop_node=air_loop.supplyInletNode(),
                name='{} Main Electric Htg Coil'.format(loop_name))
        else:  # default to NaturalGas
            create_coil_heating_gas(
                model, air_loop_node=air_loop.supplyInletNode(),
                name='{} Main Gas Htg Coil'.format(loop_name))
    else:
        create_coil_heating_water(
            model, hot_water_loop, air_loop_node=air_loop.supplyInletNode(),
            name='{} Main Htg Coil'.format(loop_name),
            rated_inlet_water_temperature=hw_temp_c,
            rated_outlet_water_temperature=hw_temp_c - hw_delta_t_k,
            rated_inlet_air_temperature=dsgn_temps['prehtg_dsgn_sup_air_temp_c'],
            rated_outlet_air_temperature=dsgn_temps['htg_dsgn_sup_air_temp_c'])

    # create cooling coil
    if chilled_water_loop is None:
        create_coil_cooling_dx_two_speed(
            model, air_loop_node=air_loop.supplyInletNode(),
            name='{} 2spd DX Clg Coil'.format(loop_name), type='OS default')
    else:
        create_coil_cooling_water(
            model, chilled_water_loop, air_loop_node=air_loop.supplyInletNode(),
            name='{} Clg Coil'.format(loop_name))

    # outdoor air intake system
    oa_intake_controller = openstudio_model.ControllerOutdoorAir(model)
    oa_intake_controller.setName('{} OA Controller'.format(loop_name))
    oa_intake_controller.setMinimumLimitType('FixedMinimum')
    oa_intake_controller.autosizeMinimumOutdoorAirFlowRate()
    oa_intake_controller.resetMaximumFractionofOutdoorAirSchedule()
    oa_intake_controller.resetEconomizerMinimumLimitDryBulbTemperature()
    if econo_ctrl_mthd is not None:
        oa_intake_controller.setEconomizerControlType(econo_ctrl_mthd)
    if oa_damper_sch is not None:
        oa_intake_controller.setMinimumOutdoorAirSchedule(oa_damper_sch)
    controller_mv = oa_intake_controller.controllerMechanicalVentilation()
    controller_mv.setName('{} Mechanical Ventilation Controller'.format(loop_name))
    controller_mv.setSystemOutdoorAirMethod('ZoneSum')
    oa_intake = openstudio_model.AirLoopHVACOutdoorAirSystem(model, oa_intake_controller)
    oa_intake.setName('{} OA System'.format(loop_name))
    oa_intake.addToNode(air_loop.supplyInletNode())

    # set air loop availability controls and night cycle manager, after oa system added
    air_loop.setAvailabilitySchedule(hvac_op_sch)
    air_loop.setNightCycleControlType('CycleOnAny')

    if model.version() < openstudio.VersionString('3.5.0'):
        avail_mgr = air_loop.availabilityManager()
        if avail_mgr.is_initialized():
            avail_mgr = avail_mgr.get()
        else:
            avail_mgr = None
    else:
        avail_mgr = air_loop.availabilityManagers()[0]

    if avail_mgr is not None and \
            avail_mgr.to_AvailabilityManagerNightCycle().is_initialized():
        avail_mgr = avail_mgr.to_AvailabilityManagerNightCycle().get()
        avail_mgr.setCyclingRunTime(1800)

    # attach the VAV system to each zone
    for zone in thermal_zones:
        zone_name = zone.nameString()
        # create reheat coil
        if electric_reheat or hot_water_loop is None:
            rht_coil = create_coil_heating_electric(
                model, name='{} Electric Reheat Coil'.format(zone_name))
        else:
            rht_coil = create_coil_heating_water(
                model, hot_water_loop, name='{} Reheat Coil'.format(zone_name),
                rated_inlet_water_temperature=hw_temp_c,
                rated_outlet_water_temperature=hw_temp_c - hw_delta_t_k,
                rated_inlet_air_temperature=dsgn_temps['htg_dsgn_sup_air_temp_c'],
                rated_outlet_air_temperature=dsgn_temps['zn_htg_dsgn_sup_air_temp_c'])

        # create VAV terminal
        terminal = openstudio_model.AirTerminalSingleDuctVAVReheat(
            model, model.alwaysOnDiscreteSchedule(), rht_coil)
        terminal.setName('{} VAV Terminal'.format(zone_name))
        if model.version() < openstudio.VersionString('3.0.1'):
            terminal.setZoneMinimumAirFlowMethod('Constant')
        else:
            terminal.setZoneMinimumAirFlowInputMethod('Constant')
        # default to single maximum control logic
        terminal.setDamperHeatingAction('Normal')
        terminal.setMaximumReheatAirTemperature(dsgn_temps['zn_htg_dsgn_sup_air_temp_c'])
        air_loop.multiAddBranchForZone(zone, terminal.to_HVACComponent().get())
        # air_terminal_single_duct_vav_reheat_apply_initial_prototype_damper_position
        min_damper_position = 0.3
        terminal.setConstantMinimumAirFlowFraction(min_damper_position)
        if return_plenum is not None:
            zone.setReturnPlenum(return_plenum)
        # zone sizing
        sizing_zone = zone.sizingZone()
        sizing_zone.setZoneCoolingDesignSupplyAirTemperature(
            dsgn_temps['zn_clg_dsgn_sup_air_temp_c'])
        sizing_zone.setZoneHeatingDesignSupplyAirTemperature(
            dsgn_temps['zn_htg_dsgn_sup_air_temp_c'])

    return air_loop


def model_add_pvav_pfp_boxes(
        model, thermal_zones, system_name=None, chilled_water_loop=None,
        hvac_op_sch=None, oa_damper_sch=None,
        fan_efficiency=0.62, fan_motor_efficiency=0.9, fan_pressure_rise=4.0):
    """Creates a packaged VAV system with parallel fan powered boxes.

    Args:
        model: [OpenStudio::Model::Model] OpenStudio model object.
        thermal_zones: [Array<OpenStudio::Model::ThermalZone>] array of zones to
            connect to this system.
        system_name: [String] the name of the system, or None in which case it
            will be defaulted.
        chilled_water_loop: [OpenStudio::Model::PlantLoop] chilled water loop
            to connect cooling coils to. If None, will be DX cooling.
        hvac_op_sch: [String] name of the HVAC operation schedule or None in
            which case will be defaulted to always on.
        oa_damper_sch: [String] name of the oa damper schedule or None in
            which case will be defaulted to always open.
        fan_efficiency: [Double] fan total efficiency, including motor and impeller.
        fan_motor_efficiency: [Double] fan motor efficiency.
        fan_pressure_rise: [Double] fan pressure rise, inH2O.
    """
    # create air handler
    air_loop = openstudio_model.AirLoopHVAC(model)
    system_name = '{} Zone PVAV with PFP Boxes and Reheat'.format(len(thermal_zones)) \
        if system_name is None else system_name
    air_loop.setName(system_name)
    loop_name = air_loop.nameString()

    # hvac operation schedule
    hvac_op_sch = model_add_schedule(model, hvac_op_sch)

    # oa damper schedule
    oa_damper_sch = model_add_schedule(model, oa_damper_sch)

    # default design temperatures and settings used across all air loops
    dsgn_temps = standard_design_sizing_temperatures()
    adjust_sizing_system(air_loop, dsgn_temps)

    # air handler controls
    sa_temp_sch = create_constant_schedule_ruleset(
        model, dsgn_temps['clg_dsgn_sup_air_temp_c'],
        name='Supply Air Temp - {}F'.format(dsgn_temps['clg_dsgn_sup_air_temp_f']),
        schedule_type_limit='Temperature')
    sa_stpt_manager = openstudio_model.SetpointManagerScheduled(model, sa_temp_sch)
    sa_stpt_manager.setName('{} Supply Air Setpoint Manager'.format(loop_name))
    sa_stpt_manager.addToNode(air_loop.supplyOutletNode())

    # create fan
    fan = create_fan_by_name(
        model, 'VAV_System_Fan', fan_name='{} Fan'.format(loop_name),
        fan_efficiency=fan_efficiency, pressure_rise=fan_pressure_rise,
        motor_efficiency=fan_motor_efficiency, end_use_subcategory='VAV System Fans')
    fan.setAvailabilitySchedule(model.alwaysOnDiscreteSchedule())
    fan.addToNode(air_loop.supplyInletNode())

    # create heating coil
    create_coil_heating_electric(
        model, air_loop_node=air_loop.supplyInletNode(),
        name='{} Main Htg Coil'.format(loop_name))

    # create cooling coil
    if chilled_water_loop is None:
        create_coil_cooling_dx_two_speed(
            model, air_loop_node=air_loop.supplyInletNode(),
            name='{} 2spd DX Clg Coil'.format(loop_name), type='OS default')
    else:
        create_coil_cooling_water(
            model, chilled_water_loop, air_loop_node=air_loop.supplyInletNode(),
            name='{} Clg Coil'.format(loop_name))

    # create outdoor air intake system
    oa_intake_controller = openstudio_model.ControllerOutdoorAir(model)
    oa_intake_controller.setName('{} OA Controller'.format(loop_name))
    oa_intake_controller.setMinimumLimitType('FixedMinimum')
    oa_intake_controller.autosizeMinimumOutdoorAirFlowRate()
    oa_intake_controller.setMinimumOutdoorAirSchedule(oa_damper_sch)
    oa_intake_controller.resetEconomizerMinimumLimitDryBulbTemperature()
    controller_mv = oa_intake_controller.controllerMechanicalVentilation()
    controller_mv.setName('{} Vent Controller'.format(loop_name))
    controller_mv.setSystemOutdoorAirMethod('ZoneSum')

    oa_intake = openstudio_model.AirLoopHVACOutdoorAirSystem(model, oa_intake_controller)
    oa_intake.setName('{} OA System'.format(loop_name))
    oa_intake.addToNode(air_loop.supplyInletNode())

    # set air loop availability controls and night cycle manager, after oa system added
    air_loop.setAvailabilitySchedule(hvac_op_sch)
    air_loop.setNightCycleControlType('CycleOnAny')

    # attach the VAV system to each zone
    for zone in thermal_zones:
        zone_name = zone.nameString()
        # create electric reheat coil
        rht_coil = create_coil_heating_electric(
            model, name='{} Electric Reheat Coil'.format(zone_name))

        # create terminal fan
        pfp_fan = create_fan_by_name(model, 'PFP_Fan',
                                     fan_name='{} PFP Term Fan'.format(zone_name))
        pfp_fan.setAvailabilitySchedule(model.alwaysOnDiscreteSchedule())

        # parallel fan powered terminal
        pfp_terminal = openstudio_model.AirTerminalSingleDuctParallelPIUReheat(
            model, model.alwaysOnDiscreteSchedule(), pfp_fan, rht_coil)
        pfp_terminal.setName("#{zone.name} PFP Term")
        air_loop.multiAddBranchForZone(zone, pfp_terminal.to_HVACComponent().get())

        # adjust zone sizing
        sizing_zone = zone.sizingZone()
        sizing_zone.setCoolingDesignAirFlowMethod('DesignDay')
        sizing_zone.setHeatingDesignAirFlowMethod('DesignDay')
        sizing_zone.setZoneCoolingDesignSupplyAirTemperature(
            dsgn_temps['zn_clg_dsgn_sup_air_temp_c'])
        sizing_zone.setZoneHeatingDesignSupplyAirTemperature(
            dsgn_temps['zn_htg_dsgn_sup_air_temp_c'])

    return air_loop


def model_add_psz_ac(
        model, thermal_zones, system_name=None, cooling_type='Single Speed DX AC',
        chilled_water_loop=None, hot_water_loop=None, heating_type=None,
        supplemental_heating_type=None, fan_location='DrawThrough',
        fan_type='ConstantVolume', hvac_op_sch=None, oa_damper_sch=None):
    """Creates a PSZ-AC system for each zone and adds it to the model.

    Args:
        model: [OpenStudio::Model::Model] OpenStudio model object.
        thermal_zones: [Array<OpenStudio::Model::ThermalZone>] array of zones
            to connect to this system.
        system_name: [String] the name of the system, or None in which case it
            will be defaulted.
        cooling_type: [String] valid choices are Water, Two Speed DX AC,
            Single Speed DX AC, Single Speed Heat Pump, Water To Air Heat Pump.
        chilled_water_loop: [OpenStudio::Model::PlantLoop] chilled water loop
            to connect cooling coil to, or None.
        hot_water_loop: [OpenStudio::Model::PlantLoop] hot water loop to
            connect heating coil to, or None.
        heating_type: [String] valid choices are NaturalGas, Electricity,
            Water, Single Speed Heat Pump, Water To Air Heat Pump, or None (no heat).
        supplemental_heating_type: [String] valid choices are Electricity,
            NaturalGas, None (no heat).
        fan_location: [String] valid choices are BlowThrough, DrawThrough.
        fan_type: [String] valid choices are ConstantVolume, Cycling.
        hvac_op_sch: [String] name of the HVAC operation schedule or None in
            which case will be defaulted to always on.
        oa_damper_sch: [String] name of the oa damper schedule or None in
            which case will be defaulted to always open.
    """
    # hvac operation schedule
    hvac_op_sch = model_add_schedule(model, hvac_op_sch)

    # oa damper schedule
    oa_damper_sch = model_add_schedule(model, oa_damper_sch)

    # create a PSZ-AC for each zone
    air_loops = []
    for zone in thermal_zones:
        zone_name = zone.nameString()
        air_loop = openstudio_model.AirLoopHVAC(model)
        system_name = '{} PSZ-AC'.format(zone_name) \
            if system_name is None else '{} {}'.format(zone_name, system_name)
        air_loop.setName(system_name)
        loop_name = air_loop.nameString()

        # default design temperatures and settings used across all air loops
        dsgn_temps = standard_design_sizing_temperatures()
        if hot_water_loop is not None:
            hw_temp_c = hot_water_loop.sizingPlant().designLoopExitTemperature()
            hw_delta_t_k = hot_water_loop.sizingPlant().loopDesignTemperatureDifference()

        # adjusted design heating temperature for psz_ac
        dsgn_temps['zn_htg_dsgn_sup_air_temp_f'] = 122.0
        dsgn_temps['zn_htg_dsgn_sup_air_temp_c'] = \
            TEMPERATURE.to_unit([dsgn_temps['zn_htg_dsgn_sup_air_temp_f']], 'C', 'F')[0]
        dsgn_temps['htg_dsgn_sup_air_temp_f'] = dsgn_temps['zn_htg_dsgn_sup_air_temp_f']
        dsgn_temps['htg_dsgn_sup_air_temp_c'] = dsgn_temps['zn_htg_dsgn_sup_air_temp_c']

        # default design settings used across all air loops
        adjust_sizing_system(air_loop, dsgn_temps, min_sys_airflow_ratio=1.0)

        # air handler controls
        # add a setpoint manager single zone reheat to control the supply air temperature
        setpoint_mgr_single_zone_reheat = \
            openstudio_model.SetpointManagerSingleZoneReheat(model)
        setpoint_mgr_single_zone_reheat.setName(
            '{} Setpoint Manager SZ Reheat'.format(zone_name))
        setpoint_mgr_single_zone_reheat.setControlZone(zone)
        setpoint_mgr_single_zone_reheat.setMinimumSupplyAirTemperature(
            dsgn_temps['zn_clg_dsgn_sup_air_temp_c'])
        setpoint_mgr_single_zone_reheat.setMaximumSupplyAirTemperature(
            dsgn_temps['zn_htg_dsgn_sup_air_temp_c'])
        setpoint_mgr_single_zone_reheat.addToNode(air_loop.supplyOutletNode())

        # zone sizing
        sizing_zone = zone.sizingZone()
        sizing_zone.setZoneCoolingDesignSupplyAirTemperature(
            dsgn_temps['zn_clg_dsgn_sup_air_temp_c'])
        sizing_zone.setZoneHeatingDesignSupplyAirTemperature(
            dsgn_temps['zn_htg_dsgn_sup_air_temp_c'])

        # create heating coil
        if heating_type in ('NaturalGas', 'Gas'):
            htg_coil = create_coil_heating_gas(
                model, name='{} Gas Htg Coil'.format(loop_name))
        elif heating_type == 'Water':
            if hot_water_loop is None:
                print('No hot water plant loop supplied')
                return False
            htg_coil = create_coil_heating_water(
                model, hot_water_loop, name='{} Water Htg Coil'.format(loop_name),
                rated_inlet_water_temperature=hw_temp_c,
                rated_outlet_water_temperature=hw_temp_c - hw_delta_t_k,
                rated_inlet_air_temperature=dsgn_temps['prehtg_dsgn_sup_air_temp_c'],
                rated_outlet_air_temperature=dsgn_temps['htg_dsgn_sup_air_temp_c'])
        elif heating_type == 'Single Speed Heat Pump':
            htg_coil = create_coil_heating_dx_single_speed(
                model, name='{} HP Htg Coil'.format(zone_name), type='PSZ-AC', cop=3.3)
        elif heating_type == 'Water To Air Heat Pump':
            htg_coil = create_coil_heating_water_to_air_heat_pump_equation_fit(
                model, hot_water_loop,
                name='{} Water-to-Air HP Htg Coil'.format(loop_name))
        elif heating_type in ('Electricity', 'Electric'):
            htg_coil = create_coil_heating_electric(
                model, name='{} Electric Htg Coil'.format(loop_name))
        else:
            # zero-capacity, always-off electric heating coil
            htg_coil = create_coil_heating_electric(
                model, name='{} No Heat'.format(loop_name),
                schedule=model.alwaysOffDiscreteSchedule(),
                nominal_capacity=0.0)

        # create supplemental heating coil
        if supplemental_heating_type in ('Electricity', 'Electric'):
            supplemental_htg_coil = create_coil_heating_electric(
                model, name='{} Electric Backup Htg Coil'.format(loop_name))
        elif supplemental_heating_type in ('NaturalGas', 'Gas'):
            supplemental_htg_coil = create_coil_heating_gas(
                model, name='{} Gas Backup Htg Coil'.format(loop_name))
        else:  # Zero-capacity, always-off electric heating coil
            supplemental_htg_coil = create_coil_heating_electric(
                model, name='{} No Heat'.format(loop_name),
                schedule=model.alwaysOffDiscreteSchedule(), nominal_capacity=0.0)

        # create cooling coil
        if cooling_type == 'Water':
            if chilled_water_loop is None:
                print('No chilled water plant loop supplied')
                return False
            clg_coil = create_coil_cooling_water(
                model, chilled_water_loop, name='{} Water Clg Coil'.format(loop_name))
        elif cooling_type == 'Two Speed DX AC':
            clg_coil = create_coil_cooling_dx_two_speed(
                model, name='{} 2spd DX AC Clg Coil'.format(loop_name))
        elif cooling_type == 'Single Speed DX AC':
            clg_coil = create_coil_cooling_dx_single_speed(
                model, name='{} 1spd DX AC Clg Coil'.format(loop_name), type='PSZ-AC')
        elif cooling_type == 'Single Speed Heat Pump':
            clg_coil = create_coil_cooling_dx_single_speed(
                model, name='{} 1spd DX HP Clg Coil'.format(loop_name), type='Heat Pump')
        elif cooling_type == 'Water To Air Heat Pump':
            if chilled_water_loop is None:
                print('No chilled water plant loop supplied')
                return False
            clg_coil = create_coil_cooling_water_to_air_heat_pump_equation_fit(
                model, chilled_water_loop,
                name='{} Water-to-Air HP Clg Coil'.format(loop_name))
        else:
            clg_coil = None

        # Use a Fan:OnOff in the unitary system object
        if fan_type == 'Cycling':
            fan = create_fan_by_name(model, 'Packaged_RTU_SZ_AC_Cycling_Fan',
                                     fan_name='{} Fan'.format(loop_name))
        elif fan_type == 'ConstantVolume':
            fan = create_fan_by_name(model, 'Packaged_RTU_SZ_AC_CAV_OnOff_Fan',
                                     fan_name='{} Fan'.format(loop_name))
        else:
            print('Invalid fan_type')
            return False

        # fan location
        fan_location = 'DrawThrough' if fan_location is None else fan_location
        if fan_location not in ('DrawThrough', 'BlowThrough'):
            msg = 'Invalid fan_location {} for fan {}.'.format(
                fan_location, fan.nameString())
            print(msg)
            return False

        # construct unitary system object
        unitary_system = openstudio_model.AirLoopHVACUnitarySystem(model)
        if fan is not None:
            unitary_system.setSupplyFan(fan)
        if htg_coil is not None:
            unitary_system.setHeatingCoil(htg_coil)
        if clg_coil is not None:
            unitary_system.setCoolingCoil(clg_coil)
        if supplemental_htg_coil is not None:
            unitary_system.setSupplementalHeatingCoil(supplemental_htg_coil)
        unitary_system.setControllingZoneorThermostatLocation(zone)
        unitary_system.setFanPlacement(fan_location)
        unitary_system.addToNode(air_loop.supplyInletNode())

        # added logic and naming for heat pumps
        if heating_type == 'Water To Air Heat Pump':
            unitary_system.setMaximumOutdoorDryBulbTemperatureforSupplementalHeaterOperation(
                TEMPERATURE.to_unit([40.0], 'C', 'F')[0])
            unitary_system.setName('{} Unitary HP'.format(loop_name))
            unitary_system.setMaximumSupplyAirTemperature(
                dsgn_temps['zn_htg_dsgn_sup_air_temp_c'])
            if model.version() < openstudio.VersionString('3.7.0'):
                unitary_system.setSupplyAirFlowRateMethodDuringCoolingOperation(
                    'SupplyAirFlowRate')
                unitary_system.setSupplyAirFlowRateMethodDuringHeatingOperation(
                    'SupplyAirFlowRate')
                unitary_system.setSupplyAirFlowRateMethodWhenNoCoolingorHeatingisRequired(
                    'SupplyAirFlowRate')
            else:
                unitary_system.autosizeSupplyAirFlowRateDuringCoolingOperation()
                unitary_system.autosizeSupplyAirFlowRateDuringHeatingOperation()
                unitary_system.autosizeSupplyAirFlowRateWhenNoCoolingorHeatingisRequired()
        elif heating_type == 'Single Speed Heat Pump':
            unitary_system.setMaximumOutdoorDryBulbTemperatureforSupplementalHeaterOperation(
                TEMPERATURE.to_unit([40.0], 'C', 'F')[0])
            unitary_system.setName('{} Unitary HP'.format(loop_name))
        else:
            unitary_system.setName('{} Unitary AC'.format(loop_name))

        # specify control logic
        unitary_system.setAvailabilitySchedule(hvac_op_sch)
        if fan_type == 'Cycling':
            unitary_system.setSupplyAirFanOperatingModeSchedule(
                model.alwaysOffDiscreteSchedule())
        else:  # constant volume operation
            unitary_system.setSupplyAirFanOperatingModeSchedule(hvac_op_sch)

        # add the OA system
        oa_controller = openstudio_model.ControllerOutdoorAir(model)
        oa_controller.setName('{} OA System Controller'.format(loop_name))
        oa_controller.setMinimumOutdoorAirSchedule(oa_damper_sch)
        oa_controller.autosizeMinimumOutdoorAirFlowRate()
        oa_controller.resetEconomizerMinimumLimitDryBulbTemperature()
        oa_system = openstudio_model.AirLoopHVACOutdoorAirSystem(model, oa_controller)
        oa_system.setName('{} OA System'.format(loop_name))
        oa_system.addToNode(air_loop.supplyInletNode())

        # set air loop availability controls and night cycle manager, after oa system added
        air_loop.setAvailabilitySchedule(hvac_op_sch)
        air_loop.setNightCycleControlType('CycleOnAny')

        if model.version() < openstudio.VersionString('3.5.0'):
            avail_mgr = air_loop.availabilityManager()
            avail_mgr = avail_mgr.get() if avail_mgr.is_initialized() else None
        else:
            avail_mgr = air_loop.availabilityManagers()[0]

        if avail_mgr is not None and \
                avail_mgr.to_AvailabilityManagerNightCycle().is_initialized():
            avail_mgr = avail_mgr.to_AvailabilityManagerNightCycle().get()
            avail_mgr.setCyclingRunTime(1800)

        # create a diffuser and attach the zone/diffuser pair to the air loop
        diffuser = openstudio_model.AirTerminalSingleDuctUncontrolled(
            model, model.alwaysOnDiscreteSchedule)
        diffuser.setName('{} Diffuser'.format(loop_name))
        air_loop.multiAddBranchForZone(zone, diffuser.to_HVACComponent().get())
        air_loops.append(air_loop)

    return air_loops


def model_add_psz_vav(
        model, thermal_zones, system_name=None, heating_type=None,
        cooling_type='AirCooled', supplemental_heating_type=None, hvac_op_sch=None,
        fan_type='VAV_System_Fan', oa_damper_sch=None, hot_water_loop=None,
        chilled_water_loop=None, minimum_volume_setpoint=None):
    """Creates a packaged single zone VAV system for each zone.

    Args:
        model: [OpenStudio::Model::Model] OpenStudio model object.
        thermal_zones: [Array<OpenStudio::Model::ThermalZone>] array of zones
            to connect to this system.
        system_name: [String] the name of the system, or None in which case it
            will be defaulted.
        heating_type: [String] valid choices are NaturalGas, Electricity, Water,
            None (no heat).
        supplemental_heating_type: [String] valid choices are Electricity,
            NaturalGas, None (no heat).
        hvac_op_sch: [String] name of the HVAC operation schedule or None in
            which case will be defaulted to always on.
        oa_damper_sch: [String] name of the oa damper schedule or None in which
            case will be defaulted to always open.
    """
    # hvac operation schedule
    hvac_op_sch = model_add_schedule(model, hvac_op_sch)

    # oa damper schedule
    oa_damper_sch = model_add_schedule(model, oa_damper_sch)

    # create a PSZ-AC for each zone
    air_loops = []
    for zone in thermal_zones:
        zone_name = zone.nameString()
        air_loop = openstudio_model.AirLoopHVAC(model)
        system_name = '{} PSZ-VAV'.format(zone_name) \
            if system_name is None else '{} {}'.format(zone_name, system_name)
        air_loop.setName(system_name)
        loop_name = air_loop.nameString()

        # default design temperatures used across all air loops
        dsgn_temps = standard_design_sizing_temperatures()

        # adjusted zone design heating temperature for psz_vav
        dsgn_temps['htg_dsgn_sup_air_temp_f'] = dsgn_temps['zn_htg_dsgn_sup_air_temp_f']
        dsgn_temps['htg_dsgn_sup_air_temp_c'] = dsgn_temps['zn_htg_dsgn_sup_air_temp_c']

        # default design settings used across all air loops
        adjust_sizing_system(air_loop, dsgn_temps)

        # air handler controls
        # add a setpoint manager single zone reheat to control the supply air temperature
        setpoint_mgr_single_zone_reheat = \
            openstudio_model.SetpointManagerSingleZoneReheat(model)
        setpoint_mgr_single_zone_reheat.setName(
            '{} Setpoint Manager SZ Reheat'.format(zone_name))
        setpoint_mgr_single_zone_reheat.setControlZone(zone)
        setpoint_mgr_single_zone_reheat.setMinimumSupplyAirTemperature(
            dsgn_temps['zn_clg_dsgn_sup_air_temp_c'])
        setpoint_mgr_single_zone_reheat.setMaximumSupplyAirTemperature(
            dsgn_temps['zn_htg_dsgn_sup_air_temp_c'])
        setpoint_mgr_single_zone_reheat.addToNode(air_loop.supplyOutletNode())

        # zone sizing
        sizing_zone = zone.sizingZone()
        sizing_zone.setZoneCoolingDesignSupplyAirTemperature(
            dsgn_temps['zn_clg_dsgn_sup_air_temp_c'])
        sizing_zone.setZoneHeatingDesignSupplyAirTemperature(
            dsgn_temps['zn_htg_dsgn_sup_air_temp_c'])

        # create fan
        fan = create_fan_by_name(model, fan_type, fan_name='{} Fan'.format(loop_name),
                                 end_use_subcategory='VAV System Fans')
        fan.setAvailabilitySchedule(hvac_op_sch)

        # create heating coil
        if heating_type in ('NaturalGas', 'Gas'):
            htg_coil = create_coil_heating_gas(
                model, name='{} Gas Htg Coil'.format(loop_name))
        elif heating_type in ('Electricity', 'Electric'):
            htg_coil = create_coil_heating_electric(
                model, name='{} Electric Htg Coil'.format(loop_name))
        elif heating_type == 'Water':
            htg_coil = create_coil_heating_water(
                model, hot_water_loop, name='{} Water Htg Coil'.format(loop_name))
        else:  # Zero-capacity, always-off electric heating coil
            htg_coil = create_coil_heating_electric(
                model, name='{} No Heat'.format(loop_name),
                schedule=model.alwaysOffDiscreteSchedule(), nominal_capacity=0.0)

        # create supplemental heating coil
        if supplemental_heating_type in ('Electricity', 'Electric'):
            supplemental_htg_coil = create_coil_heating_electric(
                model, name='{} Electric Backup Htg Coil'.format(loop_name))
        elif supplemental_heating_type in ('NaturalGas', 'Gas'):
            supplemental_htg_coil = create_coil_heating_gas(
                model, name='{} Gas Backup Htg Coil'.format(loop_name))
        else:  # zero-capacity, always-off electric heating coil
            supplemental_htg_coil = create_coil_heating_electric(
                model, name='{} No Backup Heat'.format(loop_name),
                schedule=model.alwaysOffDiscreteSchedule(), nominal_capacity=0.0)

        # create cooling coil
        if cooling_type == 'WaterCooled':
            clg_coil = create_coil_cooling_water(
                model, chilled_water_loop, name='{} Clg Coil'.format(loop_name))
        else:  # AirCooled
            clg_coil = openstudio_model.CoilCoolingDXVariableSpeed(model)
            clg_coil.setName('{} Var spd DX AC Clg Coil'.format(loop_name))
            clg_coil.setBasinHeaterCapacity(10.0)
            clg_coil.setBasinHeaterSetpointTemperature(2.0)
            # first speed level
            clg_spd_1 = openstudio_model.CoilCoolingDXVariableSpeedSpeedData(model)
            clg_coil.addSpeed(clg_spd_1)
            clg_coil.setNominalSpeedLevel(1)

        # wrap coils in a unitary system
        unitary_system = openstudio_model.AirLoopHVACUnitarySystem(model)
        unitary_system.setSupplyFan(fan)
        unitary_system.setHeatingCoil(htg_coil)
        unitary_system.setCoolingCoil(clg_coil)
        unitary_system.setSupplementalHeatingCoil(supplemental_htg_coil)
        unitary_system.setName('{} Unitary PSZ-VAV'.format(zone_name))
        # The following control strategy can lead to "Developer Error: Component sizing incomplete."
        # EnergyPlus severe (not fatal) errors if there is no heating design load
        unitary_system.setControlType('SingleZoneVAV')
        unitary_system.setControllingZoneorThermostatLocation(zone)
        unitary_system.setMaximumSupplyAirTemperature(dsgn_temps['zn_htg_dsgn_sup_air_temp_c'])
        unitary_system.setFanPlacement('BlowThrough')
        if model.version() < openstudio.VersionString('3.7.0'):
            unitary_system.setSupplyAirFlowRateMethodDuringCoolingOperation(
                'SupplyAirFlowRate')
            unitary_system.setSupplyAirFlowRateMethodDuringHeatingOperation(
                'SupplyAirFlowRate')
            if minimum_volume_setpoint is None:
                unitary_system.setSupplyAirFlowRateMethodWhenNoCoolingorHeatingisRequired(
                    'SupplyAirFlowRate')
            else:
                us = unitary_system
                us.setSupplyAirFlowRateMethodWhenNoCoolingorHeatingisRequired(
                    'FractionOfAutosizedCoolingValue')
                us.setFractionofAutosizedDesignCoolingSupplyAirFlowRateWhenNoCoolingorHeatingisRequired(
                    minimum_volume_setpoint)
        else:
            unitary_system.autosizeSupplyAirFlowRateDuringCoolingOperation()
            unitary_system.autosizeSupplyAirFlowRateDuringHeatingOperation()
            if minimum_volume_setpoint is None:
                unitary_system.autosizeSupplyAirFlowRateWhenNoCoolingorHeatingisRequired()
            else:
                us = unitary_system
                us.setFractionofAutosizedDesignCoolingSupplyAirFlowRateWhenNoCoolingorHeatingisRequired(
                    minimum_volume_setpoint)
        unitary_system.setSupplyAirFanOperatingModeSchedule(model.alwaysOnDiscreteSchedule())
        unitary_system.addToNode(air_loop.supplyInletNode())

        # create outdoor air system
        oa_controller = openstudio_model.ControllerOutdoorAir(model)
        oa_controller.setName('{} OA Sys Controller'.format(loop_name))
        oa_controller.setMinimumOutdoorAirSchedule(oa_damper_sch)
        oa_controller.autosizeMinimumOutdoorAirFlowRate()
        oa_controller.resetEconomizerMinimumLimitDryBulbTemperature()
        oa_controller.setHeatRecoveryBypassControlType('BypassWhenOAFlowGreaterThanMinimum')
        oa_system = openstudio_model.AirLoopHVACOutdoorAirSystem(model, oa_controller)
        oa_system.setName('{} OA System'.format(loop_name))
        oa_system.addToNode(air_loop.supplyInletNode())

        # set air loop availability controls and night cycle manager, after oa system added
        air_loop.setAvailabilitySchedule(hvac_op_sch)
        air_loop.setNightCycleControlType('CycleOnAny')

        # create a VAV no reheat terminal and attach the zone/terminal pair to the air loop
        diffuser = openstudio_model.AirTerminalSingleDuctVAVNoReheat(
            model, model.alwaysOnDiscreteSchedule())
        diffuser.setName('{} Diffuser'.format(loop_name))
        air_loop.multiAddBranchForZone(zone, diffuser.to_HVACComponent().get())
        air_loops.append(air_loop)

    return air_loops


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


def model_add_four_pipe_fan_coil(
        model, thermal_zones, chilled_water_loop, hot_water_loop=None,
        ventilation=False, capacity_control_method='CyclingFan'):
    """Adds four pipe fan coil units to each zone.

    Args:
        model: [OpenStudio::Model::Model] OpenStudio model object.
        thermal_zones: [Array<OpenStudio::Model::ThermalZone>] array of zones to
            add fan coil units.
        chilled_water_loop: [OpenStudio::Model::PlantLoop] the chilled water loop
            that serves the fan coils.
        hot_water_loop: [OpenStudio::Model::PlantLoop] the hot water loop that
            serves the fan coils. If None, a zero-capacity, electric heating
            coil set to Always-Off will be included in the unit.
        ventilation: [Boolean] If true, ventilation will be supplied through
            the unit. If false, no ventilation will be supplied through the unit,
            with the expectation that it will be provided by a DOAS or separate system.
        capacity_control_method: [String] Capacity control method for the fan coil.
            Options are ConstantFanVariableFlow, CyclingFan, VariableFanVariableFlow,
            and VariableFanConstantFlow.  If VariableFan, the fan will be VariableVolume.
    """
    # default design temperatures used across all air loops
    dsgn_temps = standard_design_sizing_temperatures()

    # make a fan coil unit for each zone
    fcus = []
    for zone in thermal_zones:
        zone_name = zone.nameString()
        sizing_zone = zone.sizingZone()
        sizing_zone.setZoneCoolingDesignSupplyAirTemperature(
            dsgn_temps['zn_clg_dsgn_sup_air_temp_c'])
        sizing_zone.setZoneHeatingDesignSupplyAirTemperature(
            dsgn_temps['zn_htg_dsgn_sup_air_temp_c'])

        if chilled_water_loop:
            fcu_clg_coil = create_coil_cooling_water(
                model, chilled_water_loop, name='{} FCU Cooling Coil'.format(zone_name))
        else:
            print('Fan coil units require a chilled water loop, but none was provided.')
            return False

        if hot_water_loop:
            fcu_htg_coil = create_coil_heating_water(
                model, hot_water_loop, name='{} FCU Heating Coil'.format(zone_name),
                rated_outlet_air_temperature=dsgn_temps['zn_htg_dsgn_sup_air_temp_c'])
        else:  # Zero-capacity, always-off electric heating coil
            fcu_htg_coil = create_coil_heating_electric(
                model, name='{} No Heat'.format(zone_name),
                schedule=model.alwaysOffDiscreteSchedule(), nominal_capacity=0.0)

        if capacity_control_method in ('VariableFanVariableFlow', 'VariableFanConstantFlow'):
            fcu_fan = create_fan_by_name(
                model, 'Fan_Coil_VarSpeed_Fan',
                fan_name='{} Fan Coil Variable Fan'.format(zone_name),
                end_use_subcategory='FCU Fans')
        else:
            fcu_fan = create_fan_by_name(
                model, 'Fan_Coil_Fan', fan_name='{} Fan Coil fan'.format(zone_name),
                end_use_subcategory='FCU Fans')
        fcu_fan.setAvailabilitySchedule(model.alwaysOnDiscreteSchedule())
        fcu_fan.autosizeMaximumFlowRate()

        fcu = openstudio_model.ZoneHVACFourPipeFanCoil(
            model, model.alwaysOnDiscreteSchedule(), fcu_fan, fcu_clg_coil, fcu_htg_coil)
        fcu.setName('{} FCU'.format(zone_name))
        fcu.setCapacityControlMethod(capacity_control_method)
        fcu.autosizeMaximumSupplyAirFlowRate()
        if not ventilation:
            fcu.setMaximumOutdoorAirFlowRate(0.0)
        fcu.addToThermalZone(zone)
        fcus.append(fcu)

    return fcus


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


def model_add_waterside_economizer(
        model, chilled_water_loop, condenser_water_loop, integrated=True):
    """Adds a waterside economizer to the chilled water and condenser loop.

    Args:
        model: [OpenStudio::Model::Model] OpenStudio model object.
        integrated [Boolean] when set to true, models an integrated waterside economizer.
            Integrated - in series with chillers, can run simultaneously with chillers
            Non-Integrated - in parallel with chillers, chillers locked out during operation
    """
    # make a new heat exchanger
    heat_exchanger = openstudio_model.HeatExchangerFluidToFluid(model)
    heat_exchanger.setHeatExchangeModelType('CounterFlow')
    # zero degree minimum necessary to allow both economizer and heat exchanger
    # to operate in both integrated and non-integrated archetypes
    # possibly results from an EnergyPlus issue that didn't get resolved correctly
    # https://github.com/NREL/EnergyPlus/issues/5626
    heat_exchanger.setMinimumTemperatureDifferencetoActivateHeatExchanger(0.0)
    heat_exchanger.setHeatTransferMeteringEndUseType('FreeCooling')
    o_min_tl = TEMPERATURE.to_unit([35.0], 'C', 'F')[0]
    heat_exchanger.setOperationMinimumTemperatureLimit(o_min_tl)
    o_max_tl = TEMPERATURE.to_unit([72.0], 'C', 'F')[0]
    heat_exchanger.setOperationMaximumTemperatureLimit(o_max_tl)
    heat_exchanger.setAvailabilitySchedule(model.alwaysOnDiscreteSchedule())

    # get the chillers on the chilled water loop
    chillers = chilled_water_loop.supplyComponents(
        'OS:Chiller:Electric:EIR'.to_IddObjectType())

    if integrated:
        if os_vector_len(chillers) == 0:
            msg = 'No chillers were found on {}; only modeling waterside economizer'.format(
                chilled_water_loop.nameString())
            print(msg)

        # set methods for integrated heat exchanger
        heat_exchanger.setName('Integrated Waterside Economizer Heat Exchanger')
        heat_exchanger.setControlType('CoolingDifferentialOnOff')

        # add the heat exchanger to the chilled water loop upstream of the chiller
        heat_exchanger.addToNode(chilled_water_loop.supplyInletNode())

        # Copy the setpoint managers from the plant's supply outlet node
        # to the chillers and HX outlets.
        # This is necessary so that the correct type of operation scheme will be created.
        # Without this, OS will create an uncontrolled operation scheme
        # and the chillers will never run.
        chw_spms = chilled_water_loop.supplyOutletNode.setpointManagers()
        objs = []
        for obj in chillers:
            objs.append(obj.to_ChillerElectricEIR.get())
        objs.append(heat_exchanger)
        for obj in objs:
            outlet = obj.supplyOutletModelObject().get().to_Node().get()
            for spm in chw_spms:
                new_spm = spm.clone().to_SetpointManager().get()
                new_spm.addToNode(outlet)
    else:
        # non-integrated
        # if the heat exchanger can meet the entire load, the heat exchanger will run
        # and the chiller is disabled.
        # In E+, only one chiller can be tied to a given heat exchanger, so if you have
        # multiple chillers, they will cannot be tied to a single heat exchanger without EMS.
        chiller = None
        if os_vector_len(chillers) == 0:
            msg = 'No chillers were found on {}; cannot add a non-integrated ' \
                'waterside economizer.'.format(chilled_water_loop.nameString())
            print(msg)
            heat_exchanger.setControlType('CoolingSetpointOnOff')
        elif os_vector_len(chillers) > 1:
            chiller = chillers[0]
            msg = 'More than one chiller was found on {}. EnergyPlus only allows a ' \
                'single chiller to be interlocked with the HX.  Chiller {} was selected.' \
                ' Additional chillers will not be locked out during HX operation.'.format(
                    chilled_water_loop.nameString(), chiller.nameString())
            print(msg)
        else:  # 1 chiller
            chiller = chillers[0]
        chiller = chiller.to_ChillerElectricEIR().get()

        # set methods for non-integrated heat exchanger
        heat_exchanger.setName('Non-Integrated Waterside Economizer Heat Exchanger')
        heat_exchanger.setControlType('CoolingSetpointOnOffWithComponentOverride')

        # add the heat exchanger to a supply side branch of the chilled water loop
        # parallel with the chiller(s)
        chilled_water_loop.addSupplyBranchForComponent(heat_exchanger)

        # Copy the setpoint managers from the plant's supply outlet node to the HX outlet.
        # This is necessary so that the correct type of operation scheme will be created.
        # Without this, the HX will never run
        chw_spms = chilled_water_loop.supplyOutletNode().setpointManagers()
        outlet = heat_exchanger.supplyOutletModelObject().get().to_Node().get()
        for spm in chw_spms:
            new_spm = spm.clone().to_SetpointManager().get()
            new_spm.addToNode(outlet)

        # set the supply and demand inlet fields to interlock the heat exchanger with the chiller
        chiller_supply_inlet = chiller.supplyInletModelObject().get().to_Node().get()
        heat_exchanger.setComponentOverrideLoopSupplySideInletNode(chiller_supply_inlet)
        chiller_demand_inlet = chiller.demandInletModelObject().get().to_Node().get()
        heat_exchanger.setComponentOverrideLoopDemandSideInletNode(chiller_demand_inlet)

        # check if the chilled water pump is on a branch with the chiller.
        # if it is, move this pump before the splitter so that it can push water
        # through either the chiller or the heat exchanger.
        pumps_on_branches = []
        # search for constant and variable speed pumps between supply splitter and supply mixer.
        supply_comps = chilled_water_loop.supplyComponents(
            chilled_water_loop.supplySplitter(), chilled_water_loop.supplyMixer())
        for supply_comp in supply_comps:
            if supply_comp.to_PumpConstantSpeed().is_initialized():
                pumps_on_branches.append(supply_comp.to_PumpConstantSpeed().get())
            elif supply_comp.to_PumpVariableSpeed().is_initialized():
                pumps_on_branches.append(supply_comp.to_PumpVariableSpeed().get())
        # If only one pump is found, clone it, put the clone on the supply inlet node,
        # and delete the original pump.
        # If multiple branch pumps, clone the first pump found, add it to the inlet
        # of the heat exchanger, and warn user.
        if len(pumps_on_branches) == 1:
            pump = pumps_on_branches[0]
            pump_clone = pump.clone(model).to_StraightComponent().get()
            pump_clone.addToNode(chilled_water_loop.supplyInletNode())
            pump.remove()
        elif len(pumps_on_branches) > 1:
            hx_inlet_node = heat_exchanger.inletModelObject().get().to_Node().get()
            pump = pumps_on_branches[0]
            pump_clone = pump.clone(model).to_StraightComponent().get()
            pump_clone.addToNode(hx_inlet_node)

    # add heat exchanger to condenser water loop
    condenser_water_loop.addDemandBranchForComponent(heat_exchanger)

    # change setpoint manager on condenser water loop to allow waterside economizing
    dsgn_sup_wtr_temp_f = 42.0
    dsgn_sup_wtr_temp_c = TEMPERATURE.to_unit([42.0], 'C', 'F')[0]
    for spm in condenser_water_loop.supplyOutletNode().setpointManagers():
        if spm.to_SetpointManagerFollowOutdoorAirTemperature().is_initialized():
            spm = spm.to_SetpointManagerFollowOutdoorAirTemperature().get()
            spm.setMinimumSetpointTemperature(dsgn_sup_wtr_temp_c)
        elif spm.to_SetpointManagerScheduled().is_initialized():
            spm = spm.to_SetpointManagerScheduled().get()()
            cw_temp_sch = create_constant_schedule_ruleset(
                model, dsgn_sup_wtr_temp_c,
                name='{} Temp - {}F'.format(
                    chilled_water_loop.nameString(), int(dsgn_sup_wtr_temp_f)),
                schedule_type_limit='Temperature')
            spm.setSchedule(cw_temp_sch)
        else:
            msg = 'Condenser water loop {} setpoint manager {} is not a recognized ' \
                'setpoint manager type. Cannot change to account for the waterside ' \
                'economizer.'.format(condenser_water_loop.nameString(), spm.nameString())
            print(msg)

    return heat_exchanger


def model_get_or_add_ground_hx_loop():
    pass


def model_get_or_add_heat_pump_loop():
    pass


def model_get_or_add_chilled_water_loop(
        model, cool_fuel, chilled_water_loop_cooling_type='WaterCooled'):
    """Get existing chilled water loop or add a new one if there isn't one already.
    
    Args:
        model: [OpenStudio::Model::Model] OpenStudio model object.
        cool_fuel: [String] the cooling fuel. Valid choices are Electricity,
            DistrictCooling, and HeatPump.
        chilled_water_loop_cooling_type: [String] Archetype for chilled water
            loops, AirCooled or WaterCooled.
    """
    # retrieve the existing chilled water loop or add a new one if necessary
    chilled_water_loop = None
    if model.getPlantLoopByName('Chilled Water Loop').is_initialized():
        chilled_water_loop = model.getPlantLoopByName('Chilled Water Loop').get()
    else:
        if cool_fuel == 'DistrictCooling':
            chilled_water_loop = model_add_chw_loop(
                model, chw_pumping_type='const_pri', cooling_fuel=cool_fuel)
        elif cool_fuel == 'HeatPump':
            condenser_water_loop = model_get_or_add_ambient_water_loop(model)
            chilled_water_loop = model_add_chw_loop(
                model, chw_pumping_type='const_pri_var_sec',
                chiller_cooling_type='WaterCooled',
                chiller_compressor_type='Rotary Screw',
                condenser_water_loop=condenser_water_loop)
        elif cool_fuel == 'Electricity':
            if chilled_water_loop_cooling_type == 'AirCooled':
                chilled_water_loop = model_add_chw_loop(
                    model, chw_pumping_type='const_pri',
                    chiller_cooling_type='AirCooled', cooling_fuel=cool_fuel)
            else:
                fan_type = 'Variable Speed Fan'
                condenser_water_loop = model_add_cw_loop(
                    model, cooling_tower_type='Open Cooling Tower',
                    cooling_tower_fan_type='Propeller or Axial',
                    cooling_tower_capacity_control=fan_type,
                    number_of_cells_per_tower=1, number_cooling_towers=1)
                chilled_water_loop = model_add_chw_loop(
                    model, chw_pumping_type='const_pri_var_sec',
                    chiller_cooling_type='WaterCooled',
                    chiller_compressor_type='Rotary Screw',
                    condenser_water_loop=condenser_water_loop)
        else:
            print('No cool_fuel specified.')

    return chilled_water_loop


def model_get_or_add_hot_water_loop(
        model, heat_fuel, hot_water_loop_type='HighTemperature'):
    """Get existing hot water loop or add a new one if there isn't one already.

    Args:
        model: [OpenStudio::Model::Model] OpenStudio model object.
        heat_fuel: [String] the heating fuel. Valid choices are NaturalGas,
            Electricity, DistrictHeating, DistrictHeatingWater, DistrictHeatingSteam.
        hot_water_loop_type: [String] Archetype for hot water loops.
    """
    if heat_fuel is None:
        print('Hot water loop fuel type is nil. Cannot add hot water loop.')
        return None

    make_new_hot_water_loop = True
    hot_water_loop = None
    # retrieve the existing hot water loop or add a new one if not of the correct type
    if model.getPlantLoopByName('Hot Water Loop').is_initialized():
        hot_water_loop = model.getPlantLoopByName('Hot Water Loop').get()
        design_loop_exit_temperature = \
            hot_water_loop.sizingPlant().designLoopExitTemperature()
        design_loop_exit_temperature = \
            TEMPERATURE.to_unit([design_loop_exit_temperature], 'F', 'C')[0]
        # check that the loop is the correct archetype
        if hot_water_loop_type == 'HighTemperature':
            if design_loop_exit_temperature > 130.0:
                make_new_hot_water_loop = False 
        elif hot_water_loop_type == 'LowTemperature':
            if design_loop_exit_temperature <= 130.0:
                make_new_hot_water_loop = False

    if make_new_hot_water_loop:
        if hot_water_loop_type == 'HighTemperature':
            hot_water_loop = model_add_hw_loop(model, heat_fuel)
        elif hot_water_loop_type == 'LowTemperature':
            hot_water_loop = model_add_hw_loop(
                model, heat_fuel, dsgn_sup_wtr_temp=120.0,
                boiler_draft_type='Condensing')
        else:
            print('Hot water loop archetype {} not recognized.'.format(hot_water_loop_type))
            return None
    return hot_water_loop


def model_get_or_add_ambient_water_loop():
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
        elif main_heat_fuel in ('DistrictHeating', 'DistrictHeatingWater',
                                'DistrictHeatingSteam'):
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
        model_add_vav_pfp_boxes(
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
