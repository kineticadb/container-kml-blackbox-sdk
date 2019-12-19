import time
import random

import pandas as pd

from sdk.bb_runner import bulk_infer_capable



def convert_to_celsius(inMap=None):

    F = int(inMap['temp_f'])

    C = (F - 32) * 5 / 9
    K = (F - 32) * 5 / 9 + 273.15

    if K < 0:
        raise ValueError("Nonsensical inputs - below absolute zero")

    BF = "H20 in Liquid state at sea level"

    if C > 100:
        BF = "Above H20 Boiling Point"

    elif C < 0:
        BF = "Below H20 Freezing Point"

    outMap = {'temp_c': C,
              'temp_k': K,
              'state': BF}

    return [outMap]

def convert_to_fahrenheit(inMap=None):

    C = int(inMap['temp_c'])
    F = (C * 9 / 5) + 32
    K = (F - 32) * 5 / 9 + 273.15

    if K < 0:
        raise ValueError("Nonsensical inputs - below absolute zero")

    BF = "H20 in Liquid state at sea level"

    if C > 100:
        BF = "Above H20 Boiling Point"

    elif C < 0:
        BF = "Below H20 Freezing Point"

    outMap = {'temp_f': F,
              'temp_k': K,
              'state': BF}

    return outMap