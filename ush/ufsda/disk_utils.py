def mkdir(dirpath):
    """
    mkdir(dirpath)
    creates directory `dirpath`
    equivalent to `mkdir -p dirpath` in bash
    """
    import os
    try:
        os.makedirs(dirpath, exist_ok=True)
        print(f"{dirpath} created successfully")
    except OSError as error:
        print(f"{dirpath} could not be created")
