
import numpy as np
from matplotlib import pyplot as plt, rc_context
from .characterization import ExhaustiveChar, Random2dChar, Random3dChar
from .util import _info, _warning, _error

_config = {
    'figsize': (5, 3),
    'format' : 'pdf',
    'dpi'    : 300,
    'bbox_inches': 'tight',
    'grid' : 'minor',
    'rc_context' : { 'font.family' : 'Times New Roman', 'font.size' : 12, 'mathtext.fontset' : 'cm' }
}

def geomean(ls: list) -> float:
    return np.prod(np.power(ls, 1 / len(ls)))

def visualize_exhaustive(char: ExhaustiveChar, diffparams: list = []) -> list:
    """
    Generate some plots from an exhaustive characterization

    This function takes arguments as follows
    - char the exhaustive characterization data
    - diffparams the list of differing parameters in case of multiple configurations

    Returns the paths to the result files list(str)
    """
    modname = f'{char.module}{"".join([f"_{p}" for p in diffparams])}'
    plotpaths = []

    with rc_context(_config['rc_context']):
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

        # PLOT 1: Mean error per result
        path = f'./output/{char.name}/mepr_{modname}.{_config["format"]}'
        fig, ax = plt.subplots(figsize=_config['figsize'], clear=True)
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

        # PLOT 2: Mean relative error per result
        path = f'./output/{char.name}/mredpr_{modname}.{_config["format"]}'
        fig, ax = plt.subplots(figsize=_config['figsize'], clear=True)
        keys = [k for k in keys if k != 0]
        data = [geomean(np.abs(np.array(resdict[k]) / k)) for k in keys]
        ax.bar(keys, data, zorder=4, width=1)
        ax.set_xlim(xlim)
        ax.set_xlabel(result)
        ax.set_ylabel('Mean error')
        ax.grid(_config['grid'])
        fig.tight_layout()
        fig.savefig(path, dpi=_config['dpi'], bbox_inches=_config['bbox_inches'])
        plotpaths.append(path)

        # PLOT 3: Histogram of error magnitudes
        # Filter the non-zero errors
        path = f'./output/{char.name}/hist_{modname}.{_config["format"]}'
        data = [v for v in np.array(char.data).reshape(-1) if v != 0]
        fig, ax = plt.subplots(figsize=_config['figsize'], clear=True)
        nbins = 1 << opwdth if opwdth <= 6 else 64
        counts, bins = np.histogram(data, nbins)
        counts = counts / counts.sum()
        width = .8 * (np.max(bins) - np.min(bins)) / nbins
        ax.bar((bins[:-1] + bins[1:]) / 2, counts, align='center', width=width)
        sax = ax.twinx()
        sax.plot(bins[:-1], np.cumsum(counts), color='r')
        ax.set_xlabel('Error magnitude')
        ax.set_ylim(0)
        ax.set_ylabel('Relative frequency')
        sax.set_ylim(0, 1)
        sax.set_ylabel('Cumulative frequency')
        sax.tick_params(axis='y', colors='r')
        ax.grid(_config['grid'])
        fig.tight_layout()
        fig.savefig(path, dpi=_config['dpi'], bbox_inches=_config['bbox_inches'])
        plotpaths.append(path)

    return plotpaths



def stack_exhaustive(chars: list) -> list:
    """
    Generate some stacked plots from a list of exhaustive characterizations

    This function takes arguments as follows
    - chars the list of exhaustive characterization data

    Returns the paths to the result files list(str) | None
    """
    if len(chars) == 0:
        return None

    modnames  = [f'{char.module}{"".join([f"_{p}" for p in char.params])}' for char in chars]
    plotpaths = []

    with rc_context(_config['rc_context']):
        # Establish some constants regarding the designs
        opwdth = np.max([char.width for char in chars])

        # PLOT 1: Histogram of error magnitudes
        path = f'./output/{chars[0].name}/hist_{chars[0].module}_stack.{_config["format"]}'
        fig, ax = plt.subplots(figsize=_config['figsize'], clear=True)
        sax = ax.twinx()
        nbins = 1 << opwdth if opwdth <= 6 else 64

        # Filter the non-zero errors (and sort with names to inform the user)
        datas = list(zip([[v for v in np.array(char.data).reshape(-1) if v != 0] for char in chars], modnames))
        datas.sort(reverse=True, key=lambda p: np.max(np.abs(p[0])))
        modnames = [p[1] for p in datas]
        datas    = [p[0] for p in datas]

        # Compute the histogram data on a set of shared bins
        _, bins = np.histogram(datas[0], nbins)
        width   = .8 * (np.max(bins) - np.min(bins)) / nbins
        counts  = []
        for data in datas:
            cnts, _ = np.histogram(data, bins)
            cnts = cnts / cnts.sum()
            counts.append(cnts)

        # Find the y-axis limits
        maxs  = [np.max(cnts) for cnts in counts]
        y_max = (np.max(maxs) + np.min(maxs)) / 2 if np.max(maxs) > 2 * np.min(maxs) else None

        # Plot the individual histograms
        print(f'{_info} Plotted stacked histograms in order:')
        rect_contnrs = []
        for i, cnts in enumerate(counts[::-1]):
            rects = ax.bar((bins[:-1] + bins[1:]) / 2, cnts, align='center', width=width, zorder=2*i)
            rect_contnrs.append(rects)
            color = ", ".join([f"{c:.3f}" for c in rects.patches[0].get_facecolor()])
            print(f'{_info} - {modnames[::-1][i]} (color: ({color}))')
        label_align = 'left'
        for rects in rect_contnrs:
            # Get y-axis height to calculate label position from
            y_top = y_max if y_max is not None else ax.get_ylim()[1]

            # Add a label to all bars that exceed the y-axis limits
            for rect in rects:
                height = rect.get_height()
                if height > y_top:
                    label_y = y_top * .95
                    label_x = rect.get_x() + rect.get_width() * (-.75 if label_align == 'right' else 1.75)
                    label_color = rect.get_facecolor()
                    ax.text(label_x, label_y, f'{height:.2f}',
                            ha=label_align, va='center', color=label_color)
                    label_align = 'right' if label_align == 'left' else 'left'

        # Plot the total cumulative distribution
        sumcnts = np.array(counts[0])
        for cnts in counts[1:]:
            sumcnts += np.array(cnts)
        sumcnts = sumcnts / len(counts)
        sax.plot(bins[:-1], np.cumsum(sumcnts), color='r')
        ax.set_xlabel('Error magnitude')
        if y_max is not None:
            ax.set_ylim(0, y_max)
        else:
            ax.set_ylim(0)
        ax.set_ylabel('Relative frequency')
        sax.set_ylim(0, 1)
        sax.set_ylabel('Cumulative frequency')
        sax.tick_params(axis='y', colors='r')
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
    modname = f'{char.module}{"".join([f"_{p}" for p in diffparams])}'
    plotpaths = []

    with rc_context(_config['rc_context']):
        # Establish some constants regarding the design
        result  = f"Exact {'sum' if char.module == 'adder' else 'product'}"
        opwdth  = char.width
        reswdth = opwdth if char.module == 'adder' else 2*opwdth
        xlim    = (-2**(reswdth-1), 2**(reswdth-1)-1) if char.sgn else (0, 2**reswdth-1)

        # PLOT 1: Mean error per result
        path = f'./output/{char.name}/mepr_{modname}.{_config["format"]}'
        fig, ax = plt.subplots(figsize=_config['figsize'], clear=True)
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

        # PLOT 2: Mean relative error per result
        path = f'./output/{char.name}/mredpr_{modname}.{_config["format"]}'
        fig, ax = plt.subplots(figsize=_config['figsize'], clear=True)
        keys = [k for k in char.data.keys() if k != 0]
        data = [geomean(np.abs(np.array(char.data[k]) / k)) for k in keys]
        keys = [k if k < 2**(reswdth-1) else k - 2**reswdth for k in keys]
        ax.bar(keys, data, zorder=4, width=1)
        ax.set_xlim(xlim)
        ax.set_xlabel(result)
        ax.set_ylabel('Mean error')
        ax.grid(_config['grid'])
        fig.tight_layout()
        fig.savefig(path, dpi=_config['dpi'], bbox_inches=_config['bbox_inches'])
        plotpaths.append(path)

        # PLOT 3: Histogram of error magnitudes
        # Filter the non-zero errors
        path = f'./output/{char.name}/hist_{modname}.{_config["format"]}'
        data = []
        for res in char.data.keys():
            data.extend([v for v in char.data[res] if v != 0])
        fig, ax = plt.subplots(figsize=_config['figsize'], clear=True)
        nbins = 1 << opwdth if opwdth <= 6 else 64
        counts, bins = np.histogram(data, nbins)
        counts = counts / counts.sum()
        width = .8 * (np.max(bins) - np.min(bins)) / nbins
        ax.bar((bins[:-1] + bins[1:]) / 2, counts, align='center', width=width)
        sax = ax.twinx()
        sax.plot(bins[:-1], np.cumsum(counts), color='r')
        ax.set_xlabel('Error magnitude')
        ax.set_ylim(0)
        ax.set_ylabel('Relative frequency')
        sax.set_ylim(0, 1)
        sax.set_ylabel('Cumulative frequency')
        sax.tick_params(axis='y', colors='r')
        ax.grid(_config['grid'])
        fig.tight_layout()
        fig.savefig(path, dpi=_config['dpi'], bbox_inches=_config['bbox_inches'])
        plotpaths.append(path)

    return plotpaths



def stack_random2d(chars: list) -> list:
    """
    Generate some stacked plots from a list of random 2D characterizations

    This function takes arguments as follows
    - chars the list of random 2D characterization data

    Returns the paths to the result files list(str) | None
    """
    if len(chars) == 0:
        return None

    modnames  = [f'{char.module}{"".join([f"_{p}" for p in char.params])}' for char in chars]
    plotpaths = []

    with rc_context(_config['rc_context']):
        # Establish some constants regarding the design
        opwdth = np.max([char.width for char in chars])

        # PLOT 1: Histogram of error magnitudes
        path = f'./output/{chars[0].name}/hist_{chars[0].module}_stack.{_config["format"]}'
        fig, ax = plt.subplots(figsize=_config['figsize'], clear=True)
        sax = ax.twinx()
        nbins = 1 << opwdth if opwdth <= 6 else 64

        # Filter the non-zero errors
        datas = []
        for char in chars:
            data = []
            for res in char.data.keys():
                data.extend([v for v in char.data[res] if v != 0])
            datas.append(data)
        datas = list(zip(datas, modnames))
        datas.sort(reverse=True, key=lambda p: np.max(np.abs(p[0])))
        modnames = [p[1] for p in datas]
        datas    = [p[0] for p in datas]

        # Compute the histogram data on a set of shared bins
        _, bins = np.histogram(datas[0], nbins)
        width   = .8 * (np.max(bins) - np.min(bins)) / nbins
        counts  = []
        for data in datas:
            cnts, _ = np.histogram(data, bins)
            cnts = cnts / cnts.sum()
            counts.append(cnts)

        # Find the y-axis limits
        maxs = [np.max(cnts) for cnts in counts]
        y_max = (np.max(maxs) + np.min(maxs)) / 2 if np.max(maxs) > 2 * np.min(maxs) else None

        # Plot the individual histograms
        print(f'{_info} Plotted stacked histograms in order:')
        rect_contnrs = []
        for i, cnts in enumerate(counts[::-1]):
            rects = ax.bar((bins[:-1] + bins[1:]) / 2, cnts, align='center', width=width, zorder=2*i)
            rect_contnrs.append(rects)
            color = ", ".join([f"{c:.3f}" for c in rects.patches[0].get_facecolor()])
            print(f'{_info} - {modnames[::-1][i]} (color: ({color}))')
        label_align = 'left'
        for rects in rect_contnrs:
            # Get y-axis height to calculate label position from
            y_top = y_max if y_max is not None else ax.get_ylim()[1]

            # Add a label to all bars that exceed the y-axis limits
            for rect in rects:
                height = rect.get_height()
                if height > y_top:
                    label_y = y_top * .95
                    label_x = rect.get_x() + rect.get_width() * (-.75 if label_align == 'right' else 1.75)
                    label_color = rect.get_facecolor()
                    ax.text(label_x, label_y, f'{height:.2f}',
                            ha=label_align, va='center', color=label_color)
                    label_align = 'right' if label_align == 'left' else 'left'

        # Plot the total cumulative distribution
        sumcnts = np.array(counts[0])
        for cnts in counts[1:]:
            sumcnts += np.array(cnts)
        sumcnts = sumcnts / len(counts)
        sax.plot(bins[:-1], np.cumsum(sumcnts), color='r')
        ax.set_xlabel('Error magnitude')
        if y_max is not None:
            ax.set_ylim(0, y_max)
        else:
            ax.set_ylim(0)
        ax.set_ylabel('Relative frequency')
        sax.set_ylim(0, 1)
        sax.set_ylabel('Cumulative frequency')
        sax.tick_params(axis='y', colors='r')
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
    modname = f'{char.module}{"".join([f"_{p}" for p in diffparams])}'
    plotpaths = []

    # PLOT 1: 3D bar chart with MEDs
    with rc_context(_config['rc_context']):
        path = f'./output/{char.name}/med_{modname}.{_config["format"]}'

        # Establish some constants regarding the design
        opwdth  = char.width

        # Compute the mean error in a number of input operand domains
        dmns = 4
        if not (dmns != 0 and (dmns & (dmns-1)) == 0):
            print(f'{_error} Number of domains for 3D characterizations must be a power of two, got {dmns}')
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
        fig = plt.figure(figsize=(5, 5), num=1, clear=True)
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



def visualize(chars: list, kvargmap: dict) -> list:
    """
    Convert the output from one or more characterizations into plots

    This function takes arguments as follows
    - chars a list of characterization data list(Characterization)
    - kvargmap a dictionary of command line arguments passed to emixa

    Returns list(str) | None if no characterization data is passed
    """
    # If no data is passed, return nothing
    if len(chars) == 0:
        return None

    # Find the indices of the parameters that change
    numdiffs = [len(set([char.params[i] for char in chars])) for i in range(len(chars[0].params))]
    diffind  = [i for i, arg in enumerate(numdiffs) if arg != 1]

    # Filter the broken configurations
    fltrd_chars = [char for char in chars if char is not None]

    # Process the plots together if requested
    paths = []
    if 'stack' in kvargmap:
        # Process the data into one plot depending on its type
        if len(fltrd_chars) > 1:
            head = fltrd_chars[0]
            if isinstance(head, ExhaustiveChar):
                plotpaths = stack_exhaustive(fltrd_chars)
            elif isinstance(head, Random2dChar):
                plotpaths = stack_random2d(fltrd_chars)
            elif isinstance(head, Random3dChar):
                print(f'{_warning} Cannot produce stacked plot for 3D characterizations')
                plotpaths = None

            # Don't add paths for broken configurations
            if plotpaths is not None:
                paths.extend(plotpaths)

    # Otherwise, process them separately
    else:
        for char in fltrd_chars:
            # Use the predetermined indices to extract the changing parameters
            diffparams = [char.params[i] for i in diffind]

            # Process the data differently depending on its type
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
