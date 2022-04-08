import os
import logging


def mkdir(dirpath):
    """
    mkdir(dirpath)
    creates directory `dirpath`
    equivalent to `mkdir -p dirpath` in bash
    """
    import os
    try:
        os.makedirs(dirpath, exist_ok=True)
        logging.info(f"{dirpath} created successfully")
    except OSError as error:
        logging.info(f"{dirpath} could not be created")


def symlink(src, dest):
    try:
        os.symlink(src, dest)
        logging.info(f"Symbolically linked {src} to {dest}")
    except FileExistsError:
        os.remove(dest)
        logging.info(f"{dest} exists, removing...")
        os.symlink(src, dest)
        logging.info(f"Symbolically linked {src} to {dest}")
