
import re

_info    = '[emixa-info]'
_warning = '[\x1b[33memixa-warning\x1b[0m]'
_error   = '[\x1b[31memixa-error\x1b[0m]'

def relabel(string: str) -> str:
    """
    Format outputs from SBT according to emixa's style

    This function takes arguments as follows
    - string an output string from SBT

    Returns a string with info, warning, and error messages relabeled in 
    emixa's style
    """
    string = re.sub(r'\[info\]',    _info,    string)
    string = re.sub(r'\[warning\]', _warning, string)
    string = re.sub(r'\[error\]',   _error,   string)
    return string
