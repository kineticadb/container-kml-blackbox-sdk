import os
import sys
import time
import warnings
import traceback
import json
import collections
import datetime
import argparse
import uuid

import zmq
import gpudb
import requests
from requests.exceptions import ConnectionError

import kmllogger
logger = kmllogger.attach_log(module="kml-bbox-utils", log_name='kml', debug=True)

def validate_kml_api(api_base):

    if api_base is None:
        logger.error(f"No valid KML API found ({api_base})")
        return False

    # Loop here many times with longer waits 
    #   to ensure a blip in the RESP API doesnt kill the entire script

    wait_times = [2, 4, 8, 16, 32, 64]
    for waitsecs in wait_times:

        try:
            r = requests.get(f"{api_base}/kml/ping")
            if r.status_code == 200:
                api_response = r.json()
                if 'success' in api_response and r.json()['success']:
                    logger.info(f"Successfully connected to API base {api_base}")
                    return True
        except ConnectionError as e:    # This is the correct syntax
            logger.warn(f"Could not connect to KML API {api_base}, will retry shortly...")
            time.sleep(waitsecs)
            # eating this error

    logger.error(f"Could not connect to KML API {api_base}, exhausted tries. Giving up.")
    return False

def get_dep_details(api_base, dep_id):
    # TODO: Loop here atleast X times with longer waits 
    #   to ensure a blip in the RESP API doesnt kill the entire script

    dep_details_uri = f"{api_base}/kml/model/deployment/{dep_id}/view"
    logger.info(f"Obtaining deployment details from {dep_details_uri}")
    dep_details_resp = requests.get(dep_details_uri)
    if (dep_details_resp.status_code == 404):
        logger.error(f"Could not find deployment with id {dep_id}")
        sys.exit(1)
    dep_details = dep_details_resp.json()    

    if 'success' not in dep_details or not dep_details['success']:
        logger.error(f"Could not find deployment with id {dep_id}")
        sys.exit(1)

    bbox_module = dep_details["response"]["item"]["base_model_inst"]["base_model"]["model_config"]["blackbox_module"]
    bbox_function = dep_details["response"]["item"]["base_model_inst"]["base_model"]["model_config"]["blackbox_function"]
    schema_inbound = json.dumps(dep_details["response"]["item"]["model_dep_config"]["inp-tablemonitor"]["type_schema"])
    schema_outbound = json.dumps(dep_details["response"]["item"]["model_dep_config"]["out-tablemonitor"]["type_schema"])
    table_outbound = dep_details["response"]["item"]["model_dep_config"]["out-tablemonitor"]["table_name"]

    return (bbox_module, bbox_function, schema_inbound, schema_outbound, table_outbound)