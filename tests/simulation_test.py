# coding=utf-8
import os

from ladybug.dt import Date
from honeybee_energy.simulation.parameter import SimulationParameter
from honeybee_energy.simulation.sizing import SizingParameter
from honeybee_energy.simulation.control import SimulationControl
from honeybee_energy.simulation.shadowcalculation import ShadowCalculation
from honeybee_energy.simulation.output import SimulationOutput
from honeybee_energy.simulation.runperiod import RunPeriod
from honeybee_energy.simulation.daylightsaving import DaylightSavingTime

from honeybee_openstudio.openstudio import OSModel, os_vector_len
from honeybee_openstudio.simulation import sizing_to_openstudio, \
    simulation_control_to_openstudio, shadow_calculation_to_openstudio, \
    simulation_output_to_openstudio, run_period_to_openstudio, \
    simulation_parameter_to_openstudio, assign_epw_to_model


def test_simulation_control_to_openstudio():
    """Test the simulation_control_to_openstudio method."""
    os_model = OSModel()
    sim_control = SimulationControl()
    os_sim_control = simulation_control_to_openstudio(sim_control, os_model)
    os_sim_control_str = str(os_sim_control)
    assert os_sim_control_str.startswith('OS:SimulationControl,')


def test_shadow_calculation_to_openstudio():
    """Test the shadow_calculation_to_openstudio method."""
    os_model = OSModel()
    shadow_calc = ShadowCalculation()
    os_shadow_calc = shadow_calculation_to_openstudio(shadow_calc, os_model)
    os_shadow_calc_str = str(os_shadow_calc)
    assert os_shadow_calc_str.startswith('OS:ShadowCalculation,')


def test_sizing_parameter_to_openstudio():
    """Test the sizing_to_openstudio method."""
    os_model = OSModel()
    sizing = SizingParameter()
    ddy_path = 'assets/chicago_monthly.ddy'
    ddy_path = os.path.join(os.path.dirname(__file__), ddy_path)
    sizing.add_from_ddy(ddy_path)

    os_sizing = sizing_to_openstudio(sizing, os_model)
    os_sizing_str = str(os_sizing)
    assert os_sizing_str.startswith('OS:Sizing:Parameters,')
    os_des_days = os_model.getDesignDays()
    assert os_vector_len(os_des_days) == 12


def test_simulation_output_to_openstudio():
    """Test the simulation_output_to_openstudio method."""
    os_model = OSModel()
    sim_output = SimulationOutput()
    sim_output.add_zone_energy_use('all')

    os_outputs = simulation_output_to_openstudio(sim_output, os_model)
    assert len(os_outputs) == 9
    os_output_str = str(os_outputs[0])
    assert os_output_str.startswith('OS:Output:Variable,')


def test_run_period_to_openstudio():
    """Test the run_period_to_openstudio method."""
    os_model = OSModel()
    run_period = RunPeriod()

    os_run_period = run_period_to_openstudio(run_period, os_model)
    os_run_period_str = str(os_run_period)
    assert os_run_period_str.startswith('OS:RunPeriod,')

    os_model = OSModel()
    run_period = RunPeriod()
    run_period.start_date = Date(1, 1)
    run_period.end_date = Date(6, 21)
    run_period.start_day_of_week = 'Monday'
    run_period.holidays = (Date(1, 1), Date(3, 17))
    run_period.daylight_saving_time = DaylightSavingTime()

    os_run_period = run_period_to_openstudio(run_period, os_model)
    os_run_period_str = str(os_run_period)
    assert os_run_period_str.startswith('OS:RunPeriod,')
    os_holidays = os_model.getRunPeriodControlSpecialDayss()
    assert os_vector_len(os_holidays) == 2


def test_simulation_parameter_to_openstudio():
    """Test the translation of SimulationParameter to OpenStudio."""
    sim_par = SimulationParameter()
    os_model = simulation_parameter_to_openstudio(sim_par)
    os_des_days = os_model.getDesignDays()
    assert os_vector_len(os_des_days) == 0

    sim_par = SimulationParameter()
    output = SimulationOutput()
    output.add_zone_energy_use()
    sim_par.output = output
    run_period = RunPeriod(Date(1, 1), Date(6, 21))
    sim_par.run_period = run_period
    sim_par.timestep = 4
    sim_control_alt = SimulationControl(run_for_sizing_periods=True,
                                        run_for_run_periods=False)
    sim_par.simulation_control = sim_control_alt
    shadow_calc_alt = ShadowCalculation('FullExteriorWithReflections')
    sim_par.shadow_calculation = shadow_calc_alt
    sizing_alt = SizingParameter(None, 1, 1)
    ddy_path = 'assets/chicago_monthly.ddy'
    ddy_path = os.path.join(os.path.dirname(__file__), ddy_path)
    sizing_alt.add_from_ddy(ddy_path)
    sim_par.sizing_parameter = sizing_alt
    sim_par.north_angle = 20
    sim_par.terrain_type = 'Ocean'
    os_model = simulation_parameter_to_openstudio(sim_par)
    os_des_days = os_model.getDesignDays()
    assert os_vector_len(os_des_days) == 12


def test_assign_epw_to_model():
    """Test the assign_epw_to_model method."""
    os_model = OSModel()
    epw_path = 'assets/chicago.epw'
    epw_path = os.path.join(os.path.dirname(__file__), epw_path)
    assert not os_model.weatherFile().is_initialized()

    assign_epw_to_model(epw_path, os_model, set_climate_zone=True)

    assert os_model.weatherFile().is_initialized()
    climate_zone_objs = os_model.getClimateZones()
    ashrae_zones = climate_zone_objs.getClimateZones('ASHRAE')
    assert os_vector_len(ashrae_zones) == 1
