#!/bin/bash
set -ex

# Running the primary model runner and passing in all arguments
python -m bb_runner \
    --bbx-module $BLACKBOX_MODULE \
    --bbx-function $BLACKBOX_FUNCTION \
    --db-host $DB_HOST \
    --db-port $DB_PORT \
    --db-user $DB_USER \
    --db-pass $DB_PASS \
    --db-table $DB_TABL \
    --zmq-host $ZMQ_HOST \
    --zmq-port $ZMQ_PORT \
    --zmq-topic $ZMQ_TOPC \
    --schema-inbound $SCHEMA_INBOUND  \
    --schema-outbound $SCHEMA_OUTBOUND \
    2>&1 | tee bbox.log

#--quiet -- this is optional to reduce standard output