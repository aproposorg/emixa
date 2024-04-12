#!/usr/bin/env python3

import sys
import os

from emixa.characterization import characterize
from emixa.function import funcgen
from emixa.visualization import visualize
from emixa.util import _info, _warning, _error

# TODO Implement support for multiple different error modeling strategies in the random characterization flows.
#      And figure out if the regression strategy is any good.
#
# TODO Implement support for passing named parameters to the Scala test.
#
# TODO Implement support for different bit-width operands in multipliers.
#
# TODO Implement support for defining default arguments in tests.

def emixa(args) -> None:
    """
    Error Modeling of Inexact Arithmetic (EMIXA)

    This function takes positional arguments as follows:
    - args[0] the name of the test
    - args[1:] (optional) the parameters to pass to the test
    If the first of these arguments is missing, a ValueError exception is raised.

    In addition to these, it supports the following command line arguments:
    - '-f' or '--function' that takes no arguments
    - '-p' or '--plot' that takes no arguments
    - '-v' or '--verbose' that takes no arguments
    If none of these arguments is passed, emixa performs no characterization.

    For example, assuming a test 'ApproxAdderSpec' is defined to take two integer
    inputs, call the function as follows:
    >>> from emixa import emixa
    >>> emixa(['-f', '-d=4', 'ApproxAdderSpec', 32, 8])

    Or from the command line as follows:
    >>> ./emixa.py [-f[unction]] [-p[lot]] [-v[erbose]] ApproxAdderSpec 32 8
    
    Any additional parameters beyond those required by the specified test are
    ignored and discarded. Integer arguments can be passed as ranges in the 
    format of start:stop[:by] denoting the range [start:stop] as follows:
    >>> ./emixa.py [-f[unction]] [-p[lot]] [-v[erbose]] ApproxAdderSpec 16:33 8
    """
    # Capture any potential arguments to the tests
    kvargmap = {}
    for kvarg in filter(lambda arg: arg.startswith('-'), args):
        key = kvarg.lower().replace('-', '')
        if key == 'h' or key == 'help':
            kvargmap['help'] = True
        elif key == 'f' or key == 'function':
            kvargmap['function'] = True
        elif key == 'p' or key == 'plot':
            kvargmap['plot'] = True
        elif key == 'v' or key =='verbose':
            kvargmap['verbose'] = True
        else:
            print(f'{_warning} Unrecognized command line argument {key}')
    
    # If the help flag was passed, don't do anything
    if 'help' in kvargmap:
        print(emixa.__doc__)
        return

    # If no arguments are passed, don't do anything
    if 'function' not in kvargmap and 'plot' not in kvargmap:
        print(f'{_info} No outputs (-f or -p) requested, skipping further processing')
        return

    # Check if any arguments were passed
    args = list(filter(lambda arg: not arg.startswith('-'), args))
    if len(args) == 0:
        print(f'{_error} No test name specified')
        return

    # Run any possible characterizations with the given arguments
    chars = characterize(args, kvargmap)

    # If the data is valid, process it as specified by the command line
    if chars is None:
        print(f'{_error} Characterization data is invalid or unavailable, exiting')
        return
    funcpaths = funcgen(chars) if 'function' in kvargmap else None
    plotpaths = visualize(chars) if 'plot' in kvargmap else None

    # Write responses to the console
    if funcpaths is not None:
        if len(funcpaths) != 0:
            print(f'{_info} Wrote Python output files to:')
            for path in funcpaths:
                print(f'{_info}  - {path}')
        else:
            print(f'{_info} No Python output files written')
    if plotpaths is not None:
        if len(plotpaths) != 0:
            print(f'{_info} Wrote plot output files to:')
            for path in plotpaths:
                print(f'{_info}  - {path}')
        else:
            print(f'{_info} No plot output files written')

    # Processing completed, return from here
    print(f'{_info} Finished processing, exiting')
    return

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(emixa.__doc__)
    else:
        os.chdir(os.path.dirname(os.path.abspath(__file__)))
        emixa(sys.argv[1:])
