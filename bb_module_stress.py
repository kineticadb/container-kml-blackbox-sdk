import os
import string
import random
import logging
import uuid 

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

console_logger = logging.getLogger("kml-bbx-stressor-stdout")
console_logger.setLevel(logging.DEBUG)
handlerC = logging.StreamHandler()
handlerC.setFormatter(formatter)
if (console_logger.hasHandlers()):
    console_logger.handlers.clear()
console_logger.addHandler(handlerC)


file_logger = logging.getLogger("kml-bbx-stressor-file")
file_logger.setLevel(logging.DEBUG)
handlerF = logging.FileHandler("kml-bbx.log")
handlerF.setFormatter(formatter)
if (file_logger.hasHandlers()):
    file_logger.handlers.clear()
file_logger.addHandler(handlerF)


def randomString(n):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k = n)) 

running_memory = []
def blackbox_function_rsc_pressure(inMap):
    f1=int(inMap['figure1'])
    f2=int(inMap['figure2'])
    mylabel=inMap['mylabel']

    if "stress" in inMap:
        stress = inMap["stress"]
        stress_factor = inMap["stress_factor"]
        if stress=="stdout":
            console_logger.info("Received stress request: stdout")
            # Purposefully try and generate lots of stdout
            for _ in range(stress_factor):
                # generate stress_factor * kilobytes of stdout
                console_logger.info(randomString(1024))

        if stress=="disk":
            console_logger.info("Received stress request: disk")
            # Purposefully try and generate lots of disk use
            for _ in range(stress_factor):
                # generate stress_factor * kilobytes of log output
                file_logger.info(randomString(1024))
            # generate stress_factor * kilobytes of disk use
            with open(f"{uuid.uuid1()}.junk", 'w') as junkfile:
                junkfile.write(randomString(1024*stress_factor))

        if inMap["stress"]=="memory":
            console_logger.info("Received stress request: memory")
            # generate stress_factor * kilobytes of memory use
            running_memory.append(randomString(1024*stress_factor))

    outMap = {
        'sum':f1+f2,
        'product':f1*f2,
        'max':max([f1,f2]),
        'suminwords': mylabel + " " + str(int(f1+f2))
        }
    return outMap