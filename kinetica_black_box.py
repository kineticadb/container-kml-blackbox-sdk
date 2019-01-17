import os
import sys
import json
import pprint
import collections
import traceback
import datetime
import time

import zmq
import gpudb

import kmllogger
logger = kmllogger.attach_log(module="kml-bbox-sdk", log_name='kml', debug=True)


class KineticaBlackBox(object):
    """Kinetica black box class."""

    socket = None
    schema_inbound = None
    schema_outbound = None
    sink_table = None

    def __init__(self, bb_module, bb_method,
                 schema_inbound, schema_outbound,
                 zmq_dealer_host, zmq_dealer_port,
                 db_table, db_host = "127.0.0.1", db_port = "9191",
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
        :param db_table:
        :type db_table: str
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
        logger.info(f"db_table: {db_table}")
        logger.info(f"db_host: {db_host}")
        logger.info(f"db_port: {db_port}")
        logger.info(f"db_user: {db_user}")
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
        logger.info(f"Attempting to connect to DB at {db_host}:{db_port} to push to {db_table}")
        if db_user == 'no_cred' or db_pass == 'no_cred':
            db=gpudb.GPUdb(encoding='BINARY',
                           host=db_host,
                           port=db_port)
        else:
            db=gpudb.GPUdb(encoding='BINARY',
                           host=db_host,
                           port=db_port,
                           username=db_user,
                           password=db_pass)

        self.sink_table = gpudb.GPUdbTable(name = db_table, db = db)
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

        response_count=0
        while True:

            mpr = self.socket.recv_multipart()
            #if mpr[0].decode() != topicfilter:
            #    print(f"Inbound filter {mpr[0]} does not match subscribed filter {topicfilter}")

            parts_received = len(mpr)
            logger.info(f"Processing insert notification with {parts_received-1} frames")
            
            audit_records_insert_queue=[]
            for mindex, m in enumerate(mpr[1:]):                    
                inference_inbound_payload=gpudb.GPUdbRecord.decode_binary_data(schema_decoder, m)[0]
                response_count=response_count+1

                # wipe out all previous results
                entity_datum = collections.OrderedDict()
                logger.info(f"Processing frame {1+mindex} of {parts_received}: Message count # {response_count} {inference_inbound_payload['guid']}")

                # TODO: per code review w/ Eli 2 Jan 2019, this is unnecessary
                #for afield in outfields:
                #    entity_datum[afield["name"]]=None
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

            insert_status=self.sink_table.insert_records(audit_records_insert_queue)

            # TODO: examine insert_status and determine if DB insert was a filure
            logger.info(f"Response sent back to DB with status")
    # end run

# end class KineticaBlackBox
