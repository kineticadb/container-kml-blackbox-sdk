import os
import sys
import time
import warnings
import traceback
import json
import collections
import datetime
import uuid
import logging
import pprint
import copy
import logging

import zmq
import gpudb
import requests
from requests.exceptions import ConnectionError

logger = logging.getLogger("kml-bbox-sdk")
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handlerC = logging.StreamHandler(sys.stdout)
handlerC.setFormatter(formatter)
logger.addHandler(handlerC)


# Grab environment variables or die trying
def grab_or_die(env_var_key):
    if env_var_key not in os.environ:
        logger.error(f"Could not find {env_var_key} environment variable. Cannot proceed.")
        sys.exit(1)
    return os.environ[env_var_key]

def get_conn_db(db_conn_str, db_user, db_pass):
    # Prepare DB Communications
    logger.info(f"Attempting to connect to DB at {db_conn_str} to push to {tbl_out_audit}")
    if db_user == 'no_cred' or db_pass == 'no_cred':
        cn_db=gpudb.GPUdb(encoding='BINARY',
                       host=db_conn_str)
    else:
        cn_db=gpudb.GPUdb(encoding='BINARY',
                       host=db_conn_str,
                       username=db_user,
                       password=db_pass)
    return cn_db

def validate_kml_api(api_base):

    if api_base is None:
        logger.error(f"No valid KML API found ({api_base})")
        return False

    # Loop here many times with longer waits
    #   to ensure a blip in the RESP API doesnt kill the entire script
    wait_times = [1, 2, 4, 8, 16, 32, 64]
    for waitsecs in wait_times:

        try:
            r = requests.get(f"{api_base}/ping")
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

if __name__ == '__main__':

    # Things coming in from the environment via env-variables
    KML_API_BASE = grab_or_die("KML_API_BASE")
    KML_DEPL_ID = grab_or_die("KML_DEPL_ID")
    ZMQ_CONN_STR = grab_or_die("ZMQ_CONN_STR")
    DB_CONN_STR = grab_or_die("DB_CONN_STR")
    DB_USER = grab_or_die("DB_USER")
    DB_PASS = grab_or_die("DB_PASS")

    logger.info("Initializing KineticaBlackBox")
    logger.info(f"KML_API_BASE: {KML_API_BASE}")
    logger.info(f"ZMQ_CONN_STR: {ZMQ_CONN_STR}")
    logger.info(f"DB_CONN_STR: {DB_CONN_STR}")
    logger.info(f"DB_USER: {DB_USER}")
    logger.info(f"DB_PASS: *******")

    # Things we default, but can capture in as environment variables
    be_quiet = True if (os.environ.get('be_quiet') and os.environ.get('be_quiet').upper()=="TRUE") else False
    if be_quiet:
        logger.setLevel(logging.ERROR)

    BATCH_SIZE = int(os.getenv('BATCH_SIZE', 10000))

    # Things we grab from REST API View
    bb_module = "bb_module_default"
    bb_method = "blackbox_function_default"
    schema_inbound = None # dependent on model, must come from deployment
    #schema_outbound = None # dependent on model, must come from deployment
    tbl_out_results =  None # dependent on deployment, must come from deployment
    tbl_out_audit = None # dependent on deployment, must come from deployment

    dep_details_uri = f"{KML_API_BASE}/model/deployment/{KML_DEPL_ID}/view"
    logger.info(f"Obtaining deployment details from {dep_details_uri}")
    if not validate_kml_api(KML_API_BASE):
        logger.error(f"Could not reach KML REST API for deployment details")
        sys.exit(1)
    dep_details_resp = requests.get(dep_details_uri)
    if (dep_details_resp.status_code == 404):
        logger.error(f"Could not find deployment with id {KML_DEPL_ID}")
        sys.exit(1)
    dep_details = dep_details_resp.json()

    if 'success' not in dep_details or not dep_details['success']:
        logger.error(f"Could not find live deployment with id {KML_DEPL_ID}")
        sys.exit(1)

    bb_module = dep_details["response"]["item"]["base_model_inst"]["model_inst_config"]["blackbox_module"]
    bb_method = dep_details["response"]["item"]["base_model_inst"]["model_inst_config"]["blackbox_function"]
    schema_inbound = dep_details["response"]["item"]["model_dep_config"]["inp-tablemonitor"]["type_schema"]
    tbl_out_results = dep_details["response"]["item"]["model_dep_config"]["sink_table"]
    tbl_out_audit = dep_details["response"]["item"]["model_dep_config"]["out-tablemonitor"]["table_name"]
    output_record_list = dep_details["response"]["item"]["base_model_inst"]["model_inst_config"]["output_record_type"]
    outfields = [arec["col_name"] for arec in output_record_list]

    logger.info(f"bb_module: {bb_module}")
    logger.info(f"bb_method: {bb_method}")
    logger.info(f"schema_inbound: {schema_inbound}")
    logger.info(f"tbl_out_results: {tbl_out_results}")
    logger.info(f"tbl_out_audit: {tbl_out_audit}")
    logger.info(f"Output fields: {len(outfields)}")
    for outf in outfields:
        logger.info(f"   Output field: {outf}")

    schema_decoder = json.dumps(schema_inbound) #json.loads(json.dumps(schema_inbound))
    method_to_call = getattr(__import__(bb_module), bb_method)
    logger.info(f"Dynamically loaded function {bb_method} from module {bb_module} for lambda application")

    hotpotatoes = 0

    try:
        # Prepare ZMQ Socket
        context = zmq.Context()
        cn_zmq = context.socket(zmq.PULL)
        cn_zmq.connect(ZMQ_CONN_STR)

        # Prepare DB Connection
        cn_db = get_conn_db(DB_CONN_STR, DB_USER, DB_PASS)

        # [Re]Establish table handles
        h_tbl_out_audit = gpudb.GPUdbTable(name = tbl_out_audit, db = cn_db)
        h_tbl_out_results = None
        logger.info(f"DB Results Table {tbl_out_results}")
        if tbl_out_results and tbl_out_results != "NOT_APPLICABLE":
            h_tbl_out_results = gpudb.GPUdbTable(name = tbl_out_results, db = cn_db)
            logger.info(f"Established connection to sink table")
            logger.info(f"All results will be persisted to both Audit {tbl_out_audit} and output DB Tables {tbl_out_results}")
        else:
            logger.info(f"All results will be persisted to Audit DB Table {tbl_out_audit} only")


        while True:

            logger.info("Awaiting inbound requests")

            mpr = cn_zmq.recv_multipart()
            parts_received = len(mpr)
            hotpotatoes += 1
            logger.info(f"Received inbound request number {hotpotatoes} from dealer with {parts_received} items")

            infer_q=[]
            for mindex, m in enumerate(mpr[1:]):

                # TODO: Determine whether we can decode the entire array at once, rather than member-by-member
                inference_inbound_payload=gpudb.GPUdbRecord.decode_binary_data(schema_decoder, m)[0]

                # wipe out all previous results
                results_package = None # TODO: is this necessary given the below?
                # by default send back all inputs as well as our calculated outputs
                # TODO: Remove binary fields, as those could be huge and duplication is not desirable
                results_package = copy.deepcopy(inference_inbound_payload)

                results_package["success"]=0 # we start with the assumption of failure
                results_package["errorstack"]=None
                results_package["errorlog"]=None

                for o in outfields:
                    results_package[o]=None

                process_start_dt=datetime.datetime.now().replace(microsecond=100).isoformat(' ')[:-3]
                results_package["process_start_dt"]=process_start_dt

                try:
                    outMaps = method_to_call(inference_inbound_payload)
                    results_package["success"]=1
                    process_end_dt=datetime.datetime.now().replace(microsecond=100).isoformat(' ')[:-3]
                    results_package["process_end_dt"]=process_end_dt

                    for outMap in outMaps:
                        lineitem = copy.deepcopy(results_package)
                        for k,v in outMap.items():
                            lineitem[k]=v
                        infer_q.append(lineitem)

                        if not be_quiet:
                            logger.debug ("\tResults received from blackbox:")
                            # TODO: Only do this for non-binary fields and non-store-only fields
                            for ko,vo in outMap.items():
                                logger.debug("\t %s: %s" % (ko,vo))
                            logger.debug ("\t>> Completed")

                except Exception as e:
                    logger.error(e)
                    error_type, error, tb = sys.exc_info()
                    logger.error(traceback.format_tb(tb))
                    traceback.print_exc(file=sys.stdout)
                    results_package["errorstack"]="\n".join(traceback.format_tb(tb))
                    if e:
                        results_package["errorlog"]=str(e)
                    process_end_dt=datetime.datetime.now().replace(microsecond=100).isoformat(' ')[:-3]
                    results_package["process_end_dt"]=process_end_dt
                    infer_q.append(results_package)

            # TODO: Check to ensure persist was successful, otherwise, keep trying and eventually fail+reconnect
            _ = h_tbl_out_audit.insert_records(infer_q)
            if tbl_out_results and tbl_out_results != "NOT_APPLICABLE":
                _ = h_tbl_out_results.insert_records(infer_q)

            logger.info(f"Completed Processing block request {hotpotatoes} with {parts_received} parts")

    except Exception as e:
        # TODO: Send some distress signal back to REST API
        # If we continuously get here, there is a problem
        logger.error("Problems initializing relay pipeline")
        logger.error(e)
        logger.debug(traceback.format_exc())

        # Wait briefly, then re-try establishing connections
        time.sleep(2)

if __name__ == '__main__':
    main()

    # TODO: Really, we should *never* exit. So if we exit, that is a failure already
    # The only "exit" would be if we are terminated externally via REST API
    sys.exit(1)