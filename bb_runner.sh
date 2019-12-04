#!/bin/bash
set -ex

# Running the primary model runner and passing in all arguments
python -m sdk.bb_runner_batched 2>&1 | tee bbox.log

# We should never really get here
sleep 1000