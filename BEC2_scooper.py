#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Scooper script to interface with lyse"""
# mv test_0.sis test_0a.sis ;  mv test_1.sis test_1a.sis ; mv test_0a.sis test_0.sis ; mv test_1a.sis test_1.sis

from filewatch import FileChangeNotifier
from libsis.libsis import libsis
import os
import h5py
import zprocess
import scooper
from datetime import datetime
from pathlib import Path
import numpy as np

### Full path to incoming image-files
basedir = '/home/gabriele/sis-fish/'
monitoredfiles = [os.path.join(basedir, 'test_0.sisRAW'),
                os.path.join(basedir, 'HamamatsuVert.npy')]

#Output file settings
save_dict = {'save' : True,
            'run_name' : 'data',
            'get_scope': False}

h5path_0 = Path(r'/home/gabriele/img/')

attrs = {}
attrs['run number'] = 0
attrs['run repeat'] = 0

def ShotReady():
    print("hey dude, shot is ready!")
    now = datetime.now()


    # -------------------------------------------------------
    # prepare path for h5 file
    if save_dict['save']:
        h5path = h5path_0/now.strftime('%Y/%Y-%m-%d')/save_dict['run_name']
        h5path.mkdir(parents=True, exist_ok=True)
        ix = scooper.get_last_sequence_index(h5path)
        attrs['sequence_index'] = ix + 1
        attrs['sequence_id'] = now.strftime('%Y_%m_%d') + '_' + save_dict['run_name']
    
            
        
    attrs['run time'] = now.isoformat()
    h5filepath = h5path / f"{attrs['sequence_id']}_{attrs['sequence_index']:04d}.h5"
    scooper.make_new_h5file(h5filepath, attrs)
    # -------------------------------------------------------
    # here put whatever data you want in the h5 file
    with h5py.File(h5filepath) as h5file:
        print('banana')
        hor_images = np.fromfile(monitoredfiles[0], dtype=np.uint16).reshape((4, 1234, 1624))
        ver_images = np.load(monitoredfiles[1])
        print(ver_images.shape)
        
        for i, n in enumerate(['atoms', 'probe', 'back1', 'back2']):
            h5file['data/StingrayHor/{}'.format(n)] = hor_images[i]
            h5file['data/HamamatsuVert/{}'.format(n)] = ver_images[i]
            
        
        h5file['data/HamamatsuVert/sis'] = libsis.read_sis(monitoredfiles[1], full_output = True)[0]
#
#        if save_dict['get_scope']:
#            for scope, name in zip(scopes, scope_names):
#                data, t = scope.get_all_traces()
#                h5file[f'data/{name}/t'] = t
#                h5file[f'data/{name}/data'] = data
#        h5file['data'].attrs['run_name'] = save_dict['run_name']
#        h5file['data/images/raw'].attrs['camera'] = camera_name
#        for k, v in program_dict['variables'].items():
#            h5file['globals'].attrs[k] = v
#        h5file['experiment'] = str(program_dict)
#        for k, v in program_attrs.items():
#            # print(k)
#            h5file['experiment'].attrs[k] = v
    
    # -------------------------------------------------------
    # submit to lyse
    scooper.submit_to_lyse(h5filepath)
    print('END')


def main():
    FileWatcher = FileChangeNotifier(files= monitoredfiles,
                                    callback= ShotReady)
    FileWatcher.setEnabled(True)

if __name__ == '__main__':
    main()
    input("Press enter to quit.\n")
