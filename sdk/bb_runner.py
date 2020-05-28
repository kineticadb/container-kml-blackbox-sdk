import os
import sys
import time
import traceback
import json
import datetime
import logging
import copy
import logging
import pprint

import zmq
import gpudb
import requests
from requests.exceptions import ConnectionError

###############################################################################
# For use by SDK Clients
# Use this decorator if you wish to declare a black box function bulk capable

def bulk_infer_capable(func):
    def inner(inMap):
        return func(inMap)
    setattr(inner, 'BULK_INFER_CAPABLE', True)
    return inner
###############################################################################

logger = logging.getLogger("kml-bbx-sdk")
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handlerC = logging.StreamHandler()
handlerC.setFormatter(formatter)
if (logger.hasHandlers()):
    logger.handlers.clear()
logger.addHandler(handlerC)

# Build event signature
env_pod_name = os.environ.get('HOSTNAME')
env_dep_id = os.environ.get('KML_DEPL_ID')
pt = env_pod_name.split('-')
dep_name = '-'.join([pt[0], pt[1], pt[2]])

ZMQ_HEARTBEAT = 900

DEFAULT_EVENT_SIG = {"deployment_id": env_dep_id,
                     "deployment_name": dep_name,
                     "reporter_type": "WORKER",
                     "k8s_pod_name": env_pod_name}


# Grab environment variables or die trying
def grab_or_die(env_var_key):
    if env_var_key not in os.environ:
        logger.error(f"Could not find {env_var_key} environment "
                     f"variable. Cannot proceed.")
        sys.exit(1)
    return os.environ[env_var_key]


def get_tbl_handle(tbl_name, db, schema=None):
    #tbl_ref = tbl_name if not schema else f"{schema}.{tbl_name}"
    tbl_ref = tbl_name
    return gpudb.GPUdbTable(name=tbl_ref,
                            db=db,
                            use_multihead_io=True,
                            #  multihead_ingest_batch_size=10000,
                            flush_multi_head_ingest_per_insertion=True)


def get_conn_db(db_conn_str, db_user, db_pass):
    # Prepare DB Communications
    logger.info(f"Attempting to connect to DB at {db_conn_str} to push to {tbl_out_audit}")
    if db_user == 'no_cred' or db_pass == 'no_cred':
        cn_db = gpudb.GPUdb(encoding='BINARY',
                            host=db_conn_str,
                            primary_host=db_conn_str)
    else:
        cn_db = gpudb.GPUdb(encoding='BINARY',
                            host=db_conn_str,
                            primary_host=db_conn_str,
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


def phone_home_status(api_base, dep_id, credentials, target_status):
    if not target_status:
        raise ValueError("target_status cannot be null")

    if target_status not in ["RUNNING", "FAILED"]:
        raise ValueError("target_status must be [RUNNING|FAILED]")

    try:
        phone_home_loc = f"{api_base}/model/deployment/{dep_id}/setstatus"
        logger.info(f"Phoning home status {target_status} to {phone_home_loc}")
        r = requests.post(phone_home_loc,
                          auth=credentials,
                          json={"destination-state": target_status})

    except Exception as e:
        logger.error(e)
        error_type, error, tb = sys.exc_info()
        logger.error(traceback.format_tb(tb))
        traceback.print_exc(file=sys.stdout)


def register_event_lifecycle(api_base, credentials, event_sub_type):

    payload = {
        "event_type": "LIFECYCLE",
        "event_sub_type": event_sub_type,
    }

    payload.update(DEFAULT_EVENT_SIG)

    try:
        r = requests.post(f"{api_base}/admin/events/register",
                          auth=credentials,
                          json=payload)

    except Exception as e:
        logger.error(e)
        logger.error(payload)
        error_type, error, tb = sys.exc_info()
        logger.error(traceback.format_tb(tb))
        traceback.print_exc(file=sys.stdout)


def register_event_metrics(api_base, credentials, seq_id=None, recs_received=None,
                           recs_relayed=None, recs_inf_success=None,
                           recs_inf_failure=None, recs_inf_persisted=None,
                           throughput_inf=None, throughput_e2e=None):

    payload = {
        "event_type": "METRICS",
        "seq_id": seq_id,
        "recs_received": recs_received,
        "recs_relayed": None,
        "recs_inf_success": recs_inf_success,
        "recs_inf_failure": recs_inf_failure,
        "recs_inf_persisted": recs_inf_persisted,
        "throughput_inf": throughput_inf,
        "throughput_e2e": throughput_e2e
    }

    payload.update(DEFAULT_EVENT_SIG)

    try:
        r = requests.post(f"{api_base}/admin/events/register",
                          auth=credentials,
                          json=payload)

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
    SCHEMA_AUDIT = os.environ.get('SCHEMA_AUDIT', 'kml_audit')
    PERSIST_AUDIT = str(os.getenv('PERSIST_AUDIT', "TRUE")).upper()

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

    register_event_lifecycle(api_base=KML_API_BASE,
                             credentials=credentials,
                             event_sub_type="INITIALIZING")

    # Things we default, but can capture in as environment variables
    be_quiet = True if (os.environ.get('be_quiet') and os.environ.get('be_quiet').upper() == "TRUE") else False
    if be_quiet:
        logger.setLevel(logging.ERROR)

    register_event_lifecycle(api_base=KML_API_BASE,
                             credentials=credentials,
                             event_sub_type="DEP_DETAILS_OBTAINING")
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
    logger.info(f"Deployment details from {dep_details_uri}, "
                f"successfully obtained deployment details")

    if 'success' not in dep_details or not dep_details['success']:
        logger.error(f"Could not find live deployment with id {KML_DEPL_ID}")
        sys.exit(1)

    register_event_lifecycle(api_base=KML_API_BASE,
                             credentials=credentials,
                             event_sub_type="DEP_DETAILS_RECEIVED")

    bb_module = dep_details["response"]["item"]["base_model_inst"]["model_inst_config"]["blackbox_module"]
    bb_method = dep_details["response"]["item"]["base_model_inst"]["model_inst_config"]["blackbox_function"]
    schema_inbound = dep_details["response"]["item"]["model_dep_config"]["inp-tablemonitor"]["type_schema"]
    tbl_out_results = dep_details["response"]["item"]["model_dep_config"]["sink_table"]
    tbl_out_audit = dep_details["response"]["item"]["model_dep_config"]["out-tablemonitor"]["table_name"]
    output_record_list = dep_details["response"]["item"]["base_model_inst"]["model_inst_config"]["output_record_type"]
    outfields = [arec["col_name"] for arec in output_record_list]

    register_event_lifecycle(api_base=KML_API_BASE,
                             credentials=credentials,
                             event_sub_type="DEP_DETAILS_PROCESSED")

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
    # protected_fields = infields + ["guid", "receive_dt", "process_start_dt", "process_end_dt"]

    schema_decoder = json.dumps(schema_inbound)
    method_to_call = getattr(__import__(bb_module), bb_method)
    logger.info(f"Dynamically loaded function {bb_method} from "
                f"module {bb_module} for lambda application")

    BLACKBOX_MULTIROW_INFER = False
    if 'BULK_INFER_CAPABLE' in dir(method_to_call):
        if getattr(method_to_call, 'BULK_INFER_CAPABLE'):
            BLACKBOX_MULTIROW_INFER = True

    if BLACKBOX_MULTIROW_INFER:
        logger.info("   Employing Bulk Infer")
    else:
        logger.info("   Employing Single-Row (Traditional Mode) Infer")

    block_request_count = 0
    response_count = 0
    default_results_subdict = {
        "success": 0,
        "errorlog": None,
        "errorstack": None,
        "process_end_dt": None
    }
    for outf in outfields:
        default_results_subdict[outf] = None

    # TODO Put these connection activities into a higher-level giant try-catch
    #    to re-connect upon failures
    # In case of a ZMQ connection failure
    register_event_lifecycle(api_base=KML_API_BASE,
                             credentials=credentials,
                             event_sub_type="ZMQ_CONNECTING")

    logger.info('ZMQ socket: Configuring')
    context = zmq.Context()
    socket = context.socket(zmq.PULL)
    socket.setsockopt(zmq.TCP_KEEPALIVE, 1)
    socket.setsockopt(zmq.TCP_KEEPALIVE_IDLE, ZMQ_HEARTBEAT)
    socket.setsockopt(zmq.TCP_KEEPALIVE_INTVL, ZMQ_HEARTBEAT)
    logger.info(f"ZMQ socket: Keep-alive heartbeat set to {ZMQ_HEARTBEAT} sec")
    logger.info('ZMQ socket: Succesfully configured')
    socket.connect(ZMQ_CONN_STR)
    logger.info('ZMQ socket: Successfully connected')

    register_event_lifecycle(api_base=KML_API_BASE,
                             credentials=credentials,
                             event_sub_type="ZMQ_CONNECTED")

    # Prepare DB Connection
    register_event_lifecycle(api_base=KML_API_BASE,
                             credentials=credentials,
                             event_sub_type="DB_CONNECTING")
    cn_db = get_conn_db(DB_CONN_STR, DB_USER, DB_PASS)
    register_event_lifecycle(api_base=KML_API_BASE,
                             credentials=credentials,
                             event_sub_type="DB_CONNECTED")

    # [Re]Establish table handles

    h_tbl_out_audit = get_tbl_handle(tbl_out_audit, db=cn_db, schema=SCHEMA_AUDIT)
    h_tbl_out_results = None
    logger.info(f"DB Results Table {tbl_out_results}")
    if tbl_out_results and tbl_out_results != "NOT_APPLICABLE":
        h_tbl_out_results = gpudb.GPUdbTable(
            name=tbl_out_results,
            db=cn_db,
            use_multihead_io=True,
            #  multihead_ingest_batch_size=10000,
            flush_multi_head_ingest_per_insertion=True
        )
        logger.info(f"Established connection to sink table")
        logger.info(f"All results will be persisted to both Audit {tbl_out_audit} "
                    f"and output DB Tables {tbl_out_results}")
    else:
        logger.info(f"All results will be persisted to Audit DB "
                    f"Table {tbl_out_audit} only")

    register_event_lifecycle(api_base=KML_API_BASE,
                             credentials=credentials,
                             event_sub_type="READY_TO_INFER")

    phone_home_status(api_base=KML_API_BASE,
                      dep_id=KML_DEPL_ID,
                      credentials=credentials,
                      target_status="RUNNING")

    record_type = gpudb.RecordType.from_type_schema("", schema_decoder, {})

    while True:

        ################################################
        # Multi-Row Inferencing Case
        ################################################

        if BLACKBOX_MULTIROW_INFER:

            # Reset all metrics until we get the next batch
            seq_id = None
            recs_received = None

            # with multi-row inference, there is no easy way to discern success
            # or failure, though one could assume all-or-none
            recs_inf_success = -1
            recs_inf_failure = -1
            recs_inf_persisted = None
            throughput_inf = None
            throughput_e2e = None

            try:
                logger.info("Awaiting inbound requests")

                mpr = socket.recv_multipart()
                block_request_count += 1
                seq_id = block_request_count

                t_start_e2e = time.time()

                parts_received = len(mpr)
                logger.info(f"Received inbound request number {block_request_count} "
                            f"with {parts_received-1} frames")
                recs_received = parts_received-1

                results_package_list = [
                    dict(x) for x in gpudb.GPUdbRecord.decode_binary_data(
                        record_type,
                        mpr[1:]
                    )
                ]

                process_start_dt = datetime.datetime.now().isoformat(' ')[:-3]
                for mindex, results_package in enumerate(results_package_list):
                    response_count += 1
                    results_package_list[mindex].update(default_results_subdict)
                    results_package_list[mindex]["process_start_dt"] = process_start_dt

                t_start_inf = time.time()
                outMaps = method_to_call(copy.deepcopy(results_package_list))
                t_end_inf = time.time()

                # we can assume everything was successful, a moderately OK assumption
                recs_inf_success = recs_received
                recs_inf_failure = 0

                process_end_dt = datetime.datetime.now().isoformat(' ')[:-3]
                for mindex, results_package in enumerate(results_package_list):
                    # Protected fields cannot be overwritten by blackbox function
                    for pf in protected_fields:
                        if pf in outMaps[mindex]:
                            outMaps[mindex].pop(pf)

                    results_package_list[mindex].update(outMaps[mindex])
                    results_package_list[mindex]["process_end_dt"] = process_end_dt
                    results_package_list[mindex]["success"] = 1

                if PERSIST_AUDIT != "FALSE":
                    _ = h_tbl_out_audit.insert_records(results_package_list)
                if h_tbl_out_results is None:
                    logger.info(f"Response sent back to DB audit table")
                else:
                    _ = h_tbl_out_results.insert_records(results_package_list)
                    logger.info(f"Response sent back to DB output table and audit table")

                t_end_e2e = time.time()

                # TODO: actually grab this from insert_records return values, dont assume
                recs_inf_persisted = len(results_package_list)

                throughput_inf = int(round(1000*(t_end_inf - t_start_inf)))
                throughput_e2e = int(round(1000*(t_end_e2e - t_start_e2e)))

                # TODO: examine insert_status and determine if DB insert was a filure

                logger.info(f"Completed Processing block request "
                            f"{block_request_count} with inference: "
                            f"{throughput_inf}ms on e2e: {throughput_e2e}ms")

            except Exception as e:
                # TODO: As discussed at code review on 3 Jan 2019, push stack trace and input body to store_only field in output table
                logger.error(e)
                error_type, error, tb = sys.exc_info()
                logger.error(traceback.format_tb(tb))
                traceback.print_exc(file=sys.stdout)

            register_event_metrics(
                api_base=KML_API_BASE,
                credentials=credentials,
                seq_id=seq_id,
                recs_received=recs_received,
                recs_relayed=None,
                recs_inf_success=recs_inf_success,
                recs_inf_failure=recs_inf_failure,
                recs_inf_persisted=recs_inf_persisted,
                throughput_inf=throughput_inf,
                throughput_e2e=throughput_e2e
            )

        ################################################
        # Single-Row (Traditional) Inferencing Case
        ################################################

        else:

            # Reset all metrics until we get the next batch
            seq_id = None
            recs_received = None
            recs_inf_success = None
            recs_inf_failure = None
            recs_inf_persisted = None
            throughput_inf = None
            throughput_e2e = None

            try:
                logger.info("Awaiting inbound requests")

                mpr = socket.recv_multipart()
                block_request_count += 1
                seq_id = block_request_count

                t_start_e2e = time.time()

                parts_received = len(mpr)
                logger.info(f"Received inbound request number {block_request_count} "
                            f"with {parts_received-1} frames")
                recs_received = parts_received-1

                results_package_list = [
                    dict(x) for x in gpudb.GPUdbRecord.decode_binary_data(
                        record_type,
                        mpr[1:]
                    )
                ]

                process_start_dt = datetime.datetime.now().isoformat(' ')[:-3]
                for mindex, results_package in enumerate(results_package_list):
                    response_count += 1
                    results_package_list[mindex].update(default_results_subdict)
                    results_package_list[mindex]["process_start_dt"] = process_start_dt

                recs_inf_failure = 0
                t_start_inf = time.time()
                for mindex, results_package in enumerate(results_package_list):
                    try:
                        outMap = method_to_call(
                            copy.deepcopy(results_package_list[mindex])
                        )
                        if not isinstance(outMap, list):
                            # TODO: Consider force exceptioning on this case and
                            # forcing users to fix this
                            #  logger.warn ("Received lone dictionary function output, "
                            #               "force listifying")
                            outMap = [outMap,]

                        logger.info("Outputs Received")
                        logger.info(pprint.pformat(outMap, indent=4))
                        # Loop, in case of multi-out scenarios
                        for outMapItem in outMap:
                            # Protected fields cannot be overwritten by blackbox function
                            for pf in protected_fields:
                                if pf in outMapItem:
                                    outMapItem.pop(pf)

                            # TODO: Problem! This doesnt handle multi-out case!
                            results_package_list[mindex].update(outMapItem)
                        results_package_list[mindex]["success"] = 1
                    except Exception as e:
                        recs_inf_failure += 1
                        logger.error(e)
                        error_type, error, tb = sys.exc_info()
                        logger.error(traceback.format_tb(tb))
                        traceback.print_exc(file=sys.stdout)
                        results_package_list[mindex]["errorstack"] = "\n".join(traceback.format_tb(tb))
                        if e:
                            results_package_list[mindex]["errorlog"] = str(e)
                    results_package_list[mindex]["process_end_dt"] = datetime.datetime.now().isoformat(' ')[:-3]
                logger.info("Final persistable")
                logger.info(pprint.pformat(results_package_list, indent=4))

                t_end_inf = time.time()

                if PERSIST_AUDIT != "FALSE":
                    _ = h_tbl_out_audit.insert_records(results_package_list)
                if h_tbl_out_results is None:
                    logger.info(f"Response sent back to DB audit table")
                else:
                    _ = h_tbl_out_results.insert_records(results_package_list)
                    logger.info(f"Response sent back to DB output table and audit table")
                t_end_e2e = time.time()

                # TODO: actually grab this from insert_records return values, dont assume
                recs_inf_persisted = len(results_package_list)
                recs_inf_success = recs_received - recs_inf_failure

                throughput_inf = int(round(1000*(t_end_inf - t_start_inf)))
                throughput_e2e = int(round(1000*(t_end_e2e - t_start_e2e)))

                # TODO: examine insert_status and determine if DB insert was a failure

                logger.info(f"Completed Processing block request {block_request_count} "
                            f"with inference: {throughput_inf}ms on e2e: "
                            f"{throughput_e2e}ms")

            except Exception as e:
                # TODO: As discussed at code review on 3 Jan 2019, push stack
                # trace and input body to store_only field in output table
                logger.error(e)
                error_type, error, tb = sys.exc_info()
                logger.error(traceback.format_tb(tb))
                traceback.print_exc(file=sys.stdout)

            register_event_metrics(
                api_base=KML_API_BASE,
                credentials=credentials,
                seq_id=seq_id,
                recs_received=recs_received,
                recs_relayed=None,
                recs_inf_success=recs_inf_success,
                recs_inf_failure=recs_inf_failure,
                recs_inf_persisted=recs_inf_persisted,
                throughput_inf=throughput_inf,
                throughput_e2e=throughput_e2e
            )


#  if __name__ == '__main__':
#      main()

#      # TODO: Really, we should *never* exit. So if we exit, that is a failure already
#      # The only "exit" would be if we are terminated externally via REST API
#      logger.warn("Exiting container. Hopefully this was user-initiated from REST API.")
#      sys.exit(1)
