import time
import random

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
    rows_out = 3
    if "rows_out" in inMap:
        rows_out = int(inMap["rows_out"])
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