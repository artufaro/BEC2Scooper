import h5py
import os, glob
import logging
import sys
from datetime import datetime
import zprocess
from pathlib import Path
import time
import glob

__version__ = '0.1.0'

log = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout, level=logging.INFO)

def get_sequencedata(filepath):
    # open the h5 file to get sequence data
    attributes = {}
    
    with h5py.File(filepath, 'r') as file:
        # sequence_id = file.attrs['sequence_id']
        log.info(f'Getting sequence data from {filepath}')
        for k, v in file.attrs.items():
            attributes[k] = v
    return attributes 
    
def remove_h5file(filepath):
    # remove the file because h5 files keep growing if you delete/write
    try:
        os.remove(filepath)
        log.info(f'Deleting {filepath}')
    except:
        pass
        
def get_last_sequence_index(folderpath):
    h5files = glob.glob1(folderpath, '*.h5')
    indices = [int(f.split('_')[-1].split('.')[0]) for f in h5files]
    try:
        return max(indices)
    except ValueError:
        return -1

def make_new_h5file(filepath, attributes):
    # make a new h5 file
    log.info(f'Writing {filepath}')
    with h5py.File(filepath, 'w') as file:
        file.create_group('globals')
        for k, v in attributes.items():
            file.attrs[k] = v

def submit_to_lyse(filepath):
    zprocess.zmq_get(42519, data={'filepath': str(filepath)})


if __name__ == '__main__':

    path = Path(r'C:\Users\bec1\Desktop')
    
    # get some default paramaters
    now = datetime.now()
    data = {}
    data['sequence_id'] = now.strftime('%Y_%m_%d') +'_data'
    data['sequence_index'] = 0
    data['run time'] = now.isoformat()
    data['run number'] = 0
    data['run repeat'] = 0

    for _ in range(5): 
        try:
            data = get_sequencedata(filepath)
            data['sequence_index'] += 1
            print(data['sequence_index'])
            os.remove(filepath)
        except:
            pass
        
        filepath = path / f"{data['sequence_id']}_{data['sequence_index']}.h5"
        print(filepath)
        make_new_h5file(filepath, data)
        time.sleep(1)
        submit_to_lyse(filepath)
    