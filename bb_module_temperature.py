"""Example temperature conversion module.

Demonstration module with two model functions for converting
temperature between Fahrenheit and centigrade units.

Kinetica Blackbox Model
(c) 2023 Kinetica DB, Inc.
"""


def convert_to_celsius(inputs=None):
    """Convert from Fahrenheit with H2O state."""

    temp_f = int(inputs['temp_f'])
    temp_c = (temp_f - 32) * 5 / 9
    temp_k = (temp_f - 32) * 5 / 9 + 273.15

    if temp_k < 0:
        raise ValueError('Nonsensical inputs - below absolute zero')

    water = 'H20 in Liquid state at sea level'

    if temp_c > 100:
        water = 'Above H20 Boiling Point'

    elif temp_c < 0:
        water = 'Below H20 Freezing Point'

    outputs = {
        'temp_c': temp_c,
        'temp_k': temp_k,
        'state': water
    }

    return [outputs]


def convert_to_fahrenheit(inputs=None):
    """Convert from centigrade with H20 state."""

    temp_c = int(inputs['temp_c'])
    temp_f = (temp_c * 9 / 5) + 32
    temp_k = (temp_f - 32) * 5 / 9 + 273.15

    if temp_k < 0:
        raise ValueError('Nonsensical inputs - below absolute zero')

    water = 'H20 in Liquid state at sea level'

    if temp_c > 100:
        water = 'Above H20 Boiling Point'

    elif temp_c < 0:
        water = 'Below H20 Freezing Point'

    outputs = {
        'temp_f': temp_f,
        'temp_k': temp_k,
        'state': water
    }

    return [outputs]
