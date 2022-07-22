import os
import logging
import shutil


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


def copytree(src, dest):
    # duplicates of the shutil.copytree with the option dirs_exist_ok=True
    # which does not exixt in the version installed on orion
    try:
        shutil.copytree(src, dest)
        logging.info(f"Recursive copy of {src} to {dest}")
    except FileExistsError:
        shutil.rmtree(dest)
        logging.info(f"{dest} exists, removing...")
        shutil.copytree(src, dest)
        logging.info(f"Symbolically linked {src} to {dest}")


def symlink(src, dest):
    try:
        os.symlink(src, dest)
        logging.info(f"Symbolically linked {src} to {dest}")
    except FileExistsError:
        os.remove(dest)
        logging.info(f"{dest} exists, removing...")
        os.symlink(src, dest)
        logging.info(f"Symbolically linked {src} to {dest}")
