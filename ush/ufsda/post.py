import os
import shutil
import glob
from solo.ioda import Ioda
from r2d2 import store


def merge_diags(config):
    """
    Merges IODA diag files depending on input config dict
    """
    # loop through list of observations
    for ob in config['observations']:
        obname = ob['obs space']['name'].lower()
        outfile = ob['obs space']['obsdataout']['obsfile']
        # the above path is what 'FV3-JEDI' expects, need to modify it
        outpath = outfile.split('/')
        outpath[0] = 'analysis'
        outpath = '/'.join(outpath)
        outfile = os.path.join(config['COMOUT'], outpath)
        outmatch = os.path.splitext(outfile)[0] + '_????.*'
        diagfiles = glob.glob(outmatch)
        if len(diagfiles) > 1:
            concat_diags(diagfiles, outfile)
        elif len(diagfiles) == 1:
            shutil.copy(diagfiles[0], outfile)
        else:
            print(f"No output for {obname}. Skipping...")


def concat_diags(files, outfile):
    """
    concat_diags(files, outfile)
        for a list of files `files`, concatenate them into one `outfile`
    """
    if (len(files)) > 0:
        ioda = Ioda('diags')
        ioda.concat_files(files, outfile)
    else:
        print('No files to concatenate!')


def archive_diags(config):
    """
    Archives IODA diag files with R2D2 based on input config dict
    """
    # loop through list of observations
    for ob in config['observations']:
        obname = ob['obs space']['name'].lower()
        outfile = ob['obs space']['obsdataout']['obsfile']
        # the above path is what 'FV3-JEDI' expects, need to modify it
        outpath = outfile.split('/')
        outpath[0] = 'analysis'
        outpath = '/'.join(outpath)
        # below is assumed to be the final, concatenated diag file
        diagfile = os.path.join(config['COMOUT'], outpath)
        if os.path.exists(diagfile):
            store(
                type='diag',
                experiment=config['experiment'],
                date=config['window begin'],
                model='gfs',
                obs_type=obname.lower(),
                source_file=diagfile,
                database=config['r2d2_archive_db'],
            )


def cleanup(config):
    """
    Performs final clean up to delete/move any remaining files
    """
    print("No cleanup yet! PLACEHOLDER")
