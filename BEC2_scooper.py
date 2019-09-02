#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Scooper script to interface with lyse"""


from filewatch import FileChangeNotifier
from libsis.libsis import libsis
from cameras import cameras_db
import os
import sys
import h5py
import zprocess
import scooper
from datetime import datetime
from pathlib import Path
import numpy as np
import json
import logging
from ast import literal_eval
from collections import defaultdict
from pprint import PrettyPrinter


log = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout, level=logging.INFO)


# Full path to incoming image-files
basedir = Path(r'/home/gabriele/sis-fish/')

# json file where actions and variables are stored
json_path = '/mnt/fish3public/last-program.json'

# Basepath to saving location
#h5path_0 = Path(r'/backup/img/')
h5path_0 = Path(r'/home/gabriele/NAS542_dataBEC2')
h5path_temp =  Path(r'/backup/img/')

# Select which cameras are in use
cameras_list = [cameras_db['StingrayHor']]#, cameras_db['HamamatsuVert']]

monitoredfiles = [c.files for c in cameras_list]


class scooper:
    """
    dumb class to keep track of file saving
    """
    
    def __init__(self, monitoredfiles, h5path_0):
        self.FileWatcher = FileChangeNotifier(files= monitoredfiles,
                                    callback = self.ShotReady)
        self.FileWatcher.setEnabled(True)
        log.info(f'monitoring: {monitoredfiles}')
        self.sequence_index = -1
        self.run_number = 0
        self.h5path_0 = h5path_0
        self.to_be_kept = True
        self.pprint = PrettyPrinter(indent=4).pprint


            
    def remove_h5file(self, filepath):
    # remove the file because h5 files keep growing if you delete/write
        try:
            os.remove(filepath)
            log.info(f'Deleting {filepath}')
        except:
            pass
        
    def get_last_sequence_index(self, folderpath):
        p = Path(folderpath) 
        dirs = [x.name for x in p.iterdir() if x.is_dir()].sorted()
        print(dirs)
        sequence_index = int(dirs[-1])
        return sequence_index
        
    def make_new_h5file(self, filepath, attributes):
        # make a new h5 file
        log.info(f'Writing {filepath}')
        with h5py.File(filepath, 'w') as file:
            file.create_group('globals')
            for k, v in attributes.items():
                file.attrs[k] = v

    def submit_to_lyse(self, filepath, timeout=2):
        zprocess.zmq_get(42519, data={'filepath': str(filepath)}, timeout=timeout)

    def ShotReady(self):
    
        log.info("hey dude, shot is ready!")
        # log.info('received shot')
        
        now = datetime.now()

        # -------------------------------------------------------
        # load settings
        
        with open(json_path) as jsonfile:
           last_program = json.load(jsonfile)
           new_sequence_index = last_program["sequence_index"]
        
        

        with open('settings.py') as f:
            save_dict = literal_eval(f.read())
                
        # check if the previous shot was a temp one
#        if  self.to_be_kept == False:
#            self.remove_h5file(self.h5path)
        
        self.to_be_kept = save_dict['save']
        # -------------------------------------------------------
        # prepare path for h5 file
                     
        if new_sequence_index != self.sequence_index:
            # move to a new folder
            self.sequence_index = new_sequence_index
            self.run_number = 0
            if self.to_be_kept == False:
                self.h5dirpath = h5path_temp/now.strftime('%Y/%m/%d/')/f"{self.sequence_index:04d}"
            else:
                self.h5dirpath = self.h5path_0/now.strftime('%Y/%m/%d/')/f"{self.sequence_index:04d}"
            
            self.h5dirpath.mkdir(parents=True)
            self.sequence_id = now.strftime('%Y_%m_%d') + '_' + save_dict['sequence_name']
        
        else:
            self.run_number = self.run_number + 1  
            
        #self.pprint(f"{self.sequence_index}, {self.run_number}")
        self.h5path = self.h5dirpath/f"{self.sequence_id}_{self.run_number}.h5"
        
        
        attrs = defaultdict() 
        attrs['sequence_id'] = self.sequence_id   
        attrs['run time'] = now.isoformat()
        attrs['sequence_index'] = self.sequence_index
        attrs['run time'] = now.isoformat()
 
        self.make_new_h5file(self.h5path, attrs)
        
        # -------------------------------------------------------
        # here put whatever data you want in the h5 file
        with h5py.File(self.h5path) as h5file:
            # add raw images
            for c in cameras_list:
                images = c.get_img()
                
                for k, v in images.items():
                    h5file[f"data/{c.name}/{k}"] = v
                    
            # save program variables
            try:
                with open(json_path) as jsonfile:
                   last_program = json.load(jsonfile)
                   for k, v in last_program.items():
                       h5file[f"experiment/{k}"] = json.dumps(v)
                   
                   for k,v in last_program['variables'].items():
                       h5file["globals"].attrs[k] = v
            except  FileNotFoundError:
                print("Json file not found")
            
            # add user globals
            for k,v in save_dict['user globals'].items():
                   h5file["globals"].attrs[k] = v

        
        # -------------------------------------------------------
        # submit to lyse
        timeout = 2
        if save_dict['submit_to_lyse']:
            try:
                self.submit_to_lyse(self.h5path, timeout)
            except zprocess.utils.TimeoutError:
                print('lyse is not ON')
        
        if save_dict['submit_to_runviewer']:
            try:
                zprocess.zmq_get(42521, data=str(self.h5path), timeout=timeout)
            except zprocess.utils.TimeoutError:
                print('runviewer is not ON')
        print('END')


if __name__ == '__main__':
    Scooper = scooper(monitoredfiles, h5path_0)
    input("Press enter to quit.\n")
