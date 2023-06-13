"""Kinetica Blackbox example usage functions.

Demonstration module with demonstrations of basic SDK
functionality including:

    row-by-row inference
    bulk inference
    one-to-many multirow inference output
    environment variable usage
    etc.

Kinetica Blackbox Model
(c) 2023 Kinetica DB, Inc.

"""

import os
import time
import random

import pandas as pd

from sdk.bb_runner import bulk_infer_capable


def basic_example(inputs):
    """Demonstrate basic row-by-row calculation."""

    f1 = int(inputs['figure1'])
    f2 = int(inputs['figure2'])
    mylabel = inputs['mylabel']

    outputs = {
        'sum': f1 + f2,
        'product': f1 * f2,
        'max': max([f1, f2]),
        'suminwords': f"{mylabel} {str(int(f1 + f2))}"
    }

    return outputs


@bulk_infer_capable
def bulk_infer_example(inputs):
    """Demonstrate batched variant for inputs."""

    # Requires the "bulk_infer_capable" decorator (see module input statement at top)

    # Inputs is an array of dicts
    df = pd.DataFrame(inputs)
    df['figure1_numeric'] = pd.to_numeric(df['figure1'])
    df['figure2_numeric'] = pd.to_numeric(df['figure2'])

    # Calculations
    df['sum'] = df['figure1_numeric'] + df['figure2_numeric']
    df['product'] = df['figure1_numeric'] * df['figure2_numeric']
    df['max'] = df[['figure1_numeric', 'figure2_numeric']].max(axis=1)
    df['suminwords'] = f"{df['mylabel']} {df['sum'].astype(str)}"

    # Remove the inputs from the data frame
    del df['figure1_numeric']
    del df['figure2_numeric']

    return df.to_dict('records')


def multi_out_example(inputs):
    """Demonstrate multiple outputs from one input record."""

    f1 = int(inputs['figure1'])
    f2 = int(inputs['figure2'])

    # Generate, in this example, 4 output rows for each input
    # Outputs is now a list of dicts
    outputs = [
        {
            'operation': 'sum',
            'result': f1 + f2
        },
        {
            'operation': 'product',
            'result': f1 * f2
        },
        {
            'operation': 'min',
            'result': min([f1, f2])
        },
        {
            'operation': 'max',
            'result': max([f1, f2])
        }
    ]

    return outputs


def custom_multi_out_example(inputs):
    """Demonstrate multi-row output triggerd with flag in data."""

    # Default is one row in, one row out
    rows_out = 1

    # If boolean "multiout" is set then generate more than 1 output rows per input
    if inputs.get('multiout') and inputs['multiout'].lower() == 'true':
        rows_out = 2
    outputs = inputs

    return [
        outputs for _ in range(rows_out)
    ]


def env_var_example(inputs):
    """Demonstrate use of environment variables."""

    f1 = int(inputs['figure1'])
    f2 = int(inputs['figure2'])

    # Read environment variables from the container
    if 'ENVVAR1' not in os.environ:
        raise Exception('Missing environment variable ENVVAR1')
    var1 = os.environ['ENVVAR1']

    if 'ENVVAR2' not in os.environ:
        raise Exception('Missing environment variable ENVVAR2')
    var2 = os.environ['ENVVAR2']

    outputs = {
        'sum': f1 + f2,
        'product': f1 * f2,
        'max': max([f1, f2]),
        'greeting': f"{var1} {var2}"
    }

    return outputs


def timer_example(inputs):
    """Demonstrate performance timer."""

    f1 = int(inputs['figure1'])
    f2 = int(inputs['figure2'])
    answer = 0

    # Determine how long each inference took
    t0 = time.time()
    for _ in range(random.randint(1, 5)):
        answer = f1 + f2
        time.sleep(1)
    t1 = time.time()

    outputs = {
        'inference': answer,
        'compute_time': t1 - t0
    }

    return outputs


def crash_example(inputs):
    """Demonstrate crash within the model function."""

    record = inputs['text']

    # Generate stacktrace in the output table
    if 'crash now' in record:
        raise Exception('Intentional failure in model function!')
    else:
        outputs = {'text': record}

    return outputs
