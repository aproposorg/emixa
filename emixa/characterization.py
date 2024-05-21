
from abc import ABC
import numpy as np
import struct
import subprocess
from itertools import product
from typing import Tuple
from .util import relabel, _info, _warning, _error

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
    data = np.array([data[i:i+(1 << awidth)] for i in range(0, len(data), 1 << awidth)])

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
        i = 8
        while i < len(bytes):
            res = struct.unpack('>q', bytes[i:i+8])[0]
            cnt = struct.unpack('>i', bytes[i+8:i+12])[0]
            data[res] = [struct.unpack('>q', bytes[i+12+j*8:i+12+(j+1)*8])[0] for j in range(cnt)]
            i = i + 12 + cnt * 8

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



def val_sbt_exists(name: str, sbt_res: str) -> bool:
    """
    Validate that a characterizer exists from the output of an SBT test

    This function takes arguments as follows:
    - name the name of the characterizer
    - sbt_res the output from the SBT test

    Returns bool depending on the outcome of the SBT test
    """
    if 'No tests to run' in sbt_res:
        print(f'{_error} The specified test {name} does not exist')
        return False
    return True



def val_sbt_compiles(name: str, sbt_res: str) -> bool:
    """
    Validate that a characterizer compiles from the output of an SBT test

    This function takes arguments as follows:
    - name the name of the characterizer
    - sbt_res the output from the SBT test

    Returns bool depending on the outcome of the SBT test
    """
    if '[error]' in sbt_res:
        lines  = list(filter(lambda l: '[error]' in l, sbt_res.split('\n')))
        index  = max([(i if '^' in l else 1) for i, l in enumerate(lines)])
        errors = relabel('\n'.join(lines[:index+1]))
        print(f'{_error} The specified test {name} does not compile:\n{errors}')
        return False
    return True



def val_sbt_executed(name: str, sbt_res: str) -> bool:
    """
    Validate that a characterizer executed from the output of an SBT test

    This function takes arguments as follows:
    - name the name of the characterizer
    - sbt_res the output from the SBT test

    Returns bool depending on the outcome of the SBT test
    """
    if 'No tests were executed' in sbt_res:
        lines  = sbt_res.split('\n')
        index  = sum([(i if name in l else 0) for i, l in enumerate(lines)])
        errors = relabel('\n'.join(lines[index:index+4]))
        print(f'{_error} The specified test {name} could not be executed:\n{errors}')
        return False
    return True



def val_char_ok(name: str, sbt_res: str) -> bool:
    """
    Validate that a characterizer ran properly from the output of an SBT test

    This function takes arguments as follows:
    - name the name of the characterizer
    - sbt_res the output from the SBT test

    Returns bool depending on the outcome of the SBT test
    """
    if _error in sbt_res:
        lines  = list(filter(lambda l: _info in l or _error in l, sbt_res.split('\n')))
        index  = min([(i if _error in l else 0) for i, l in enumerate(lines)])
        errors = relabel('\n'.join(list(filter(lambda l: 'emixa' in l, lines[index:]))))
        print(f'{_error} Characterizer {name} reports errors:\n{errors}')
        return False
    return True



def val_sbt_output(name: str, sbt_res: str) -> bool:
    """
    Validate that a characterization ran successfully from the output of an SBT test

    This function takes arguments as follows:
    - name the name of the characterizer
    - sbt_res the output from the SBT test

    Returns bool depending on the outcome of the SBT test
    """
    exists   = val_sbt_exists(name, sbt_res)
    compiles = val_sbt_compiles(name, sbt_res)
    executed = val_sbt_executed(name, sbt_res)
    char_ok  = val_char_ok(name, sbt_res)
    return exists and compiles and executed and char_ok



def position_args(name: str, args: list) -> Tuple[list, list]:
    """
    Position named and positional arguments properly according to a characterizer's inputs

    This function takes arguments as follows:
    - name the name of the characterizer
    - args a list of arguments to pass to the characterizer

    Returns a list(parameters) | None if positioning was not possible
    """
    test_cmd = f'testOnly {name}'

    # Run the SBT command to capture the help message
    sbt_res = subprocess.run(['sbt', test_cmd, 'exit'], capture_output=True, text=True).stdout

    # Analyze the output to determine the argument names and default values, if any
    if not val_sbt_exists(name, sbt_res) or not val_sbt_executed(name, sbt_res):
        return None
    lines = list(filter(lambda l: _error in l, sbt_res.split('\n')))[1:]
    paramnames = list(map(lambda l: l.split(' ')[2], lines))
    deflines = list(filter(lambda l: '(got' in l, lines))
    defargs  = {splt[2] : splt[-1][:-1] for splt in [l.split(' ') for l in deflines]}

    # Extract the named arguments passed and validate them
    namedargs = [arg.split('=') for arg in args if '=' in arg]
    malformed_args = [narg for narg in namedargs if len(narg) != 2]
    if len(malformed_args) != 0:
        plural = 's' if len(malformed_args) > 1 else ''
        errors = '\n'.join([f'{_error} - {arg}' for arg in malformed_args])
        expected = '\n'.join([f'{_error} {" ".join(l.split(" ")[1:])}' for l in lines])
        print(f'{_error} Got malformed named argument{plural} for characterizer {name}:\n{errors}')
        print(f'{_error} Expected arguments:\n{expected}')
        return None
    mismatched_args = [narg[0] for narg in namedargs if narg[0] not in paramnames]
    if len(mismatched_args) != 0:
        plural = 's' if len(mismatched_args) > 1 else ''
        errors = '\n'.join([f'{_error} - {arg}' for arg in mismatched_args])
        expected = '\n'.join([f'{_error} {" ".join(l.split(" ")[1:])}' for l in lines])
        print(f'{_error} Got mismatched named argument{plural} for characterizer {name}:\n{errors}')
        print(f'{_error} Expected arguments:\n{expected}')
        return None
    unique_args, counts = np.unique([narg[0] for narg in namedargs], return_counts=True)
    if np.count_nonzero(counts > 1) != 0:
        non_unique_args = unique_args[counts > 1]
        plural = 's' if len(non_unique_args) > 1 else ''
        errors = '\n'.join([f'{_error} - {arg}' for arg in non_unique_args])
        expected = '\n'.join([f'{_error} {" ".join(l.split(" ")[1:])}' for l in lines])
        print(f'{_error} Got non-unique named argument{plural} for characterizer {name}:\n{errors}')
        print(f'{_error} Expected arguments:\n{expected}')
        return None
    namedargs = {narg[0] : narg[1] for narg in namedargs}

    # Extract the positional arguments passed and inform about additional ones
    posargs = [arg for arg in args if '=' not in arg]
    params  = []
    offset  = 0
    for prmname in paramnames:
        if prmname in namedargs:
            params.append(namedargs[prmname])
        elif offset < len(posargs):
            params.append(posargs[offset])
            offset += 1
        elif prmname in defargs:
            params.append(defargs[prmname])
        else:
            expected = '\n'.join([f'{_error} {" ".join(l.split(" ")[1:])}' for l in lines])
            print(f'{_error} Missing argument {prmname} for characterizer {name}')
            print(f'{_error} Expected arguments:\n{expected}')
            return None

    return params, paramnames



def characterize(args: list, kvargmap: dict) -> list:
    """
    Execute the characterization `name` with the given arguments `args` and 
    collect the results in a list

    This function takes arguments as follows:
    - args a list of arguments to pass to the characterizer
    - kvargmap a dictionary of command line arguments passed to emixa

    Returns list(Characterization) | None if no characterization was performed
    """
    name = args.pop(0)
    test_cmd = f'testOnly {name}'
    name = name.split('.')[-1]
    path = f'./output/{name}'

    # Extract the names of the arguments required by the test and position 
    # the passed arguments accordingly,if the test exists
    pos_args = position_args(test_cmd, args)
    if pos_args is None:
        return None
    params, paramnames = pos_args
    del pos_args

    # Split the arguments and search for any range-type arguments
    params = list(map(lambda prm: parse_range(prm) if ':' in prm else prm, params))

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
        cmdparams = ' '.join([f'-D{paramnames[i]}={param}' for i, param in enumerate(runparams)])

        # Give a status on this run with colored highlights on range parameters
        if first:
            colparams = ' '.join([f'{name}={value}' for name, value in zip(paramnames, runparams)])
        else:
            colparams = map(lambda p: f'\033[1;33m{p[1]}\033[0;0m' if p[0] in rangeinds else str(p[1]), enumerate(runparams))
            colparams = ' '.join([f'{name}={value}' for name, value in zip(paramnames, colparams)])
        print(f'{_info} Running characterizer {name} with parameters {colparams}')

        # Run the SBT command for these parameters
        sbt_res = subprocess.run([f'sbt', f'{test_cmd} -- {cmdparams}', 'exit'], capture_output=True, text=True).stdout

        # Analyze the output to determine the type of test, if any
        print(f'{_info} Analyzing output from characterizer {name}')
        if not val_sbt_output(name, sbt_res):
            return None

        # Extract the test specifications
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
