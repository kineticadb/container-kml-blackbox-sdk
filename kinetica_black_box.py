import os
import sys
import json
import pprint
import collections
import traceback
import datetime
import time
import uuid
import zmq
import gpudb
import datetime

import kmllogger
logger = kmllogger.attach_log(module="kml-bbox-sdk", log_name='kml', debug=True)


class KineticaBlackBox(object):
    """Kinetica black box class."""

    socket = None
    schema_inbound = None
    schema_outbound = None
    sink_table_audit = None
    sink_table_results = None

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
        #logger.info("Listening for incoming requests on topic: %s via %s" % (topicfilter,topic_source))
        self.socket.connect(zmq_dealer_uri)
        #self.socket.setsockopt_string(zmq.SUBSCRIBE, topicfilter)
    # end __init__


    def run(self):
        """Run the black box."""

        schema_decoder = json.dumps(json.loads(self.schema_inbound))
        outfields = json.loads(self.schema_outbound)["fields"]

        method_to_call = getattr(__import__(self.bb_module), self.bb_method)
        logger.info(f"Dynamically loaded function {self.bb_method} from module {self.bb_module} for lambda application")

        block_request_count = 0
        response_count=0
        while True:
            try:

                mpr = self.socket.recv_multipart()
                block_request_count += 1

                parts_received = len(mpr)
                logger.info(f"Processing insert notification with {parts_received-1} frames, block request {block_request_count}")
                
                audit_records_insert_queue=[]
                for mindex, m in enumerate(mpr[1:]):                    
                    inference_inbound_payload=gpudb.GPUdbRecord.decode_binary_data(schema_decoder, m)[0]
                    response_count += 1

                    # wipe out all previous results
                    entity_datum = collections.OrderedDict()
                    if 'guid' not in inference_inbound_payload:
                        inference_inbound_payload['guid'] = str(uuid.uuid4())
                        inference_inbound_payload['receive_dt'] = datetime.datetime.now().replace(microsecond=100).isoformat(' ')[:-3]
                        logger.info(f"Assigned GUID {inference_inbound_payload['guid']} to serial-free inbound")
                    logger.info(f"Processing frame {1+mindex} of {parts_received}: Message count # {response_count} {inference_inbound_payload['guid']}")

                    # TODO: per code review w/ Eli 2 Jan 2019, this is unnecessary
                    for afield in outfields:
                        entity_datum[afield["name"]]=None
                    # TODO: per code review w/ Eli 2 Jan 2019, this is unnecessary

                    entity_datum["success"]=0 # we start with the assumption of failure                

                    process_start_dt=datetime.datetime.now().replace(microsecond=100).isoformat(' ')[:-3]
                    logger.debug("\tDecoded task %s off wire for inference" % inference_inbound_payload["guid"])
                    for k,v in inference_inbound_payload.items():
                        logger.debug("\t%s: %s" % (k,v))

                    # by default send back all inputs as well as our calculated outputs
                    for k,v in inference_inbound_payload.items():
                        entity_datum[k]=v

                    # -------------------------------------------------------------------------
                    # BLACKBOX INTERACTION - **STARTING**

                    inMap = inference_inbound_payload
                    logger.debug ("\tSending to blackbox:")
                    for ki,vi in inMap.items():
                        logger.debug("\t %s: %s" % (ki,vi))

                    inference_success=False
                    try:
                        outMap = method_to_call(inMap)
                        inference_success=True

                        logger.debug ("\tResults received from blackbox:")
                        for ko,vo in outMap.items():
                            logger.debug("\t %s: %s" % (ko,vo))
                        logger.debug ("\t>> Completed")

                        for k,v in outMap.items():
                            entity_datum[k]=v
                    except Exception as e:
                        # TODO: As discussed at code review on 3 Jan 2019, push stack trace and input body to store_only field in output table
                        logger.error(e)
                        error_type, error, tb = sys.exc_info()
                        logger.error(traceback.format_tb(tb))
                        traceback.print_exc(file=sys.stdout)
                        entity_datum["errorlog"]="\n".join(traceback.format_tb(tb))

                    # -------------------------------------------------------------------------
                    # BLACKBOX INTERACTION - **COMPLETED**

                    process_end_dt=datetime.datetime.now().replace(microsecond=100).isoformat(' ')[:-3]
                    entity_datum["process_start_dt"]=process_start_dt
                    entity_datum["process_end_dt"]=process_end_dt
                    if inference_success:
                        entity_datum["success"]=1
                    else:
                        entity_datum["success"]=0

                    logger.debug("Sending response back to DB:")
                    logger.debug(entity_datum)
                    audit_records_insert_queue.append(entity_datum)

                _ = self.sink_table_audit.insert_records(audit_records_insert_queue)
                if self.sink_table_results is None:
                    logger.info(f"Response sent back to DB audit table")
                else:
                    _ = self.sink_table_results.insert_records(audit_records_insert_queue)
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
