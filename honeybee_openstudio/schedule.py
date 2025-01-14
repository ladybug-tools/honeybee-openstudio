# coding=utf-8
"""Utilities to convert schedule dictionaries to Python objects."""
from __future__ import division
import os

from ladybug.futil import write_to_file
from ladybug.analysisperiod import AnalysisPeriod
from honeybee.altnumber import no_limit
from honeybee_energy.schedule.ruleset import ScheduleRuleset
from honeybee_energy.schedule.fixedinterval import ScheduleFixedInterval

from honeybee_openstudio.openstudio import OSScheduleTypeLimits, OSScheduleRuleset, \
    OSScheduleRule, OSScheduleDay, OSScheduleFixedInterval, OSExternalFile, \
    OSScheduleFile, OSVector, OSTime, OSTimeSeries, openstudio_date


def schedule_type_limits_to_openstudio(type_limit, os_model):
    """Convert Honeybee ScheduleTypeLimit to OpenStudio ScheduleTypeLimits."""
    os_type_limit = OSScheduleTypeLimits(os_model)
    os_type_limit.setName(type_limit.identifier)
    if type_limit._display_name is not None:
        os_type_limit.setDisplayName(type_limit.display_name)
    if type_limit.lower_limit != no_limit:
        os_type_limit.setLowerLimitValue(type_limit.lower_limit)
    if type_limit.upper_limit != no_limit:
        os_type_limit.setUpperLimitValue(type_limit.upper_limit)
    os_type_limit.setNumericType(type_limit.numeric_type)
    os_type_limit.setUnitType(type_limit.unit_type)
    return os_type_limit


def schedule_day_to_openstudio(schedule_day, os_model):
    """Convert Honeybee ScheduleDay to OpenStudio ScheduleDay."""
    os_day_sch = OSScheduleDay(os_model)
    os_day_sch.setName(schedule_day.identifier)
    if schedule_day._display_name is not None:
        os_day_sch.setDisplayName(schedule_day.display_name)
    values_day = schedule_day.values
    times_day = [tm.to_array() for tm in schedule_day.times]
    times_day.pop(0)  # Remove [0, 0] from array at index 0.
    times_day.append((24, 0))  # Add [24, 0] at index 0
    for i, val in enumerate(values_day):
        time_until = OSTime(0, times_day[i][0], times_day[i][1], 0)
        os_day_sch.addValue(time_until, val)
    return os_day_sch


def schedule_ruleset_to_openstudio(schedule, os_model):
    """Convert Honeybee ScheduleRuleset to OpenStudio ScheduleRuleset."""
    # create openstudio schedule ruleset object
    os_sch_ruleset = OSScheduleRuleset(os_model)
    os_sch_ruleset.setName(schedule.identifier)
    if schedule._display_name is not None:
        os_sch_ruleset.setDisplayName(schedule.display_name)
    # assign schedule type limit
    os_type_limit = None
    if schedule.schedule_type_limit:
        os_type_limit_ref = os_model.getScheduleTypeLimitsByName(
            schedule.schedule_type_limit.identifier)
        if os_type_limit_ref.is_initialized():
            os_type_limit = os_type_limit_ref.get()
            os_sch_ruleset.setScheduleTypeLimits(os_type_limit)
    # loop through day schedules and create openstudio schedule day objects
    day_schs = {}
    def_day = schedule.default_day_schedule
    for day_sch in schedule.day_schedules:
        if day_sch.identifier != def_day.identifier:
            os_day_sch = schedule_day_to_openstudio(day_sch, os_model)
            if os_type_limit is not None:
                os_day_sch.setScheduleTypeLimits(os_type_limit)
            day_schs[day_sch.identifier] = os_day_sch
    # assign default day schedule
    os_def_day_sch = os_sch_ruleset.defaultDaySchedule()
    if os_type_limit is not None:
        os_def_day_sch.setScheduleTypeLimits(os_type_limit)
    os_def_day_sch.setName(def_day.identifier)
    if def_day._display_name is not None:
        os_def_day_sch.setDisplayName(def_day.display_name)
    values_day = def_day.values
    times_day = [tm.to_array() for tm in def_day.times]
    times_day.pop(0)  # Remove [0, 0] from array at index 0.
    times_day.append((24, 0))  # Add [24, 0] at index 0
    for i, val in enumerate(values_day):
        time_until = OSTime(0, times_day[i][0], times_day[i][1], 0)
        os_def_day_sch.addValue(time_until, val)
    # assign holiday schedule
    if schedule.holiday_schedule is not None:
        holiday_schedule = day_schs[schedule.holiday_schedule.identifier]
        os_sch_ruleset.setHolidaySchedule(holiday_schedule)
    # assign summer design day schedule
    if schedule.summer_designday_schedule is not None:
        summer_design_day = day_schs[schedule.summer_designday_schedule.identifier]
        os_sch_ruleset.setSummerDesignDaySchedule(summer_design_day)
    # assign winter design day schedule
    if schedule.winter_designday_schedule is not None:
        winter_design_day = day_schs[schedule.winter_designday_schedule.identifier]
        os_sch_ruleset.setWinterDesignDaySchedule(winter_design_day)
    # assign schedule rules
    for i, rule in enumerate(schedule.schedule_rules):
        os_rule = OSScheduleRule(os_sch_ruleset)
        os_rule.setApplySunday(rule.apply_sunday)
        os_rule.setApplyMonday(rule.apply_monday)
        os_rule.setApplyTuesday(rule.apply_tuesday)
        os_rule.setApplyWednesday(rule.apply_wednesday)
        os_rule.setApplyThursday(rule.apply_thursday)
        os_rule.setApplyFriday(rule.apply_friday)
        os_rule.setApplySaturday(rule.apply_saturday)
        start_date = openstudio_date(os_model, rule.start_date.month, rule.start_date.day)
        end_date = openstudio_date(os_model, rule.end_date.month, rule.end_date.day)
        os_rule.setStartDate(start_date)
        os_rule.setEndDate(end_date)
        schedule_rule_day = day_schs[rule.schedule_day.identifier]
        values_day = schedule_rule_day.values()
        times_day = schedule_rule_day.times()
        for tim, val in zip(times_day, values_day):
            rule_day = os_rule.daySchedule()
            rule_day.addValue(tim, val)
        os_sch_ruleset.setScheduleRuleIndex(os_rule, i)
    return os_sch_ruleset


def schedule_fixed_interval_to_openstudio(schedule, os_model):
    """Convert Honeybee ScheduleFixedInterval to OpenStudio ScheduleFixedInterval."""
    # create the new schedule
    os_fi_sch = OSScheduleFixedInterval(os_model)
    os_fi_sch.setName(schedule.identifier)
    if schedule._display_name is not None:
        os_fi_sch.setDisplayName(schedule.display_name)
    # assign start date and the out of range value
    os_fi_sch.setStartMonth(1)
    os_fi_sch.setStartDay(1)
    os_fi_sch.setOutOfRangeValue(schedule.placeholder_value)
    # assign the interpolate value
    os_fi_sch.setInterpolatetoTimestep(schedule.interpolate)
    # assign the schedule type limit
    if schedule.schedule_type_limit:
        os_type_limit_ref = os_model.getScheduleTypeLimitsByName(
            schedule.schedule_type_limit.identifier)
        if os_type_limit_ref.is_initialized():
            os_type_limit = os_type_limit_ref.get()
            os_fi_sch.setScheduleTypeLimits(os_type_limit)
    # assign the timestep
    interval_length = int(60 / schedule.timestep)
    os_fi_sch.setIntervalLength(interval_length)
    os_interval_length = OSTime(0, 0, interval_length)
    # assign the values as a timeseries
    start_date = openstudio_date(os_model, 1, 1)
    all_values = [float(val) for val in schedule.values_at_timestep(schedule.timestep)]
    series_values = OSVector(len(all_values))
    for i, val in enumerate(all_values):
        series_values[i] = val
    timeseries = OSTimeSeries(start_date, os_interval_length, series_values, '')
    os_fi_sch.setTimeSeries(timeseries)
    return os_fi_sch


def schedule_fixed_interval_to_openstudio_file(
        schedule, os_model, schedule_directory, include_datetimes=False):
    """Convert Honeybee ScheduleFixedInterval to OpenStudio ScheduleFile.

    Args:
        schedule: The Honeybee ScheduleFixedInterval to be converted.
        os_model: The OpenStudio Model to which the ScheduleFile will be added.
        schedule_directory: Text string of a path to a folder on this machine to
            which the CSV version of the file will be written.
        include_datetimes: Boolean to note whether a column of datetime objects
            should be written into the CSV alongside the data. Default is False,
            which will keep the resulting CSV lighter in file size but you may
            want to include such datetimes in order to verify that values align with
            the expected timestep. Note that the included datetimes will follow the
            EnergyPlus interpretation of aligning values to timesteps in which case
            the timestep to which the value is matched means that the value was
            utilized over all of the previous timestep.
    """
    # gather all of the data to be written into the CSV
    sched_data = [str(val) for val in schedule.values_at_timestep(schedule.timestep)]
    if include_datetimes:
        sched_a_per = AnalysisPeriod(timestep=schedule.timestep,
                                     is_leap_year=schedule.is_leap_year)
        sched_data = ('{},{}'.format(dt, val) for dt, val in
                      zip(sched_a_per.datetimes, sched_data))
    file_name = '{}.csv'.format(schedule.identifier.replace(' ', '_'))
    file_path = os.path.join(schedule_directory, file_name)
    # write the data into the file
    write_to_file(file_path, ',\n'.join(sched_data), True)
    full_path = os.path.abspath(file_path)
    # get the external file which points to the schedule csv file
    os_external_file = OSExternalFile.getExternalFile(os_model, full_path, False)
    if os_external_file.is_initialized():
        os_external_file = os_external_file.get()
    # create the schedule file
    column = 2 if include_datetimes else 1
    os_sch_file = OSScheduleFile(os_external_file, column, 0)
    os_sch_file.setName(schedule.identifier)
    if schedule._display_name is not None:
        os_sch_file.setDisplayName(schedule.display_name)
    os_sch_file.setInterpolatetoTimestep(schedule.interpolate)
    interval_length = int(60 / schedule.timestep)
    os_sch_file.setMinutesperItem(interval_length)
    # assign the schedule type limit
    if schedule.schedule_type_limit:
        os_type_limit_ref = os_model.getScheduleTypeLimitsByName(
            schedule.schedule_type_limit.identifier)
        if os_type_limit_ref.is_initialized():
            os_type_limit = os_type_limit_ref.get()
            os_sch_file.setScheduleTypeLimits(os_type_limit)
    return os_sch_file


def schedule_to_openstudio(schedule, os_model, schedule_directory=None):
    """Convert any Honeybee energy material into an OpenStudio object.

    Args:
        material: A honeybee-energy Python object of a material layer.
        os_model: The OpenStudio Model object to which the Room will be added.
        schedule_directory: An optional directory to be used to write Honeybee
            ScheduleFixedInterval objects to OpenStudio ScheduleFile objects
            instead of OpenStudio ScheduleFixedInterval, which translates to
            EnergyPlus Compact schedules.

    Returns:
        An OpenStudio object for the material.
    """
    if isinstance(schedule, ScheduleRuleset):
        return schedule_ruleset_to_openstudio(schedule, os_model)
    elif isinstance(schedule, ScheduleFixedInterval):
        if schedule_directory is None:
            return schedule_fixed_interval_to_openstudio(schedule, os_model)
        else:
            return schedule_fixed_interval_to_openstudio_file(
                schedule, os_model, schedule_directory)
    else:
        raise ValueError(
            '{} is not a recognized energy Schedule type'.format(type(schedule))
        )
