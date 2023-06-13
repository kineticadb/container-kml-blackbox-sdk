#!/bin/bash

#
# Kinetica Blackbox model container start script.
# (c) 2023 Kinetica DB, Inc.
#
# [Do not modify]
#

set -ex

# Running the primary model runner and passing in all arguments
python -m sdk.bb_runner 2>&1

# Keep container alive for debugging if something goes wrong
sleep 1000