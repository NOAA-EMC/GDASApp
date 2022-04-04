def isTrue(str_in):
    """ isTrue(str_in)
    - function to translate shell variables to python logical variables
    input: str_in - string (should be like 'YES', 'TRUE', etc.)
    returns: status (logical True or False)
    """
    str_in = str_in.upper()
    if str_in in ['Y', 'YES', '.TRUE.']:
        status = True
    else:
        status = False
    return status
