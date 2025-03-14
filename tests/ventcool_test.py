# coding=utf-8
"""Test the translators for ventilative cooling to OpenStudio."""
from ladybug.dt import Time
from honeybee.room import Room
from honeybee_energy.ventcool.control import VentilationControl
from honeybee_energy.ventcool.opening import VentilationOpening
from honeybee_energy.ventcool.fan import VentilationFan
from honeybee_energy.schedule.day import ScheduleDay
from honeybee_energy.schedule.ruleset import ScheduleRuleset
import honeybee_energy.lib.scheduletypelimits as schedule_types

from honeybee_openstudio.openstudio import OSModel
from honeybee_openstudio.ventcool import ventilation_opening_to_openstudio, \
    ventilation_fan_to_openstudio


def test_ventilation_opening_to_openstudio_simple():
    """Test the translation of VentilationOpening to OpenStudio."""
    os_model = OSModel()
    room = Room.from_box('ShoeBoxZone', 5, 10, 3)
    south_face = room[3]
    south_face.apertures_by_ratio(0.4, 0.01)
    aperture = south_face.apertures[0]
    aperture.is_operable = True
    simple_office = ScheduleDay('Simple Flush', [1, 0, 1],
                                [Time(0, 0), Time(9, 0), Time(22, 0)])
    schedule = ScheduleRuleset('Night Flush Schedule', simple_office,
                               None, schedule_types.fractional)
    vent_control = VentilationControl(18, schedule=schedule)
    room.properties.energy.window_vent_control = vent_control
    vent = VentilationOpening()
    aperture.properties.energy.vent_opening = vent

    os_vent = ventilation_opening_to_openstudio(vent, os_model)
    assert str(os_vent.name()) == '{}_Opening'.format(aperture.identifier)
    os_vent_str = str(os_vent)
    assert os_vent_str.startswith('OS:ZoneVentilation:WindandStackOpenArea,')


def test_ventilation_fan_to_openstudio():
    """Test the translation of VentilationFan to OpenStudio."""
    os_model = OSModel()
    night_sch = ScheduleRuleset.from_daily_values(
        'Night Flushing Schedule',
        [1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1])
    night_flush_control = VentilationControl(
        min_indoor_temperature=18, delta_temperature=0, schedule=night_sch)
    vent_fan = VentilationFan(
        'Night Flushing Fan', 1.5, 'Exhaust', 300, 0.65, night_flush_control)

    os_fan = ventilation_fan_to_openstudio(vent_fan, os_model)
    assert str(os_fan.name()) == 'Night Flushing Fan'
    os_fan_str = str(os_fan)
    assert os_fan_str.startswith('OS:ZoneVentilation:DesignFlowRate,')
