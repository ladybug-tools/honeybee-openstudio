# coding=utf-8
"""Module taken from OpenStudio-standards.

https://github.com/NREL/openstudio-standards/blob/master/
lib/openstudio-standards/prototypes/common/objects/Prototype.utilities.rb
"""
from __future__ import division

import re

from honeybee_openstudio.openstudio import openstudio_model


def kw_per_ton_to_cop(kw_per_ton):
    """A helper method to convert from kW/ton to COP."""
    return 3.517 / kw_per_ton


def ems_friendly_name(name):
    """Converts existing string to ems friendly string."""
    # replace white space and special characters with underscore
    # \W is equivalent to [^a-zA-Z0-9_]
    new_name = re.sub('[^A-Za-z0-9]', '_', str(name))
    # prepend ems_ in case the name starts with a number
    new_name = 'ems_{}'.format(new_name)
    return new_name


def convert_curve_biquadratic(coeffs, ip_to_si=True):
    """Convert biquadratic curves that are a function of temperature.

    From IP (F) to SI (C) or vice-versa.  The curve is of the form
    z = C1 + C2*x + C3*x^2 + C4*y + C5*y^2 + C6*x*y
    where C1, C2, ... are the coefficients,
    x is the first independent variable (in F or C)
    y is the second independent variable (in F or C)
    and z is the resulting value
    """
    if ip_to_si:
        # Convert IP curves to SI curves
        si_coeffs = []
        si_coeffs.append((coeffs[0] + (32.0 * (coeffs[1] + coeffs[3])) +
                          (1024.0 * (coeffs[2] + coeffs[4] + coeffs[5]))))
        si_coeffs.append(((9.0 / 5.0 * coeffs[1]) +
                          (576.0 / 5.0 * coeffs[2]) + (288.0 / 5.0 * coeffs[5])))
        si_coeffs.append((81.0 / 25.0 * coeffs[2]))
        si_coeffs.append(((9.0 / 5.0 * coeffs[3]) +
                          (576.0 / 5.0 * coeffs[4]) + (288.0 / 5.0 * coeffs[5])))
        si_coeffs.append((81.0 / 25.0 * coeffs[4]))
        si_coeffs.append((81.0 / 25.0 * coeffs[5]))
        return si_coeffs
    else:
        # Convert SI curves to IP curves
        ip_coeffs = []
        ip_coeffs.append((coeffs[0] - (160.0 / 9.0 * (coeffs[1] + coeffs[3])) +
                          (25_600.0 / 81.0 * (coeffs[2] + coeffs[4] + coeffs[5]))))
        ip_coeffs.append((5.0 / 9.0 * (coeffs[1] - (320.0 / 9.0 * coeffs[2]) -
                                       (160.0 / 9.0 * coeffs[5]))))
        ip_coeffs.append((25.0 / 81.0 * coeffs[2]))
        ip_coeffs.append((5.0 / 9.0 * (coeffs[3] - (320.0 / 9.0 * coeffs[4]) -
                                       (160.0 / 9.0 * coeffs[5]))))
        ip_coeffs.append((25.0 / 81.0 * coeffs[4]))
        ip_coeffs.append((25.0 / 81.0 * coeffs[5]))
        return ip_coeffs


def create_curve_biquadratic(
        model, coeffs, crv_name, min_x, max_x, min_y, max_y, min_out, max_out):
    """Create a biquadratic curve."""
    curve = openstudio_model.CurveBiquadratic(model)
    curve.setName(crv_name)
    curve.setCoefficient1Constant(coeffs[0])
    curve.setCoefficient2x(coeffs[1])
    curve.setCoefficient3xPOW2(coeffs[2])
    curve.setCoefficient4y(coeffs[3])
    curve.setCoefficient5yPOW2(coeffs[4])
    curve.setCoefficient6xTIMESY(coeffs[5])
    if min_x is None:
        curve.setMinimumValueofx(min_x)
    if max_x is not None:
        curve.setMaximumValueofx(max_x)
    if min_y is not None:
        curve.setMinimumValueofy(min_y)
    if max_y is not None:
        curve.setMaximumValueofy(max_y)
    if min_out is not None:
        curve.setMinimumCurveOutput(min_out)
    if max_out is not None:
        curve.setMaximumCurveOutput(max_out)
    return curve


def create_curve_quadratic(
        model, coeffs, crv_name, min_x, max_x, min_out, max_out, is_dimensionless=False):
    """Create a quadratic curve."""
    curve = openstudio_model.CurveQuadratic(model)
    curve.setName(crv_name)
    curve.setCoefficient1Constant(coeffs[0])
    curve.setCoefficient2x(coeffs[1])
    curve.setCoefficient3xPOW2(coeffs[2])
    if min_x is None:
        curve.setMinimumValueofx(min_x)
    if max_x is not None:
        curve.setMaximumValueofx(max_x)
    if min_out is not None:
        curve.setMinimumCurveOutput(min_out)
    if max_out is not None:
        curve.setMaximumCurveOutput(max_out)
    if is_dimensionless:
        curve.setInputUnitTypeforX('Dimensionless')
        curve.setOutputUnitType('Dimensionless')
    return curve
