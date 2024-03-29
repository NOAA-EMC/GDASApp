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


def removefile(file):
    # duplicates of the shutil.copytree with the option dirs_exist_ok=True
    # which does not exixt in the version installed on orion
    if os.path.exists(file):
        os.remove(file)
        logging.info(f"Remove {file}")
    else:
        logging.info(f"{file} does not exists...")


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
        logging.info(f"Recursive copy of {src} to {dest}")


def copyfile(src, dest):
    # same as copytree but for a single file
    try:
        shutil.copy(src, dest)
        logging.info(f"copy of {src} to {dest}")
    except FileExistsError:
        os.remove(dest)
        logging.info(f"{dest} exists, removing...")
        shutil.copy(src, dest)
        logging.info(f"copy of {src} to {dest}")


def symlink(src, dest, remove=True):
    try:
        os.symlink(src, dest)
        logging.info(f"Symbolically linked {src} to {dest}")
    except FileExistsError:
        if remove:
            os.remove(dest)
            logging.info(f"{dest} exists, removing...")
            os.symlink(src, dest)
            logging.info(f"Symbolically linked {src} to {dest}")
        else:
            logging.info(f"{dest} exists, do nothing.")
