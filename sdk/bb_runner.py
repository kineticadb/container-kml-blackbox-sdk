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
import logging
import argparse

import zmq
import gpudb
import requests
from requests.exceptions import ConnectionError

from sdk.kinetica_black_box import KineticaBlackBox

logger = logging.getLogger("kml-bbox-sdk")
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handlerC = logging.StreamHandler(sys.stdout)
handlerC.setFormatter(formatter)
logger.addHandler(handlerC)

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
    inbound_zmq_topic = dep_details["response"]["item"]["model_dep_config"]["inp-tablemonitor"]["topic_id"]
    schema_inbound = json.dumps(dep_details["response"]["item"]["model_dep_config"]["inp-tablemonitor"]["type_schema"])
    schema_outbound = json.dumps(dep_details["response"]["item"]["model_dep_config"]["out-tablemonitor"]["type_schema"])
    table_outbound = dep_details["response"]["item"]["model_dep_config"]["out-tablemonitor"]["table_name"]

    return (bbox_module, bbox_function, inbound_zmq_topic, schema_inbound, schema_outbound, table_outbound)


if __name__ == '__main__':

    # Parameter defaults
    parser = argparse.ArgumentParser()
    #parser.set_defaults(kml_host="SET_ME")
    parser.set_defaults(kml_port=9187)
    #parser.set_defaults(db_host="SET_ME")
    parser.set_defaults(db_port=9191)
    #parser.set_defaults(zmq_host="SET_ME")
    parser.set_defaults(zmq_port=9009)
    parser.set_defaults(be_quiet=False)

    # Mandatory input value
    parser.add_argument("--db-conn-str", required = True, help = "Kinetica DB Connection String")
    parser.add_argument("--db-user", help = "Kinetica DB blackbox service account user")
    parser.add_argument("--db-pass", help = "Kinetica DB blackbox service account pass")
    parser.add_argument("--db-table-audit", help = "Blackbox output audit table")
    parser.add_argument("--db-table-results", help = "Blackbox output results table")
    parser.add_argument("--zmq-dealer-host", required = True, help = "BlackBox Dealer ZMQ Host (usually same as DB host node)")
    parser.add_argument("--zmq-dealer-port", type=int, help = "BlackBox Dealer ZMQ Port Port (defaults to 9009)")
    parser.add_argument("--bbx-module", help = "Blackbox module for execution")
    parser.add_argument("--bbx-function", help = "Blackbox method for execution")

    # Path A - KML REST API Driven Details
    parser.add_argument("--deployment-id", type=int, help = "KML Deployment Entity ID")
    parser.add_argument("--kml-api-base", help = "KML REST API Base (protocol, host, port)")

    # Path B - Command-line Driven Details
    parser.add_argument("--schema-inbound", help = "Blackbox inbound message schema")
    parser.add_argument("--schema-outbound", help = "Blackbox outboud message schema")

    parser.add_argument("--quiet", action="store_true", dest="be_quiet", help = "Reduce Standard Output logging")

    # TODO: Environment variable pass-through of user/pass
    # TODO: also pass thru db host and port

    args = parser.parse_args()  

    logger.info("Arguments interpreted and defaults applied as required")
    logger.info(f"DB Conn Str {args.db_conn_str}")
    logger.info(f"    DB User {args.db_user}")
    #logger.info(f"    DB Pass {args.db_pass}")
    logger.info(f"   ZMQ Host {args.zmq_dealer_host}")    
    logger.info(f"   ZMQ Port {args.zmq_dealer_port}")
    logger.info(f" Quiet Mode {args.be_quiet}")

    logger.info(f"KML APIBase {args.kml_api_base}")
    logger.info(f" BBX Module {args.bbx_module}")
    logger.info(f"   BBX Func {args.bbx_function}")
    logger.info(f" DB Table A {args.db_table_audit}")
    logger.info(f" DB Table R {args.db_table_results}")

    schema_inbound = None
    schema_outbound = None
    bbx_module = None
    bbx_function = None
    db_table = None

    if args.deployment_id:
        logger.info("Obtaining inbound/outbound schema from KML REST API")
        logger.info(f"    Depl ID {args.deployment_id}")
        if not args.kml_host:
            logger.error("Configured to obtain inbound/outbound schema from KML REST API...but no KML Host specified")
            sys.exit(1)
        if args.schema_inbound:
            logger.error("Configured to obtain inbound/outbound schema from KML REST API...but encountered ambiguous command-line input schema entry")
            sys.exit(1)
        if args.schema_outbound:
            logger.error("Configured to obtain inbound/outbound schema from KML REST API...but encountered ambiguous command-line output schema entry")
            sys.exit(1)

        if args.bbx_module:
            logger.error("Configured to obtain inbound/outbound schema from KML REST API...but encountered ambiguous bbx_module command-line entry")
            sys.exit(1)
        if args.bbx_function:
            logger.error("Configured to obtain inbound/outbound schema from KML REST API...but encountered ambiguous bbx_function command-line entry")
            sys.exit(1)
        if args.db_table_audit:
            logger.error("Configured to obtain inbound/outbound schema from KML REST API...but encountered ambiguous db_table (audit) command-line entry")
            sys.exit(1)
        if args.db_table_results:
            logger.error("Configured to obtain inbound/outbound schema from KML REST API...but encountered ambiguous db_table (results) command-line entry")
            sys.exit(1)
        
        if not validate_kml_api(api_base = args.kml_api_base):
            logger.error("Unsuccessful reaching out to KML REST API")
            sys.exit(1)
        else:
            logger.info("Successfully connected to KML REST API")

        bbx_module, bbx_function, schema_inbound, schema_outbound, db_table = get_dep_details(api_base = args.kml_api_base, dep_id = args.deployment_id)


    else:
        logger.info("Obtaining inbound/outbound schema from command-line arguments --schema-inbound {...} and --schema-outbound  {...}")
        if not args.schema_inbound:
            logger.error("Configured to obtain inbound schema from command line arguments...but no command-line inputs found")
            sys.exit(1)
        if not args.schema_outbound:
            logger.error("Configured to obtain output schema from command line arguments...but no command-line inputs found")
            sys.exit(1)
        if not args.bbx_module:
            logger.error("Configured to obtain bbx_module from command line arguments...but no command-line inputs found")
            sys.exit(1)
        if not args.bbx_function:
            logger.error("Configured to obtain bbx_function from command line arguments...but no command-line inputs found")
            sys.exit(1)
        if not args.db_table_audit:
            logger.error("Configured to obtain output db_table_audit from command line arguments...but no command-line inputs found")
            sys.exit(1)
        if not args.db_table_results:
            logger.error("Configured to obtain output db_table_results from command line arguments...but no command-line inputs found")
            sys.exit(1)

        schema_inbound = args.schema_inbound
        schema_outbound = args.schema_outbound
        bbx_module = args.bbx_module
        bbx_function = args.bbx_function
        db_table_results = args.db_table_results    
        db_table_audit = args.db_table_audit    

    logger.info(f"  Schema In {schema_inbound}")
    logger.info(f" Schema Out {schema_outbound}")

    logger.info(f" BBX Module {bbx_module}")
    logger.info(f" BBX Function {bbx_function}")
    logger.info(f" Table Out Audit {db_table_audit}")
    logger.info(f" Table Out Results {db_table_results}")

    bb = KineticaBlackBox(
            bb_module = bbx_module, 
            bb_method = bbx_function, 
            schema_inbound = schema_inbound, 
            schema_outbound = schema_outbound, 
            zmq_dealer_host = args.zmq_dealer_host, 
            zmq_dealer_port = args.zmq_dealer_port, 
            db_table_audit = db_table_audit, 
            db_table_results = db_table_results, 
            db_conn_str  = args.db_conn_str,
            db_user  = args.db_user,
            db_pass  = args.db_pass,
            be_quiet = args.be_quiet)
    
    bb.run()
