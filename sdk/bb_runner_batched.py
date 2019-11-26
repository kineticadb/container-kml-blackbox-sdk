import os
import sys
import json
import pprint
import collections
import traceback
import datetime
import time
import uuid
import datetime
import copy
import logging

import zmq
import gpudb

logger = logging.getLogger("kml-bbox-sdk")
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handlerC = logging.StreamHandler(sys.stdout)
handlerC.setFormatter(formatter)
logger.addHandler(handlerC)

class KineticaBlackBox(object):
    """Kinetica black box class."""

    socket = None
    schema_inbound = None
    schema_outbound = None
    sink_table_audit = None
    sink_table_results = None
    be_quiet = False

    def __init__(self, bb_module, bb_method,
                 schema_inbound, schema_outbound,
                 zmq_dealer_host, zmq_dealer_port,
                 db_table_audit, db_table_results, db_conn_str,
                 db_user = "", db_pass = "", be_quiet = False ):
        """Construct a new KineticaBlackBox object.

        :param bb_module:
        :type bb_module: dict
        :param bb_method:
        :type bb_method: dict
        :param schema_inbound:
        :type schema_inbound: str
        :param schema_outbound:
        :type schema_outbound: str
        :param zmq_dealer_host:
        :type zmq_dealer_host: str
        :param zmq_dealer_port:
        :type zmq_dealer_port: str
        :param db_table_audit:
        :type db_table_audit: str
        :param db_table_results:
        :type db_table_results: str
        :param db_host: Default "127.0.0.1".
        :type db_host: str
        :param db_port: Default "9191".
        :type db_port: str
        :param db_user: optional
        :type db_user: str
        :param db_pw: optional
        :type db_pw: str

        """

        logger.info("Initializing KineticaBlackBox")
        logger.info(f"zmq_dealer_host: {zmq_dealer_host}")
        logger.info(f"zmq_dealer_port: {zmq_dealer_port}")
        logger.info(f"db_table a: {db_table_audit}")
        logger.info(f"db_table r: {db_table_results}")
        logger.info(f"db_conn_str: {db_conn_str}")
        logger.info(f"db_user: {db_user}")
        logger.info(f"db_pass: *******")
        logger.info(f"schema_inbound: {schema_inbound}")
        logger.info(f"schema_outbound: {schema_outbound}")
        logger.info(f"bb_module: {bb_module}")
        logger.info(f"bb_method: {bb_method}")

        if be_quiet:
            import logging
            logger.setLevel(logging.INFO)

        self.be_quiet = be_quiet
        self.schema_inbound = schema_inbound
        self.schema_outbound = schema_outbound

        self.bb_module = bb_module
        self.bb_method = bb_method

        # Prepare DB Communications
        logger.info(f"Attempting to connect to DB at {db_conn_str} to push to {db_table_audit}")
        if db_user == 'no_cred' or db_pass == 'no_cred':
            db=gpudb.GPUdb(encoding='BINARY',
                           host=db_conn_str)
        else:
            db=gpudb.GPUdb(encoding='BINARY',
                           host=db_conn_str,
                           username=db_user,
                           password=db_pass)

        self.sink_table_audit = gpudb.GPUdbTable(name = db_table_audit, db = db)

        logger.info(f"DB Results Table {db_table_results}")
        if db_table_results == "NOT_APPLICABLE":
            logger.info(f"All results will be persisted to Audit DB Table {db_table_audit}")
            self.sink_table_results = None
        else:
            self.sink_table_results = gpudb.GPUdbTable(name = db_table_results, db = db)
            logger.info(f"Established connection to sink table")
            logger.info(self.sink_table_results)

        logger.info(self.sink_table_results)
        if self.sink_table_results is None:
            logger.info(f"All results will be persisted to Audit DB Table only")
        else:
            logger.info(f"All results will be persisted to both Audit and output DB Tables {db_table_results}")

        logger.info("Prepping response with with schema")
        logger.info(json.dumps(json.loads(schema_outbound)))

        # Prepare ZMQ Communications
        zmq_dealer_uri = f"tcp://{zmq_dealer_host}:{zmq_dealer_port}"
        context = zmq.Context()
        self.socket = context.socket(zmq.PULL)
        self.socket.connect(zmq_dealer_uri)
    # end __init__

    def run(self):
        """Run the black box."""

        schema_decoder = json.dumps(json.loads(self.schema_inbound))
        outfields = json.loads(self.schema_outbound)["fields"]

        method_to_call = getattr(__import__(self.bb_module), self.bb_method)
        logger.info(f"Dynamically loaded function {self.bb_method} from module {self.bb_module} for lambda application")

        block_request_count = 0
        response_count=0
        default_results_subdict={
            "success":0,
            "errorlog": None,
            "errorstack": None
            }

        while True:
            try:
                mpr = self.socket.recv_multipart()
                block_request_count += 1

                parts_received = len(mpr)
                logger.info(f"Processing insert notification with {parts_received-1} frames, block request {block_request_count}")

                results_package_list = gpudb.GPUdbRecord.decode_binary_data(schema_decoder, mpr[1:])
                for mindex, results_package in enumerate(results_package_list):
                    response_count += 1
                    results_package_list[mindex].update(default_results_subdict)
                    results_package_list[mindex]["process_start_dt"]=datetime.datetime.now().replace(microsecond=100).isoformat(' ')[:-3]
                    results_package_list[mindex]["process_end_dt"]=None
                    if 'guid' not in results_package_list[mindex]:
                        results_package_list[mindex]['guid'] = str(uuid.uuid4())
                        results_package_list[mindex]['receive_dt'] = datetime.datetime.now().replace(microsecond=100).isoformat(' ')[:-3]
                outMaps = method_to_call(results_package_list)

                for mindex, results_package in enumerate(results_package_list):
                    results_package_list[mindex]["process_end_dt"]=datetime.datetime.now().replace(microsecond=100).isoformat(' ')[:-3]
                    results_package_list[mindex].update(outMaps[mindex])
                    results_package_list[mindex]["success"]=1

                _ = self.sink_table_audit.insert_records(results_package_list)
                if self.sink_table_results is None:
                    logger.info(f"Response sent back to DB audit table")
                else:
                    _ = self.sink_table_results.insert_records(results_package_list)
                    logger.info(f"Response sent back to DB output table and audit table")

                # TODO: examine insert_status and determine if DB insert was a filure

                logger.info(f"Completed Processing block request {block_request_count}")

            except Exception as e:
                # TODO: As discussed at code review on 3 Jan 2019, push stack trace and input body to store_only field in output table
                logger.error(e)
                error_type, error, tb = sys.exc_info()
                logger.error(traceback.format_tb(tb))
                traceback.print_exc(file=sys.stdout)

    # end run

# end class KineticaBlackBox


