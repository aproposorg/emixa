
import re

_info    = '[emixa-info]'
_warning = '[\033[1;33memixa-warning\033[0;0m]'
_error   = '[\033[1;31memixa-error\033[0;0m]'

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
