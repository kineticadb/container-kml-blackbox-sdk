import time
import random

import pandas as pd


def blackbox_function_default(inMap):
    outMap = inMap
    return outMap

def blackbox_function_identity(inMap):
    outMap = inMap
    return outMap

def blackbox_function_identity_multiout(inMap):
    outMap = inMap
    return [outMap]

def blackbox_function_identity_custom_multiout(inMap):
    rows_out = 1
    if "character" in inMap and inMap["character"]=="Arvin Sloane":
        rows_out = 2
    if "character" in inMap and inMap["character"]=="Sidney Bristow":
        rows_out = 2
    outMap = inMap
    return [outMap for i in range(rows_out)]

def blackbox_function_math(inMap):
    f1=int(inMap['figure1'])
    f2=int(inMap['figure2'])
    mylabel=inMap['mylabel']

    if 'please_crash_me' in mylabel:
        raise Exception("User-initiated purposeful failure! Go Figure")

    outMap = {
        'sum':f1+f2,
        'product':f1*f2,
        'max':max([f1,f2]),
        'suminwords': mylabel + " " + str(int(f1+f2))
        }
    return outMap

from sdk.bb_runner import bulk_infer_capable

@bulk_infer_capable
def blackbox_function_math_bulkinfer(inMap):
    # Unlike the non-batched variant above, inMap here is an ARRAY of dicts
    in_df = pd.DataFrame(inMap)
    in_df['figure1_numeric'] = pd.to_numeric(in_df["figure1"])
    in_df['figure2_numeric'] = pd.to_numeric(in_df["figure2"])

    in_df['sum'] = in_df["figure1_numeric"] + in_df["figure2_numeric"]
    in_df['product'] = in_df["figure1_numeric"] * in_df["figure2_numeric"]
    in_df['max'] = in_df[["figure1_numeric", "figure2_numeric"]].max(axis=1)
    in_df['suminwords'] = in_df["mylabel"] + " " + in_df['sum'].astype(str)
    return in_df.to_dict('records')

def blackbox_function_math_multiout(inMap):
    f1=int(inMap['figure1'])
    f2=int(inMap['figure2'])
    mylabel=inMap['mylabel']

    if 'please_crash_me' in mylabel:
        raise Exception("User-initiated purposeful failure! Go Figure")

    out_q = [
        {'operation':'sum', 'result':f1+f2},
        {'operation':'product', 'result':f1*f2},
        {'operation':'min', 'result':min([f1,f2])},
        {'operation':'max', 'result':max([f1,f2])}]
    return out_q

def blackbox_function_advanced_math(inMap):
    f1=int(inMap['figure1'])
    f2=int(inMap['figure2'])
    mylabel=inMap['mylabel']

    if 'please_crash_me' in mylabel:
        raise Exception("User-initiated purposeful failure! Go Figure")

    outMap = {
        'division':f1/f2,
        'modulo':f1%f2,
        'min':min([f1,f2]),
        'productinwords': mylabel + " " + str(int(f1*f2))
        }
    return outMap

def blackbox_function_math_superslow(inMap):
    f1=int(inMap['figure1'])
    f2=int(inMap['figure2'])
    mylabel=inMap['mylabel']

    # artificial delay
    on_time_calcs_ratio = 0.99
    if 'on_time_calcs_ratio' in inMap:
        on_time_calcs_ratio=int(inMap['on_time_calcs_ratio'])

    if random.random() >= 0.9999: # EXTREME SLOWDOWN!
        time.sleep(60)
    elif random.random() >= 0.999: # The 9-9-9 Plan!
        time.sleep(15)
    elif random.random() >= on_time_calcs_ratio: # Normal slowdown!
        time.sleep(1)

    if 'please_crash_me' in mylabel:
        raise Exception("User-initiated purposeful failure! Go Figure")

    outMap = {
        'sum':f1+f2,
        'product':f1*f2,
        'max':max([f1,f2]),
        'suminwords': mylabel + " " + str(int(f1+f2))
        }
    return outMap

# BlackBox function to demonstrate intake of environment variables
def blackbox_function_envvar_demo(inMap):
    f1=int(inMap['figure1'])
    f2=int(inMap['figure2'])

    if 'ENVVAR1' not in os.environ:
        raise Exception("Missing environment variable ENVVAR1")

    if 'ENVVAR2' not in os.environ:
        raise Exception("Missing environment variable ENVVAR2")

    outMap = {
        'sum':f1+f2,
        'product':f1*f2,
        'max':max([f1,f2]),
        'suminwords': f"{ENVVAR1} {f1+f2} {ENVVAR2}"
        }
    return outMap

def classify_petworthiness_engineered_inputs(inMap):
    outMap = inMap
    return outMap