# coding=utf-8
"""Module taken from OpenStudio-standards.

https://github.com/NREL/openstudio-standards/blob/master/
lib/openstudio-standards/prototypes/common/objects/Prototype.hvac_systems.rb
"""
from __future__ import division

from ladybug.datatype.temperature import Temperature
from ladybug.datatype.temperaturedelta import TemperatureDelta
from ladybug.datatype.pressure import Pressure

from honeybee_openstudio.openstudio import openstudio, openstudio_model, os_vector_len
from .utilities import kw_per_ton_to_cop
from .schedule import create_constant_schedule_ruleset
from .central_air_source_heat_pump import create_central_air_source_heat_pump
from .boiler_hot_water import create_boiler_hot_water
from .plant_loop import chw_sizing_control, plant_loop_set_chw_pri_sec_configuration
from .pump_variable_speed import pump_variable_speed_set_control_type

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
