LOGGING_SILENTLY = False

def attach_log(module='unknown_module', log_name='kml', debug=False):
    """Setup the log file for the calling module."""

    import logging
    import os

    # Configure the logger
    module = module.replace('kml.api.', '')
    logger = logging.getLogger(module)
    if LOGGING_SILENTLY:
        logger.setLevel(logging.ERROR)
    else:        
        logger.setLevel(logging.DEBUG)

    # Create a file handler
    log_name = '.'.join([log_name, 'log'])
    path = os.path.dirname(os.path.realpath(__file__)) 
    

    # Create a logging format
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    handlerF = logging.FileHandler('/'.join([path, log_name]))
    handlerF.setFormatter(formatter)
    handlerF.setLevel(logging.DEBUG)

    handlerC = logging.StreamHandler()
    handlerC.setFormatter(formatter)
    handlerC.setLevel(logging.DEBUG)


    # Add the handlers to the logger
    logger.addHandler(handlerF)
    logger.addHandler(handlerC)

    return logger