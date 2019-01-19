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
    --db-table-audit $DB_TABL_AUDIT \
    --db-table-results $DB_TABL_RESULTS \
    --zmq-dealer-host $ZMQ_DEALER_HOST \
    --zmq-dealer-port $ZMQ_DEALER_PORT \
    --schema-inbound $SCHEMA_INBOUND  \
    --schema-outbound $SCHEMA_OUTBOUND \
    --quiet
    2>&1 | tee bbox.log

#--quiet -- this is optional to reduce standard output