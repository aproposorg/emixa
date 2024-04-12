
import numpy as np
from matplotlib import pyplot as plt, rc_context
from .characterization import ExhaustiveChar, Random2dChar, Random3dChar
from .util import _error

_config = {
    'figsize': (5, 3),
    'format' : 'pdf',
    'dpi'    : 300,
    'bbox_inches': 'tight',
    'grid' : 'minor',
    'rc_context' : { 'font.family' : 'Times New Roman', 'font.size' : 12, 'mathtext.fontset' : 'cm' }
}

def visualize_exhaustive(char: ExhaustiveChar, diffparams: list = []) -> list:
    """
    Generate some plots from an exhaustive characterization

    This function takes arguments as follows
    - char the exhaustive characterization data
    - diffparams the list of differing parameters in case of multiple configurations

    Returns the paths to the result files list(str)
    """
    modname = f'{char.module}{"".join(map(lambda p: f"_{p}", diffparams))}'
    plotpaths = []

    # PLOT 1: Mean error per result
    with rc_context(_config['rc_context']):
        path = f'./output/{char.name}/mepr_{modname}.{_config["format"]}'

        # Establish some constants regarding the design
        result  = f"Exact {'sum' if char.module == 'adder' else 'product'}"
        op      = (lambda a, b: a + b) if char.module == 'adder' else (lambda a, b: a * b)
        reswdth = char.width if char.module == 'adder' else 2*char.width
        opwdth  = char.width
        oprng   = range(-2**(opwdth-1),  2**(opwdth-1)) if char.sgn else range(2**opwdth)
        xlim    = (-2**(reswdth-1), 2**(reswdth-1)-1)   if char.sgn else (0, 2**reswdth-1)

        # Recompute the accurate results
        resdict = {}
        opmask  = (1 << opwdth) - 1
        resmask = (1 << reswdth) - 1
        resext  = (-1 << reswdth) if char.sgn else 0
        for a in oprng:
            for b in oprng:
                res = op(a, b) & resmask
                if char.sgn:
                    if char.module == 'adder' and (res >> (char.width - 1)) == 1:
                        res |= resext
                    if char.module == 'multiplier' and (res >> (2*char.width - 1)) == 1:
                        res |= resext
                err = char.data[a & opmask][b & opmask]
                if res in resdict:
                    resdict[res].append(err)
                else:
                    resdict[res] = [err]

        # Plot the recomputed results
        fig, ax = plt.subplots(figsize=_config['figsize'])
        keys = list(resdict.keys())
        data = [np.mean(resdict[k]) for k in keys]
        ax.bar(keys, data, zorder=4, width=1)
        ax.set_xlim(xlim)
        ax.set_xlabel(result)
        ax.set_ylabel('Mean error')
        ax.grid(_config['grid'])
        fig.tight_layout()
        fig.savefig(path, dpi=_config['dpi'], bbox_inches=_config['bbox_inches'])
        plotpaths.append(path)

    # PLOT 2: Histogram of error magnitudes
    with rc_context(_config['rc_context']):
        path = f'./output/{char.name}/hist_{modname}.{_config["format"]}'

        # Establish some constants regarding the design
        opwdth  = char.width
        reswdth = opwdth if char.module == 'adder' else 2*opwdth

        # Count the error magitudes
        data = np.array(char.data).reshape(-1)
        resdict = {}
        for res in data:
            if res in resdict:
                resdict[res] += 1
            else:
                resdict[res] = 1
        cnt = len(data)

        # Plot the counts
        fig, ax = plt.subplots(figsize=_config['figsize'])
        keys = np.sort(list(resdict.keys()))
        bars = np.array([resdict[k] / cnt for k in keys])
        ax.bar(keys, bars, zorder=4, width=1)
        ax.plot(keys, np.cumsum(bars), color='r')
        ax.set_xlabel('Error magnitude')
        ax.set_ylabel('Relative frequency')
        ax.grid(_config['grid'])
        fig.tight_layout()
        fig.savefig(path, dpi=_config['dpi'], bbox_inches=_config['bbox_inches'])
        plotpaths.append(path)

    return plotpaths



def visualize_random2d(char: Random2dChar, diffparams: list = []) -> list:
    """
    Generate some plots from a random 2D characterization

    This function takes arguments as follows
    - char the exhaustive characterization data
    - diffparams the list of differing parameters in case of multiple configurations

    Returns the paths to the result files list(str)
    """
    modname = f'{char.module}{"".join(map(lambda p: f"_{p}", diffparams))}'
    plotpaths = []

    # PLOT 1: Mean error per result
    with rc_context(_config['rc_context']):
        path = f'./output/{char.name}/mepr_{modname}.{_config["format"]}'

        # Establish some constants regarding the design
        result  = f"Exact {'sum' if char.module == 'adder' else 'product'}"
        reswdth = char.width if char.module == 'adder' else 2*char.width
        xlim    = (-2**(reswdth-1), 2**(reswdth-1)-1) if char.sgn else (0, 2**reswdth-1)

        # Plot the results
        fig, ax = plt.subplots(figsize=_config['figsize'])
        keys = list(char.data.keys())
        data = [np.mean(char.data[k]) for k in keys]
        keys = [k if k < 2**(reswdth-1) else k - 2**reswdth for k in keys]
        ax.bar(keys, data, zorder=4, width=1)
        ax.set_xlim(xlim)
        ax.set_xlabel(result)
        ax.set_ylabel('Mean error')
        ax.grid(_config['grid'])
        fig.tight_layout()
        fig.savefig(path, dpi=_config['dpi'], bbox_inches=_config['bbox_inches'])
        plotpaths.append(path)

    # PLOT 2: Histogram of error magnitudes
    with rc_context(_config['rc_context']):
        path = f'./output/{char.name}/hist_{modname}.{_config["format"]}'

        # Establish some constants regarding the design
        opwdth  = char.width
        reswdth = opwdth if char.module == 'adder' else 2*opwdth

        # Filter the non-zero errors
        data = []
        for res in char.data.keys():
            data.extend([v for v in char.data[res] if v != 0])

        # Plot the histogram
        fig, ax = plt.subplots(figsize=_config['figsize'])
        counts, bins = np.histogram(data, 1 << opwdth if opwdth <= 6 else 64)
        counts = counts / counts.sum()
        ax.stairs(counts, bins)
        ax.plot(bins[:-1], np.cumsum(counts), color='r')
        ax.grid(_config['grid'])
        fig.tight_layout()
        fig.savefig(path, dpi=_config['dpi'], bbox_inches=_config['bbox_inches'])
        plotpaths.append(path)

    return plotpaths



def visualize_random3d(char: Random3dChar, diffparams: list = []) -> list:
    """
    Generate some plots from a random 3D characterization

    This function takes arguments as follows
    - char the exhaustive characterization data
    - diffparams the list of differing parameters in case of multiple configurations

    Returns the paths to the result files list(str)
    """
    modname = f'{char.module}{"".join(map(lambda p: f"_{p}", diffparams))}'
    plotpaths = []

    # PLOT 1: 3D bar chart with MEDs
    with rc_context(_config['rc_context']):
        path = f'./output/{char.name}/med_{modname}.{_config["format"]}'

        # Establish some constants regarding the design
        opwdth  = char.width

        # Compute the mean error in a number of input operand domains
        dmns = 4
        if not (dmns != 0 and (dmns & (dmns-1)) == 0):
            f'{_error} Number of domains for 3D characterizations must be a power of two, got {dmns}'
            return []
        opmin   = -2**(opwdth-1) if char.sgn else 0
        dmnstep = (2**opwdth) // dmns
        sgn_chng = lambda k: k if k < 2**(opwdth-1) else k - 2**opwdth
        data = {(sgn_chng(k[0]), sgn_chng(k[1])) : char.data[(k[0], k[1])] for k in char.data} if char.sgn else char.data
        res  = []
        for da in range(0, dmns):
            damin, damax = opmin + da * dmnstep, opmin + (da+1) * dmnstep
            res.append([])
            for db in range(0, dmns):
                dbmin, dbmax = opmin + db * dmnstep, opmin + (db+1) * dmnstep
                dmndata = [data[(k[0], k[1])] for k in data if damin <= k[0] < damax and dbmin <= k[1] < dbmax]
                res[da].append(np.mean(np.abs(dmndata)))
        res = np.array(res).reshape(-1)
        lbls = ['', '']
        lbls.extend([f'$[{opmin + d * dmnstep}:{opmin + (d+1) * dmnstep})$' for d in range(0, dmns)])
        lbls.append('')

        # Plot the results
        fig = plt.figure(figsize=(5, 5))
        ax  = fig.add_subplot(111, projection='3d')
        _x  = _y = np.arange(dmns)
        _xx, _yy = np.meshgrid(_x, _y)
        x, y = _xx.ravel(), _yy.ravel()
        ax.bar3d(x, y, np.zeros_like(res), 1, 1, res, shade=True)
        ax.set_xticklabels(lbls[1:])
        ax.set_yticklabels(lbls)
        ax.set_xlabel('Operand $a$')
        ax.set_ylabel('Operand $b$')
        ax.set_zlabel('Mean absolute error')
        fig.tight_layout()
        fig.savefig(path, dpi=_config['dpi'], bbox_inches=_config['bbox_inches'])
        plotpaths.append(path)

    return plotpaths



def visualize(chars: list) -> list:
    """
    Convert the output from one or more characterizations into plots

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

        # Process the data different depending on its type
        if isinstance(char, ExhaustiveChar):
            plotpaths = visualize_exhaustive(char, diffparams)
        elif isinstance(char, Random2dChar):
            plotpaths = visualize_random2d(char, diffparams)
        elif isinstance(char, Random3dChar):
            plotpaths = visualize_random3d(char, diffparams)

        # Don't keep the broken configurations
        if plotpaths is not None:
            paths.extend(plotpaths)

    return paths
