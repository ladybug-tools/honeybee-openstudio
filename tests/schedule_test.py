"""Test the translators for schedules to OpenStudio."""
from ladybug.dt import Date, Time
from honeybee.altnumber import no_limit

from honeybee_energy.schedule.day import ScheduleDay
from honeybee_energy.schedule.rule import ScheduleRule
from honeybee_energy.schedule.ruleset import ScheduleRuleset
from honeybee_energy.schedule.fixedinterval import ScheduleFixedInterval
from honeybee_energy.schedule.typelimit import ScheduleTypeLimit
import honeybee_energy.lib.scheduletypelimits as schedule_types

from honeybee_openstudio.openstudio import OSModel
from honeybee_openstudio.schedule import schedule_type_limits_to_openstudio, \
    schedule_day_to_openstudio, schedule_to_openstudio


def test_schedule_typelimit_to_openstudio():
    """Test the ScheduleRuleset translation to_openstudio."""
    os_model = OSModel()
    os_model.setDayofWeekforStartDay('Sunday')  # this avoids lots of warnings

    temperature = ScheduleTypeLimit(
        'Temperature', -273.15, no_limit, 'Continuous', 'Temperature')

    os_type_limit = schedule_type_limits_to_openstudio(temperature, os_model)
    assert str(os_type_limit.name()) == 'Temperature'
    os_type_limit_str = str(os_type_limit)
    assert os_type_limit_str.startswith('OS:ScheduleTypeLimits,')


def test_schedule_day_to_openstudio():
    """Test the ScheduleDay translation to_openstudio."""
    os_model = OSModel()
    os_model.setDayofWeekforStartDay('Sunday')  # this avoids lots of warnings
    simple_office = ScheduleDay('Simple Office Occupancy', [0, 1, 0],
                                [Time(0, 0), Time(9, 0), Time(17, 0)])

    os_sch_day = schedule_day_to_openstudio(simple_office, os_model)
    assert str(os_sch_day.name()) == 'Simple Office Occupancy'
    os_sch_day_str = str(os_sch_day)
    assert os_sch_day_str.startswith('OS:Schedule:Day,')


def test_schedule_ruleset_to_openstudio():
    """Test the ScheduleRuleset translation to_openstudio."""
    os_model = OSModel()
    os_model.setDayofWeekforStartDay('Sunday')  # this avoids lots of warnings
    schedule_type_limits_to_openstudio(schedule_types.fractional, os_model)

    weekday_office = ScheduleDay('Weekday Office Occupancy', [0, 1, 0],
                                 [Time(0, 0), Time(9, 0), Time(17, 0)])
    saturday_office = ScheduleDay('Saturday Office Occupancy', [0, 0.25, 0],
                                  [Time(0, 0), Time(9, 0), Time(17, 0)])
    sunday_office = ScheduleDay('Sunday Office Occupancy', [0])
    sat_rule = ScheduleRule(saturday_office, apply_saturday=True)
    sun_rule = ScheduleRule(sunday_office, apply_sunday=True)
    summer_office = ScheduleDay('Summer Office Occupancy', [0, 1, 0.25],
                                [Time(0, 0), Time(6, 0), Time(22, 0)])
    winter_office = ScheduleDay('Winter Office Occupancy', [0])
    schedule = ScheduleRuleset('Office Occupancy', weekday_office,
                               [sat_rule, sun_rule], schedule_types.fractional,
                               sunday_office, summer_office, winter_office)

    os_schedule = schedule_to_openstudio(schedule, os_model)
    assert str(os_schedule.name()) == 'Office Occupancy'
    os_schedule_str = str(os_schedule)
    assert os_schedule_str.startswith('OS:Schedule:Ruleset,')


def test_schedule_ruleset_to_openstudio_date_range():
    """Test the ScheduleRuleset translation to_openstudio with a date range."""
    os_model = OSModel()
    os_model.setDayofWeekforStartDay('Sunday')  # this avoids lots of warnings

    weekday_school = ScheduleDay('Weekday School Year', [0, 1, 0.5, 0],
                                 [Time(0, 0), Time(8, 0), Time(15, 0), Time(18, 0)])
    weekend_school = ScheduleDay('Weekend School Year', [0])
    weekday_summer = ScheduleDay('Weekday Summer', [0, 0.5, 0],
                                 [Time(0, 0), Time(9, 0), Time(17, 0)])
    weekend_summer = ScheduleDay('Weekend Summer', [0])

    summer_weekday_rule = ScheduleRule(
        weekday_summer, start_date=Date(7, 1), end_date=Date(9, 1))
    summer_weekday_rule.apply_weekday = True
    summer_weekend_rule = ScheduleRule(
        weekend_summer, start_date=Date(7, 1), end_date=Date(9, 1))
    summer_weekend_rule.apply_weekend = True
    school_weekend_rule = ScheduleRule(weekend_school)
    school_weekend_rule.apply_weekend = True

    summer_design = ScheduleDay('School Summer Design', [0, 1, 0.25],
                                [Time(0, 0), Time(6, 0), Time(18, 0)])
    winter_design = ScheduleDay('School Winter Design', [0])

    schedule = ScheduleRuleset('School Occupancy', weekday_school,
                               [summer_weekday_rule, summer_weekend_rule,
                                school_weekend_rule],
                               schedule_types.fractional, summer_design, winter_design)

    os_schedule = schedule_to_openstudio(schedule, os_model)
    assert str(os_schedule.name()) == 'School Occupancy'
    os_schedule_str = str(os_schedule)
    assert os_schedule_str.startswith('OS:Schedule:Ruleset,')


def test_schedule_fixedinterval_to_openstudio():
    """Test the ScheduleFixedInterval translation to_openstudio."""
    os_model = OSModel()
    os_model.setDayofWeekforStartDay('Sunday')  # this avoids lots of warnings

    trans_sched = ScheduleFixedInterval(
        'Custom Transmittance', [x / 8760 for x in range(8760)],
        schedule_types.fractional)

    os_schedule = schedule_to_openstudio(trans_sched, os_model)
    assert str(os_schedule.name()) == 'Custom Transmittance'
    os_schedule_str = str(os_schedule)
    assert os_schedule_str.startswith('OS:Schedule:FixedInterval,')
