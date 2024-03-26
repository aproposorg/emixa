
from abc import ABC
import numpy as np
import struct
import subprocess
from itertools import product
from typing import Tuple
from .util import relabel, _info, _error

class Characterization(ABC):

    def __init__(self, data, name: str, sgn: bool, width: int, module: str, params: list):
        assert type(name)   == str
        assert type(sgn)    == bool
        assert type(width)  == int
        assert type(module) == str
        self.data   = data
        self.name   = name
        self.sgn    = sgn
        self.width  = width
        self.module = module
        self.params = params
        self.type   = ''

    def __str__(self):
        params = str(self.params).replace('[', '').replace(']', '')
        return f'{self.type} characterization for test {self.name} of module {self.module} with parameters ({params})'.capitalize()



class ExhaustiveChar(Characterization):

    def __init__(self, data: dict, name: str, sgn: bool, width: int, module: str, params: list):
        super().__init__(data, name, sgn, width, module, params)
        assert type(data) == np.ndarray
        self.type = 'exhaustive'

    def __str__(self):
        return super().__str__()



class Random2dChar(Characterization):

    def __init__(self, data: dict, name: str, sgn: bool, width: int, module: str, params: list):
        super().__init__(data, name, sgn, width, module, params)
        assert type(data) == dict
        self.type = 'random2d'



class Random3dChar(Characterization):

    def __init__(self, data: dict, name: str, sgn: bool, width: int, module: str, params: list):
        super().__init__(data, name, sgn, width, module, params)
        assert type(data) == dict
        self.type = 'random3d'



def read_data_exhaustive(srcpath: str) -> Tuple[np.ndarray, int]:
    """
    Read the output from an exhaustive characterization into a numpy array

    This function takes arguments as follows
    - srcpath the directory to find the binary error file (`errors.bin`) in

    Returns a 2D array with error data | None
    """
    # Read the output file and determine the operator's bit-width
    with open(f'{srcpath}/errors.bin', 'rb') as file:
        bytes = file.read()
        awidth = struct.unpack('>i', bytes[0:4])[0]
        bwidth = struct.unpack('>i', bytes[4:8])[0]
        if awidth != bwidth:
            print(f'{_error} Operators in exhaustive characterization must have the same bit width, got {awidth} and {bwidth}')
            return None
        data = []
        for i in range(8, len(bytes), 8):
            data.append(struct.unpack('>q', bytes[i:i+8])[0])
        if (1 << awidth) * (1 << bwidth) != len(data):
            print(f'{_error} Error result dimensionality in exhaustive characterization must match operator bit width')
            return None

    # Reshape the data array    
    data = [data[i:i+(1 << awidth)] for i in range(0, len(data), 1 << awidth)]

    return data, awidth



def read_data_random2d(srcpath: str) -> Tuple[dict, int]:
    """
    Read the output from a random 2D characterization into a numpy array

    This function takes arguments as follows
    - srcpath the directory to find the binary error file (`errors.bin`) in

    Returns a dictionary (keys = computational results) with error data | None
    """
    # Read the output file and determine the operator's bit-width
    with open(f'{srcpath}/errors.bin', 'rb') as file:
        bytes = file.read()
        awidth = struct.unpack('>i', bytes[0:4])[0]
        bwidth = struct.unpack('>i', bytes[4:8])[0]
        if awidth != bwidth:
            print(f'{_error} Operators in random 2D characterization must have the same bit width, got {awidth} and {bwidth}')
            return False
        data = {}
        for i in range(8, len(bytes), 16):
            res = struct.unpack('>q', bytes[i:i+8])[0]
            med = struct.unpack('>d', bytes[i+8:i+16])[0]
            data[res] = med
    
    return data, awidth



def read_data_random3d(srcpath: str) -> Tuple[dict, int]:
    """
    Read the output from a random 2D characterization into a numpy array

    This function takes arguments as follows
    - srcpath the directory to find the binary error file (`errors.bin`) in

    Returns a dictionary (keys = operand pairs (a, b)) with error data | None
    """
    # Read the output file and determine the operator's bit-width
    with open(f'{srcpath}/errors.bin', 'rb') as file:
        bytes = file.read()
        awidth = struct.unpack('>i', bytes[0:4])[0]
        bwidth = struct.unpack('>i', bytes[4:8])[0]
        if awidth != bwidth:
            print(f'{_error} Operators in random 3D characterization must have the same bit width, got {awidth} and {bwidth}')
            return False
        data = {}
        for i in range(8, len(bytes), 24):
            a   = struct.unpack('>q', bytes[i:i+8])[0]
            b   = struct.unpack('>q', bytes[i+8:i+16])[0]
            res = struct.unpack('>q', bytes[i+16:i+24])[0]
            data[(a, b)] = res

    return data, awidth



def parse_range(arg: str) -> range:
    """
    Parse a given range start:stop[:by] (inclusive)

    This function takes arguments as follows:
    - arg the string representation of the range argument

    Returns range(start, stop, [by]) | None if the argument does not 
    represent a valid range
    """
    # Split the argument by the colon
    parts = arg.split(':')
    if len(parts) not in [2, 3]:
        print(f'{_error} Got invalid range-type argument {arg}')
        return None

    # Convert and validate all parts as being integers
    def safe_cast(i) -> int:
        try:
            val = int(i)
        except ValueError:
            val = None
        return val
    ints = list(map(safe_cast, parts))
    if None in ints:
        labels = ['start', 'stop', 'by']
        errors = list(filter(lambda tpl: tpl[1] is None, zip(parts, ints, labels)))
        for part, _, lbl in errors:
            print(f'{_error} Got invalid {lbl} part {part} in range-type argument {arg}')
            return None

    # Determine the type of range
    if len(ints) == 2: # start:stop
        start = ints[0]
        stop  = ints[1]
        by    = -1 if stop < start else 1
        return range(start, stop + by, 1)
    else: # start:stop:by
        start = ints[0]
        stop  = ints[1]
        by    = ints[2]
        if (stop < start and by >= 0) or (stop > start and by <= 0):
            print(f'{_error} Got malformed arguments to range({start}, {stop}, {by})')
            return None
        else:
            return range(start, stop + by, by)



def characterize(args: list, kvargmap: dict) -> list:
    """
    Execute the characterization `name` with the given arguments `args` and 
    collect the results in a list

    This function takes arguments as follows:
    - args a list of arguments to pass to the characterizer
    - kvargmap a dictionary of command line arguments passed to emixa

    Returns list(Characterization) | None if no characterization was performed

    TODO implement support for named arguments
    """
    name = args.pop(0)
    path = f'./output/{name}'
    test_cmd = f'testOnly {name}'

    # Split the arguments and search for any range-type arguments
    params = list(map(lambda arg: parse_range(arg) if ':' in arg else arg, args))

    # Combine the range arguments into all possible parameter combinations
    rangeparams = list(filter(lambda arg: isinstance(arg[1], range), enumerate(params)))
    rangeinds   = { arg[0] : ind for ind, arg in enumerate(rangeparams) }
    rangecombs = product(*[arg[1] for arg in rangeparams])

    # Execute all the SBT commands and collect the data classes into a list
    first = True
    res = []
    for comb in rangecombs:
        # Generate the proper combination of parameters for this run
        runparams = [comb[rangeinds[i]] if i in rangeinds else params[i] for i in range(len(params))]
        cmdparams = ' '.join([f'-Darg{i}={param}' for i, param in enumerate(runparams)])

        # Give a status on this run with colored highlights on range parameters
        if first:
            colparams = ' '.join(map(str, runparams))
        else:
            colparams = ' '.join(map(lambda p: f'\033[1;33m{p[1]}\033[0;0m' if p[0] in rangeinds else str(p[1]), enumerate(runparams)))
        print(f'{_info} Running characterizer {name} with parameters {colparams}')
        del colparams

        # Run the SBT command for these parameters
        sbt_res = subprocess.run([f'sbt', f'{test_cmd} -- {cmdparams}', 'exit'], capture_output=True, text=True).stdout

        # Analyze the output to determine the type of test, if any
        print(f'{_info} Analyzing output from characterizer {name}')
        if 'No tests to run' in sbt_res:
            print(f'{_error} The specified test {name} does not exist')
            return None
        if 'No tests were executed' in sbt_res:
            lines  = sbt_res.split('\n')
            index  = sum([(i if name in l else 0) for i, l in enumerate(lines)])
            errors = relabel('\n'.join(lines[index:index+4]))
            print(f'{_error} The specified test {name} could not be executed:\n{errors}')
            return None
        if 'emixa-error' in sbt_res:
            lines  = list(filter(lambda l: 'emixa-' in l, sbt_res.split('\n')))
            index  = min([(i if 'emixa-error' in l else 0) for i, l in enumerate(lines)])
            errors = relabel('\n'.join(list(filter(lambda l: 'emixa' in l, lines[index:]))))
            print(f'{_error} Characterizer reports errors:\n{errors}')
            return None
        if '[error]' in sbt_res:
            lines  = list(filter(lambda l: '[error]' in l, sbt_res.split('\n')))
            index  = max([(i if '^' in l else 0) for i, l in enumerate(lines)])
            errors = relabel('\n'.join(lines[:index+1]))
            print(f'{_error} The specified test {name} does not compile:\n{errors}')
            return None
        sbt_res = list(filter(lambda l: _info in l, sbt_res.split('\n')))
        specs = sbt_res[0].split(' ')
        (chartype, sgn, module) = (specs[1].lower(), specs[2].lower() == 'signed', specs[3].lower())
        if module not in ['adder', 'multiplier']:
            print(f'{_error} Cannot produce outputs for module of type {module}, only adders and multipliers are supported')
            return None

        # Redirect emixa info from the characterizer if requested by the user
        if 'verbose' in kvargmap:
            print('\n'.join(filter(lambda l: 'emixa-' in l, sbt_res)))

        # Read the output data from the characterization
        if chartype == 'exhaustive':
            print(f'{_info} Found results of exhaustive characterization')
            data, width = read_data_exhaustive(path)
            conf = ExhaustiveChar(data, name, sgn, width, module, runparams) if data is not None else None
        elif chartype == 'random2d':
            print(f'{_info} Found results of random 2D characterization')
            data, width = read_data_random2d(path)
            conf = Random2dChar(data, name, sgn, width, module, runparams) if data is not None else None
        elif chartype == 'random3d':
            print(f'{_info} Found results of random 3D characterization')
            data, width = read_data_random3d(path)
            conf = Random3dChar(data, name, sgn, width, module, runparams) if data is not None else None

        # Store the output as the proper data class
        res.append(conf)
        first = False

    # Return the list of results
    return res
