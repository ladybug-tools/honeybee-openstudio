# coding=utf-8
"""Modules taken from OpenStudio-standards.

https://github.com/NREL/openstudio-standards/blob/master/
lib/openstudio-standards/prototypes/common/objects/Prototype.CoilCoolingWater.rb
"""
from __future__ import division

from honeybee_openstudio.openstudio import openstudio_model

from .utilities import create_curve_biquadratic, create_curve_quadratic
from .schedule import model_add_schedule


def create_coil_cooling_water(
        model, chilled_water_loop, air_loop_node=None, name='Clg Coil', schedule=None,
        design_inlet_water_temperature=None, design_inlet_air_temperature=None,
        design_outlet_air_temperature=None):
    clg_coil = openstudio_model.CoilCoolingWater(model)

    # add to chilled water loop
    chilled_water_loop.addDemandBranchForComponent(clg_coil)

    # add to air loop if specified
    if air_loop_node is not None:
        clg_coil.addToNode(air_loop_node)

    # set coil name
    name = 'Clg Coil' if name is None else name
    clg_coil.setName(name)

    # set coil availability schedule
    if schedule is None:  # default always on
        coil_availability_schedule = model.alwaysOnDiscreteSchedule()
    elif isinstance(schedule, str):
        if schedule == 'alwaysOffDiscreteSchedule':
            coil_availability_schedule = model.alwaysOffDiscreteSchedule()
        elif coil_availability_schedule == 'alwaysOnDiscreteSchedule':
            coil_availability_schedule = model.alwaysOnDiscreteSchedule()
        else:
            coil_availability_schedule = model_add_schedule(model, schedule)
    else:  # assume that it is an actual schedule object
        coil_availability_schedule = schedule
    clg_coil.setAvailabilitySchedule(coil_availability_schedule)

    # rated temperatures
    if design_inlet_water_temperature is None:
        clg_coil.autosizeDesignInletWaterTemperature()
    else:
        clg_coil.setDesignInletWaterTemperature(design_inlet_water_temperature)
    if design_inlet_air_temperature is not None:
        clg_coil.setDesignInletAirTemperature(design_inlet_air_temperature)
    if design_outlet_air_temperature is not None:
        clg_coil.setDesignOutletAirTemperature(design_outlet_air_temperature)

    # defaults
    clg_coil.setHeatExchangerConfiguration('CrossFlow')

    # coil controller properties
    # @note These inputs will get overwritten if addToNode or addDemandBranchForComponent
    # is called on the htg_coil object after this
    clg_coil_controller = clg_coil.controllerWaterCoil().get()
    clg_coil_controller.setName('{} Controller'.format(clg_coil.nameString()))
    clg_coil_controller.setAction('Reverse')
    clg_coil_controller.setMinimumActuatedFlow(0.0)

    return clg_coil


def create_coil_cooling_dx_two_speed(
        model, air_loop_node=None, name='2spd DX Clg Coil', schedule=None, type=None):
    """Prototype CoilCoolingDXTwoSpeed object.

    Enters in default curves for coil by type of coil

    Args:
        model: [OpenStudio::Model::Model] OpenStudio model object.
        air_loop_node: [<OpenStudio::Model::Node>] the coil will be placed on
            this node of the air loop.
        name: [String] the name of the system, or nil in which case it will be defaulted.
        schedule: [String] name of the availability schedule, or
            [<OpenStudio::Model::Schedule>] Schedule object, or nil in which case
            default to always on.
        type: [String] the type of two speed DX coil to reference the correct curve set.
    """
    clg_coil = openstudio_model.CoilCoolingDXTwoSpeed(model)

    # add to air loop if specified
    if air_loop_node is not None:
        clg_coil.addToNode(air_loop_node)

    # set coil name
    name = '2spd DX Clg Coil' if name is None else name
    clg_coil.setName(name)

    # set coil availability schedule
    if schedule is None:  # default always on
        coil_availability_schedule = model.alwaysOnDiscreteSchedule()
    elif isinstance(schedule, str):
        if schedule == 'alwaysOffDiscreteSchedule':
            coil_availability_schedule = model.alwaysOffDiscreteSchedule()
        elif coil_availability_schedule == 'alwaysOnDiscreteSchedule':
            coil_availability_schedule = model.alwaysOnDiscreteSchedule()
        else:
            coil_availability_schedule = model_add_schedule(model, schedule)
    else:  # assume that it is an actual schedule object
        coil_availability_schedule = schedule
    clg_coil.setAvailabilitySchedule(coil_availability_schedule)

    clg_cap_f_of_temp = None
    clg_cap_f_of_flow = None
    clg_energy_input_ratio_f_of_temp = None
    clg_energy_input_ratio_f_of_flow = None
    clg_part_load_ratio = None
    clg_cap_f_of_temp_low_spd = None
    clg_energy_input_ratio_f_of_temp_low_spd = None

    # curve sets
    if type == 'OS default':
        pass  # use OS defaults
    elif type == 'Residential Minisplit HP':
        # Performance curves
        # These coefficients are in SI units
        cool_cap_ft_coeffs_si = [0.7531983499655835, 0.003618193903031667, 0.0,
                                 0.006574385031351544, -6.87181191015432e-05, 0.0]
        cool_eir_ft_coeffs_si = [-0.06376924779982301, -0.0013360593470367282,
                                 1.413060577993827e-05, 0.019433076486584752,
                                 -4.91395947154321e-05, -4.909341249475308e-05]
        cool_cap_fflow_coeffs = [1, 0, 0]
        cool_eir_fflow_coeffs = [1, 0, 0]
        cool_plf_fplr_coeffs = [0.89, 0.11, 0]

        # Make the curves
        clg_cap_f_of_temp = create_curve_biquadratic(
            model, cool_cap_ft_coeffs_si, 'Cool-Cap-fT', 0, 100, 0, 100, None, None)
        clg_cap_f_of_flow = create_curve_quadratic(
            model, cool_cap_fflow_coeffs, 'Cool-Cap-fFF', 0, 2, 0, 2, is_dimensionless=True)
        clg_energy_input_ratio_f_of_temp = create_curve_biquadratic(
            model, cool_eir_ft_coeffs_si, 'Cool-EIR-fT', 0, 100, 0, 100, None, None)
        clg_energy_input_ratio_f_of_flow = create_curve_quadratic(
            model, cool_eir_fflow_coeffs, 'Cool-EIR-fFF', 0, 2, 0, 2, is_dimensionless=True)
        clg_part_load_ratio = create_curve_quadratic(
            model, cool_plf_fplr_coeffs, 'Cool-PLF-fPLR', 0, 1, 0, 1, is_dimensionless=True)
        clg_cap_f_of_temp_low_spd = create_curve_biquadratic(
            model, cool_cap_ft_coeffs_si, 'Cool-Cap-fT', 0, 100, 0, 100, None, None)
        clg_energy_input_ratio_f_of_temp_low_spd = create_curve_biquadratic(
            model, cool_eir_ft_coeffs_si, 'Cool-EIR-fT', 0, 100, 0, 100, None, None)
        clg_coil.setRatedLowSpeedSensibleHeatRatio(0.73)
        clg_coil.setCondenserType('AirCooled')
    else:  # default curve set, type == 'PSZ-AC' || 'Split AC' || 'PTAC'
        clg_cap_f_of_temp = openstudio_model.CurveBiquadratic(model)
        clg_cap_f_of_temp.setCoefficient1Constant(0.42415)
        clg_cap_f_of_temp.setCoefficient2x(0.04426)
        clg_cap_f_of_temp.setCoefficient3xPOW2(-0.00042)
        clg_cap_f_of_temp.setCoefficient4y(0.00333)
        clg_cap_f_of_temp.setCoefficient5yPOW2(-0.00008)
        clg_cap_f_of_temp.setCoefficient6xTIMESY(-0.00021)
        clg_cap_f_of_temp.setMinimumValueofx(17.0)
        clg_cap_f_of_temp.setMaximumValueofx(22.0)
        clg_cap_f_of_temp.setMinimumValueofy(13.0)
        clg_cap_f_of_temp.setMaximumValueofy(46.0)

        clg_cap_f_of_flow = openstudio_model.CurveQuadratic(model)
        clg_cap_f_of_flow.setCoefficient1Constant(0.77136)
        clg_cap_f_of_flow.setCoefficient2x(0.34053)
        clg_cap_f_of_flow.setCoefficient3xPOW2(-0.11088)
        clg_cap_f_of_flow.setMinimumValueofx(0.75918)
        clg_cap_f_of_flow.setMaximumValueofx(1.13877)

        clg_energy_input_ratio_f_of_temp = openstudio_model.CurveBiquadratic(model)
        clg_energy_input_ratio_f_of_temp.setCoefficient1Constant(1.23649)
        clg_energy_input_ratio_f_of_temp.setCoefficient2x(-0.02431)
        clg_energy_input_ratio_f_of_temp.setCoefficient3xPOW2(0.00057)
        clg_energy_input_ratio_f_of_temp.setCoefficient4y(-0.01434)
        clg_energy_input_ratio_f_of_temp.setCoefficient5yPOW2(0.00063)
        clg_energy_input_ratio_f_of_temp.setCoefficient6xTIMESY(-0.00038)
        clg_energy_input_ratio_f_of_temp.setMinimumValueofx(17.0)
        clg_energy_input_ratio_f_of_temp.setMaximumValueofx(22.0)
        clg_energy_input_ratio_f_of_temp.setMinimumValueofy(13.0)
        clg_energy_input_ratio_f_of_temp.setMaximumValueofy(46.0)

        clg_energy_input_ratio_f_of_flow = openstudio_model.CurveQuadratic(model)
        clg_energy_input_ratio_f_of_flow.setCoefficient1Constant(1.20550)
        clg_energy_input_ratio_f_of_flow.setCoefficient2x(-0.32953)
        clg_energy_input_ratio_f_of_flow.setCoefficient3xPOW2(0.12308)
        clg_energy_input_ratio_f_of_flow.setMinimumValueofx(0.75918)
        clg_energy_input_ratio_f_of_flow.setMaximumValueofx(1.13877)

        clg_part_load_ratio = openstudio_model.CurveQuadratic(model)
        clg_part_load_ratio.setCoefficient1Constant(0.77100)
        clg_part_load_ratio.setCoefficient2x(0.22900)
        clg_part_load_ratio.setCoefficient3xPOW2(0.0)
        clg_part_load_ratio.setMinimumValueofx(0.0)
        clg_part_load_ratio.setMaximumValueofx(1.0)

        clg_cap_f_of_temp_low_spd = openstudio_model.CurveBiquadratic(model)
        clg_cap_f_of_temp_low_spd.setCoefficient1Constant(0.42415)
        clg_cap_f_of_temp_low_spd.setCoefficient2x(0.04426)
        clg_cap_f_of_temp_low_spd.setCoefficient3xPOW2(-0.00042)
        clg_cap_f_of_temp_low_spd.setCoefficient4y(0.00333)
        clg_cap_f_of_temp_low_spd.setCoefficient5yPOW2(-0.00008)
        clg_cap_f_of_temp_low_spd.setCoefficient6xTIMESY(-0.00021)
        clg_cap_f_of_temp_low_spd.setMinimumValueofx(17.0)
        clg_cap_f_of_temp_low_spd.setMaximumValueofx(22.0)
        clg_cap_f_of_temp_low_spd.setMinimumValueofy(13.0)
        clg_cap_f_of_temp_low_spd.setMaximumValueofy(46.0)

        clg_energy_input_ratio_f_of_temp_low_spd = openstudio_model.CurveBiquadratic(model)
        clg_energy_input_ratio_f_of_temp_low_spd.setCoefficient1Constant(1.23649)
        clg_energy_input_ratio_f_of_temp_low_spd.setCoefficient2x(-0.02431)
        clg_energy_input_ratio_f_of_temp_low_spd.setCoefficient3xPOW2(0.00057)
        clg_energy_input_ratio_f_of_temp_low_spd.setCoefficient4y(-0.01434)
        clg_energy_input_ratio_f_of_temp_low_spd.setCoefficient5yPOW2(0.00063)
        clg_energy_input_ratio_f_of_temp_low_spd.setCoefficient6xTIMESY(-0.00038)
        clg_energy_input_ratio_f_of_temp_low_spd.setMinimumValueofx(17.0)
        clg_energy_input_ratio_f_of_temp_low_spd.setMaximumValueofx(22.0)
        clg_energy_input_ratio_f_of_temp_low_spd.setMinimumValueofy(13.0)
        clg_energy_input_ratio_f_of_temp_low_spd.setMaximumValueofy(46.0)

        clg_coil.setRatedLowSpeedSensibleHeatRatio(0.69)
        clg_coil.setBasinHeaterCapacity(10)
        clg_coil.setBasinHeaterSetpointTemperature(2.0)

    if clg_cap_f_of_temp is not None:
        clg_coil.setTotalCoolingCapacityFunctionOfTemperatureCurve(clg_cap_f_of_temp)
    if clg_cap_f_of_flow is not None:
        clg_coil.setTotalCoolingCapacityFunctionOfFlowFractionCurve(clg_cap_f_of_flow)
    if clg_energy_input_ratio_f_of_temp is not None:
        clg_coil.setEnergyInputRatioFunctionOfTemperatureCurve(
            clg_energy_input_ratio_f_of_temp)
    if clg_energy_input_ratio_f_of_flow is not None:
        clg_coil.setEnergyInputRatioFunctionOfFlowFractionCurve(
            clg_energy_input_ratio_f_of_flow)
    if clg_part_load_ratio is not None:
        clg_coil.setPartLoadFractionCorrelationCurve(clg_part_load_ratio)
    if clg_cap_f_of_temp_low_spd is not None:
        clg_coil.setLowSpeedTotalCoolingCapacityFunctionOfTemperatureCurve(
            clg_cap_f_of_temp_low_spd)
    if clg_energy_input_ratio_f_of_temp_low_spd is not None:
        clg_coil.setLowSpeedEnergyInputRatioFunctionOfTemperatureCurve(
            clg_energy_input_ratio_f_of_temp_low_spd)

    return clg_coil
