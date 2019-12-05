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

logger = logging.getLogger("kml-bbx-sdk")
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handlerC = logging.StreamHandler(sys.stdout)
handlerC.setFormatter(formatter)
logger.addHandler(handlerC)

DEFAULT_EVENT_SIG = {
    "deployment_id": os.environ.get("KML_DEPL_ID"), # e.g.: 187,
    "deployment_name": None, # e.g.: "kml-bbx-00187",
    "k8s_replicaset": None, # e.g.: "kml-bbx-00187-5585ff96d7",
    "k8s_pod_name": None, # e.g.: "kml-bbx-00187-5585ff96d7-gh7fh",
    }

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

def validate_kml_api(api_base, credentials):

    if api_base is None:
        logger.error(f"No valid KML API found ({api_base})")
        return False

    # Loop here many times with longer waits
    #   to ensure a blip in the RESP API doesnt kill the entire script

    wait_times = [2, 4, 8, 16, 32, 64]
    for waitsecs in wait_times:

        try:
            r = requests.get(f"{api_base}/ping",
                             auth=credentials)
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

def register_event_lifecycle(api_base, credentials, event_sub_type):

    payload = {
        "event_type": "LIFECYCLE",
        "event_sub_type": event_sub_type
        }
    payload.update(DEFAULT_EVENT_SIG)

    try:
        r = requests.post(f"{api_base}/admin/events/register", auth=credentials, json=payload)

    except Exception as e:
        logger.error(e)
        logger.error(payload)
        error_type, error, tb = sys.exc_info()
        logger.error(traceback.format_tb(tb))
        traceback.print_exc(file=sys.stdout)

def register_event_metrics(api_base, credentials, recs_received=None, recs_inf_success=None, recs_inf_failure=None, recs_inf_persisted=None, throughput_inf=None, throughput_e2e=None):

    payload = {
        "recs_received": recs_received,
        "recs_inf_success": recs_inf_success,
        "recs_inf_failure": recs_inf_failure,
        "recs_inf_persisted": recs_inf_persisted,
        "throughput_inf": throughput_inf,
        "throughput_e2e": throughput_e2e
        }
    payload.update(DEFAULT_EVENT_SIG)

    try:
        r = requests.post(f"{api_base}/admin/events/register", auth=credentials, json=payload)

    except Exception as e:
        logger.error(e)
        logger.error(payload)
        error_type, error, tb = sys.exc_info()
        logger.error(traceback.format_tb(tb))
        traceback.print_exc(file=sys.stdout)

if __name__ == '__main__':

    logger.info("Initializing Kinetica BlackBox SDK")

    # Things coming in from the environment via env-variables
    KML_API_BASE = grab_or_die("KML_API_BASE")
    KML_DEPL_ID = grab_or_die("KML_DEPL_ID")
    ZMQ_DEALER_HOST = grab_or_die("ZMQ_DEALER_HOST")
    ZMQ_DEALER_PORT = grab_or_die("ZMQ_DEALER_PORT")
    ZMQ_CONN_STR = f"tcp://{ZMQ_DEALER_HOST}:{ZMQ_DEALER_PORT}"
    DB_CONN_STR = grab_or_die("DB_CONN_STR")
    DB_USER = grab_or_die("DB_USER")
    DB_PASS = grab_or_die("DB_PASS")

    BLACKBOX_MULTIROW_INFER = False
    if "BLACKBOX_MULTIROW_INFER" in os.environ and os.environ["BLACKBOX_MULTIROW_INFER"].lower().strip()=="true":
        BLACKBOX_MULTIROW_INFER = True
        logger.info("   Employing Multi-Row Infer")
    else:
        logger.info("   Employing Single-Row (Traditional Mode) Infer")

    logger.info(f"   KML_API_BASE: {KML_API_BASE}")
    logger.info(f"   DB_CONN_STR: {DB_CONN_STR}")
    logger.info(f"   DB_USER: {DB_USER}")
    logger.info(f"   DB_PASS: *******")
    logger.info(f"   ZMQ_CONN_STR: {ZMQ_CONN_STR}")

    # Container auth for api
    if DB_USER and DB_PASS:
        if DB_USER.lower() != 'no_cred':
            credentials = (DB_USER, DB_PASS)
            logger.info("   DB Connection will be authenticated")
        else:
            credentials = None
            logger.info("   DB Connection will be w/o authentication (debug mode)")
    else:
        credentials = None
        logger.info("   DB Connection will be w/o authentication (debug mode)")


    register_event_lifecycle(api_base=KML_API_BASE, credentials=credentials, event_sub_type="INITIALIZING")


    # Things we default, but can capture in as environment variables
    be_quiet = True if (os.environ.get('be_quiet') and os.environ.get('be_quiet').upper()=="TRUE") else False
    if be_quiet:
        logger.setLevel(logging.ERROR)

    register_event_lifecycle(api_base=KML_API_BASE, credentials=credentials, event_sub_type="DEP_DETAILS_OBTAINING")
    dep_details_uri = f"{KML_API_BASE}/model/deployment/{KML_DEPL_ID}/view"
    logger.info(f"Deployment details from {dep_details_uri}, attempting connection...")
    if not validate_kml_api(KML_API_BASE, credentials):
        logger.error(f"Could not reach KML REST API for deployment details")
        sys.exit(1)
    logger.info(f"Deployment details from {dep_details_uri}, successfully connected")
    dep_details_resp = requests.get(dep_details_uri, auth=credentials)
    if (dep_details_resp.status_code == 404):
        logger.error(f"Could not find deployment with id {KML_DEPL_ID}")
        sys.exit(1)
    dep_details = dep_details_resp.json()
    logger.info(f"Deployment details from {dep_details_uri}, successfully obtained deployment details")

    if 'success' not in dep_details or not dep_details['success']:
        logger.error(f"Could not find live deployment with id {KML_DEPL_ID}")
        sys.exit(1)

    register_event_lifecycle(api_base=KML_API_BASE, credentials=credentials, event_sub_type="DEP_DETAILS_RECEIVED")

    bb_module = dep_details["response"]["item"]["base_model_inst"]["model_inst_config"]["blackbox_module"]
    bb_method = dep_details["response"]["item"]["base_model_inst"]["model_inst_config"]["blackbox_function"]
    schema_inbound = dep_details["response"]["item"]["model_dep_config"]["inp-tablemonitor"]["type_schema"]
    tbl_out_results = dep_details["response"]["item"]["model_dep_config"]["sink_table"]
    tbl_out_audit = dep_details["response"]["item"]["model_dep_config"]["out-tablemonitor"]["table_name"]
    output_record_list = dep_details["response"]["item"]["base_model_inst"]["model_inst_config"]["output_record_type"]
    outfields = [arec["col_name"] for arec in output_record_list]

    register_event_lifecycle(api_base=KML_API_BASE, credentials=credentials, event_sub_type="DEP_DETAILS_PROCESSED")

    logger.info(f"bb_module: {bb_module}")
    logger.info(f"bb_method: {bb_method}")
    logger.info(f"schema_inbound: {schema_inbound}")
    logger.info(f"tbl_out_results: {tbl_out_results}")
    logger.info(f"tbl_out_audit: {tbl_out_audit}")
    logger.info(f"Output fields: {len(outfields)}")
    for outf in outfields:
        logger.info(f"   Output field: {outf}")

    protected_fields = ["guid", "receive_dt", "process_start_dt", "process_end_dt"]
    # TODO: also protect input fields
    #protected_fields = infields + ["guid", "receive_dt", "process_start_dt", "process_end_dt"]

    schema_decoder = json.dumps(schema_inbound) #json.loads(json.dumps(schema_inbound))
    method_to_call = getattr(__import__(bb_module), bb_method)
    logger.info(f"Dynamically loaded function {bb_method} from module {bb_module} for lambda application")

    block_request_count = 0
    response_count=0
    default_results_subdict={
        "success":0,
        "errorlog": None,
        "errorstack": None,
        "process_end_dt": None
        }
    for outf in outfields:
        default_results_subdict[outf]=None

    # TODO Put these connection activities into a higher-level giant try-catch
    #    to re-connect upon failures
    # In case of a ZMQ connection failure
    register_event_lifecycle(api_base=KML_API_BASE, credentials=credentials, event_sub_type="ZMQ_CONNECTING")
    context = zmq.Context()
    socket = context.socket(zmq.PULL)
    socket.connect(ZMQ_CONN_STR)
    register_event_lifecycle(api_base=KML_API_BASE, credentials=credentials, event_sub_type="ZMQ_CONNECTED")

    # Prepare DB Connection
    register_event_lifecycle(api_base=KML_API_BASE, credentials=credentials, event_sub_type="DB_CONNECTING")
    cn_db = get_conn_db(DB_CONN_STR, DB_USER, DB_PASS)
    register_event_lifecycle(api_base=KML_API_BASE, credentials=credentials, event_sub_type="DB_CONNECTED")

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


    register_event_lifecycle(api_base=KML_API_BASE, credentials=credentials, event_sub_type="READY_TO_INFER")
    while True:

        ################################################
        # Multi-Row Inferencing Case
        ################################################

        if BLACKBOX_MULTIROW_INFER:

            try:
                logger.info("Awaiting inbound requests")

                mpr = socket.recv_multipart()
                block_request_count += 1

                parts_received = len(mpr)
                logger.info(f"Processing insert notification with {parts_received-1} frames, block request {block_request_count}")

                results_package_list = gpudb.GPUdbRecord.decode_binary_data(schema_decoder, mpr[1:])
                process_start_dt = datetime.datetime.now().isoformat(' ')[:-3]
                for mindex, results_package in enumerate(results_package_list):
                    response_count += 1
                    results_package_list[mindex].update(default_results_subdict)
                    results_package_list[mindex]["process_start_dt"] = process_start_dt

                outMaps = method_to_call(results_package_list)

                process_end_dt = datetime.datetime.now().isoformat(' ')[:-3]
                for mindex, results_package in enumerate(results_package_list):
                    # Protected fields cannot be overwritten by blackbox function
                    for pf in protected_fields:
                        if pf in outMaps[mindex]:
                            outMaps[mindex].pop(pf)

                    results_package_list[mindex].update(outMaps[mindex])
                    results_package_list[mindex]["process_end_dt"] = process_end_dt
                    results_package_list[mindex]["success"]=1

                _ = h_tbl_out_audit.insert_records(results_package_list)
                if h_tbl_out_results is None:
                    logger.info(f"Response sent back to DB audit table")
                else:
                    _ = h_tbl_out_results.insert_records(results_package_list)
                    logger.info(f"Response sent back to DB output table and audit table")

                # TODO: examine insert_status and determine if DB insert was a filure

                logger.info(f"Completed Processing block request {block_request_count}")

            except Exception as e:
                # TODO: As discussed at code review on 3 Jan 2019, push stack trace and input body to store_only field in output table
                logger.error(e)
                error_type, error, tb = sys.exc_info()
                logger.error(traceback.format_tb(tb))
                traceback.print_exc(file=sys.stdout)

        ################################################
        # Single-Row (Traditional) Inferencing Case
        ################################################

        else:

            try:
                logger.info("Awaiting inbound requests")

                mpr = socket.recv_multipart()
                block_request_count += 1

                parts_received = len(mpr)
                logger.info(f"Received inbound request number {block_request_count} with {parts_received-1} frames")
                #logger.info(f"Processing insert notification with {parts_received-1} frames, block request {block_request_count}")

                results_package_list = gpudb.GPUdbRecord.decode_binary_data(schema_decoder, mpr[1:])
                process_start_dt = datetime.datetime.now().isoformat(' ')[:-3]
                for mindex, results_package in enumerate(results_package_list):
                    response_count += 1
                    results_package_list[mindex].update(default_results_subdict)
                    results_package_list[mindex]["process_start_dt"] = process_start_dt

                for mindex, results_package in enumerate(results_package_list):
                    try:
                        outMap = method_to_call(results_package_list[mindex])
                        if not isinstance(outMap, list):
                            logger.warn ("Received lone dictionary function output, force listifying")
                            outMap = [outMap,]

                        # Protected fields cannot be overwritten by blackbox function
                        for pf in protected_fields:
                            if pf in outMap[0]:
                                outMap[0].pop(pf)

                        # TODO: Problem! This doesnt handle multi-out case!
                        results_package_list[mindex].update(outMap[0])
                        results_package_list[mindex]["success"]=1
                    except Exception as e:
                        logger.error(e)
                        error_type, error, tb = sys.exc_info()
                        logger.error(traceback.format_tb(tb))
                        traceback.print_exc(file=sys.stdout)
                        results_package_list[mindex]["errorstack"]="\n".join(traceback.format_tb(tb))
                        if e:
                            results_package_list[mindex]["errorlog"]=str(e)
                    results_package_list[mindex]["process_end_dt"] = datetime.datetime.now().isoformat(' ')[:-3]

                _ = h_tbl_out_audit.insert_records(results_package_list)
                if h_tbl_out_results is None:
                    logger.info(f"Response sent back to DB audit table")
                else:
                    _ = h_tbl_out_results.insert_records(results_package_list)
                    logger.info(f"Response sent back to DB output table and audit table")

                # TODO: examine insert_status and determine if DB insert was a filure

                logger.info(f"Completed Processing block request {block_request_count}")

            except Exception as e:
                # TODO: As discussed at code review on 3 Jan 2019, push stack trace and input body to store_only field in output table
                logger.error(e)
                error_type, error, tb = sys.exc_info()
                logger.error(traceback.format_tb(tb))
                traceback.print_exc(file=sys.stdout)

if __name__ == '__main__':
    main()

    # TODO: Really, we should *never* exit. So if we exit, that is a failure already
    # The only "exit" would be if we are terminated externally via REST API
    logger.warn("Exiting container. Hopefully this was user-initiated from REST API.")
    sys.exit(1)