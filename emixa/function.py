
import numpy as np
from sklearn.linear_model import LinearRegression
from .characterization import ExhaustiveChar, Random2dChar, Random3dChar

def gen_exhaustive(char: ExhaustiveChar, diffparams: list = []) -> str:
    """
    Generate a Python function from an exhaustive characterization

    This function takes arguments as follows
    - char the exhaustive characterization data
    - diffparams the list of differing parameters in case of multiple configurations

    Returns the path to the resulting file str
    """
    modname = f'{char.module}{"".join(map(lambda p: f"_{p}", diffparams))}'

    # Initialize the description of the operator
    __mask = (1 << char.width) - 1
    if not char.sgn:
        __min = 0
        __max = (1 << char.width) - 1
    else:
        __min = -(1 << (char.width-1))
        __max = (1 << (char.width-1)) - 1
    def data_format(ls):
        return ',\n'.join([f"[{', '.join(map(str, row))}]" for row in ls])
    description = f"""\n__errors = [{data_format(char.data)}]\n\nclass {modname}:
    __array_ufunc__ = None
    __min  = {__min}
    __max  = {__max}
    __mask = {__mask}

    def __init__(self, x: int):
        assert self.__min <= x <= self.__max
        self.x = x"""

    # Determine the type of operation to implement
    (opsymb, opname) = ('+', 'add') if char.module == 'adder' else ('*', 'mul')
    if not char.sgn:
        outro = f"""return pos"""
    else:
        outro = f"""sext = -(pos >> {char.width - 1}) << {char.width}
        return sext | pos"""
    description += f"""\n
    def __{opname}__(self, y: int):
        assert self.__min <= y <= self.__max
        pos  =  (self.x {opsymb} y + __errors[self.x][y]) & self.__mask
        {outro}

    def __r{opname}__(self, y: int):
        assert self.__min <= y <= self.__max
        pos  =  (y {opsymb} self.x + __errors[self.x][y]) & self.__mask 
        {outro}\n"""

    # Write the result to a file and return the path
    path = f'./output/{char.name}/{modname}.py'
    with open(path, 'w') as file:
        file.write(description)
    return path



def gen_random2d(char: Random2dChar, diffparams: list = []) -> str:
    """
    Generate a Python function from a random 2D characterization

    This function takes arguments as follows
    - char the random 2D characterization data
    - diffparams the list of differing parameters in case of multiple configurations

    Returns the path to the resulting file str
    """
    modname = f'{char.module}{"".join([f"_{p}" for p in diffparams])}'

    # Split the output domain into n sub-domains and perform regression within 
    # each of them separately
    ndomslg2 = 2
    __dom_mask  = (1 << ndomslg2) - 1
    models = []
    for dom in range(1 << ndomslg2):
        xs   = np.array(list(filter(lambda k: (k >> (char.width - ndomslg2)) & __dom_mask == dom, char.data.keys()))).reshape((-1, 1))
        ys   = np.array(list(map(lambda k: np.mean(char.data[k]), xs[:,0])))
        model = LinearRegression().fit(xs, ys)
        models.append([model.coef_[0], model.intercept_])

    # Initialize the description of the operator
    __mask = (1 << char.width) - 1
    __dom_shft = char.width - ndomslg2
    if not char.sgn:
        __min = 0
        __max = (1 << char.width) - 1
    else:
        __min = -(1 << (char.width-1))
        __max = (1 << (char.width-1)) - 1
    def model_format(ls):
        return ',\n'.join(map(str, ls))
    description = f"""\n__model_weights = [{model_format(models)}]\n\nclass {modname}:
    __array_ufunc__ = None
    __min  = {__min}
    __max  = {__max}
    __mask = {__mask}

    __dom_mask = {__dom_mask}
    __dom_shft = {__dom_shft}

    def __init__(self, x: int):
        assert self.__min <= x <= self.__max
        self.x = x"""

    # Determine the type of operation to implement
    (opsymb, opname) = ('+', 'add') if char.module == 'adder' else ('*', 'mul')
    if not char.sgn:
        outro = f"""wghts = __model_weights[(exact >> self.__dom_shft) & self.__dom_mask]
        med   = int(wghts[0] * exact + wghts[1])
        pos   = (exact + med) & self.__mask
        return pos"""
    else:
        outro = f"""wghts = __model_weights[(exact >> self.__dom_shft) & self.__dom_mask]
        med   = int(wghts[0] * exact + wghts[1])
        pos   = (exact + med) & self.__mask
        sext  = -(pos >> {char.width - 1}) << {char.width}
        return sext | pos"""
    description += f"""\n
    def __{opname}__(self, y: int):
        assert self.__min <= y <= self.__max
        exact = (self.x {opsymb} y) & self.__mask
        {outro}

    def __r{opname}__(self, y: int):
        assert self.__min <= y <= self.__max
        exact = (y {opsymb} self.x) & self.__mask
        {outro}\n"""

    # Write the result to a file and return the path
    path = f'./output/{char.name}/{modname}.py'
    with open(path, 'w') as file:
        file.write(description)
    return path



def gen_random3d(char: Random3dChar, diffparams: list = []) -> str:
    """
    Generate a Python function from a random 3D characterization

    This function takes arguments as follows
    - char the random 3D characterization data
    - diffparams the list of differing parameters in case of multiple configurations

    Returns the path to the resulting file str
    """
    modname = f'{char.module}{"".join(map(lambda p: f"_{p}", diffparams))}'

    # Split the output domain into n sub-domains and compute the MED within 
    # each of them separately
    ndomslg2 = 2
    __dom_mask  = (1 << ndomslg2) - 1
    meds = [[] for _ in range(1 << ndomslg2)]
    for adom in range(1 << ndomslg2):
        for bdom in range(1 << ndomslg2):
            keys = list(filter(lambda k: ((k[0] >> (char.width - ndomslg2)) & __dom_mask == adom) and ((k[1] >> (char.width - ndomslg2)) & __dom_mask == bdom), char.data.keys()))
            ress = list(map(lambda k: char.data[k], keys))
            meds[adom].append(sum(ress) / len(ress))

    # Initialize the description of the operator
    __mask = (1 << char.width) - 1
    __dom_shft = char.width - ndomslg2
    if not char.sgn:
        __min = 0
        __max = (1 << char.width) - 1
    else:
        __min = -(1 << (char.width-1))
        __max = (1 << (char.width-1)) - 1
    def meds_format(ls):
        return ',\n'.join(list(map(str, ls)))
    description = f"""\n__meds = [{meds_format(meds)}]\n\nclass {modname}:
    __array_ufunc__ = None
    __min  = {__min}
    __max  = {__max}
    __mask = {__mask}

    __dom_mask = {__dom_mask}
    __dom_shft = {__dom_shft}

    def __init__(self, x: int):
        assert self.__min <= x <= self.__max
        self.x = x"""

    # Determine the type of operation to implement
    (opsymb, opname) = ('+', 'add') if char.module == 'adder' else ('*', 'mul')
    if not char.sgn:
        outro = f"""med   = __meds[(self.x >> self.__dom_shft) & self.__dom_mask][(y >> self.__dom_shft) & self.__dom_mask]
        pos   = int(exact + med) & self.__mask
        return pos"""
    else:
        outro = f"""med   = __meds[(self.x >> self.__dom_shft) & self.__dom_mask][(y >> self.__dom_shft) & self.__dom_mask]
        pos   = int(exact + med) & self.__mask
        sext  = -(pos >> {char.width - 1}) << {char.width}
        return sext | pos"""
    description += f"""\n
    def __{opname}__(self, y: int):
        assert self.__min <= y <= self.__max
        exact = (self.x {opsymb} y) & self.__mask
        {outro}

    def __r{opname}__(self, y: int):
        assert self.__min <= y <= self.__max
        exact = (y {opsymb} self.x) & self.__mask
        {outro}\n"""

    # Write the result to a file and return the path
    path = f'./output/{char.name}/{modname}.py'
    with open(path, 'w') as file:
        file.write(description)
    return path



def funcgen(chars: list) -> list:
    """
    Convert the output from one or more characterizations into Python functions

    This function takes arguments as follows
    - chars a list of characterization data list(Characterization)

    Returns list(str) | None if no characterization data is passed
    """
    # If no data is passed, return nothing
    if len(chars) == 0:
        return None

    # Find the indices of the parameters that change
    numdiffs = [len(set([char.params[i] for char in chars])) for i in range(len(chars[0].params))]
    diffind  = [i for i, arg in enumerate(numdiffs) if arg != 1]

    # Process the characterization outputs one at a time
    paths = []
    for char in chars:
        # Skip the broken configurations
        if char is None:
            continue

        # Use the predetermined indices to extract the changing parameters
        diffparams = [char.params[i] for i in diffind]

        # Process the data differently depending on its type
        if isinstance(char, ExhaustiveChar):
            path = gen_exhaustive(char, diffparams)
        elif isinstance(char, Random2dChar):
            path = gen_random2d(char, diffparams)
        elif isinstance(char, Random3dChar):
            path = gen_random3d(char, diffparams)

        # Don't keep the broken configurations
        if path is not None:
            paths.append(path)

    return paths
