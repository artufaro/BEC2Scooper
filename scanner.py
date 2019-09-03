from pathlib import Path
import logging
import sys
from datetime import datetime
import json
from ast import literal_eval
from collections import defaultdict
import time
import yaml
import zerorpc
import numpy as np

import h5py

import zprocess


from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler


logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout, level=logging.INFO)
#logging.basicConfig(stream=sys.stdout, level=logging.DEBUG) 

from cameras import cameras_db
cameras_list = [cameras_db['StingrayHor']]#, cameras_db['HamamatsuVert']]


class Scooper:
    def __init__(self, json_path, h5path_0, h5path_temp, cameras_list):
        
        self.filequeue = []
        self.sequence_index = -1
        self.run_number = 0
        self.h5path_0 = h5path_0
        self.h5path_temp = h5path_temp
        self.to_be_kept = True
        self.json_path = json_path
        self.cameras_list = cameras_list
        self.scopes = []


    def remove_h5file(self, filepath):
    # remove the file because h5 files keep growing if you delete/write
        try:
            os.remove(filepath)
            logger.info(f'Deleting {filepath}')
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
        logger.info(f'Writing {filepath}')
        with h5py.File(filepath, 'w') as file:
            file.create_group('globals')
            for k, v in attributes.items():
                file.attrs[k] = v

    def submit_to_lyse(self, filepath, timeout=2):
        zprocess.zmq_get(42519, data={'filepath': str(filepath)}, timeout=timeout)
    
    def makeh5file(self):
        logger.info("shot started")
        
        now = datetime.now()

        # -------------------------------------------------------
        # load settings
        
        with open(self.json_path) as jsonfile:
           last_program = json.load(jsonfile)
           new_sequence_index = last_program["sequence_index"]
        
        # read current settings
        with open('settings.yaml') as f:
            save_dict = yaml.load(f)
              
        
        self.to_be_kept = save_dict['save']
        # -------------------------------------------------------
        # prepare path for h5 file
                     
        if new_sequence_index != self.sequence_index:
            # move to a new folder
            self.sequence_index = new_sequence_index
            self.run_number = 0
            if self.to_be_kept == False:
                self.h5dirpath = self.h5path_temp/now.strftime('%Y/%m/%d/')/f"{self.sequence_index:04d}"
            else:
                self.h5dirpath = self.h5path_0/now.strftime('%Y/%m/%d/')/f"{self.sequence_index:04d}"
            
            self.h5dirpath.mkdir(parents=True)
            self.sequence_id = now.strftime('%Y_%m_%d') + '_' + save_dict['sequence_name']
        
        else:
            self.run_number = self.run_number + 1  
            
        self.h5path = self.h5dirpath/f"{self.sequence_id}_{self.run_number}.h5"
        
        
        attrs = defaultdict() 
        attrs['sequence_id'] = self.sequence_id   
        attrs['run time'] = now.isoformat()
        attrs['sequence_index'] = self.sequence_index
        attrs['run time'] = now.isoformat()
        
 
        self.make_new_h5file(self.h5path, attrs)
        
        with h5py.File(self.h5path) as h5file:
        # save program variables
            try:
                with open(self.json_path) as jsonfile:
                   last_program = json.load(jsonfile)
                   for k, v in last_program.items():
                       h5file[f"experiment/{k}"] = json.dumps(v)
                   
                   for k,v in last_program['variables'].items():
                       h5file["globals"].attrs[k] = v
            except  FileNotFoundError:
                logger.error("Json file not found")
            
            # add user globals
            for k,v in save_dict['user_globals'].items():
                   h5file["globals"].attrs[k] = v
        
        # append file to the queue
        shot = {'timestamp': time.time(),
                'filepath': self.h5path}
        self.filequeue.append(shot)
        
        if save_dict['submit_to_runviewer']:
            try:
                zprocess.zmq_get(42521, data=str(self.h5path), timeout=2)
            except zprocess.utils.TimeoutError:
                logger.info('runviewer is not ON')
        
        # add new scopes and create clients
        for scope in save_dict['scopes']:
            # I know this is ugly
            if scope['name'] not in [s['name'] for s in self.scopes]:
                c = zerorpc.Client(scope['address'])
                scope['client'] = c
                scope['delayed_trg'] = False
                self.scopes.append(scope)
        
        # arm all the scopes
        for scope in self.scopes:
        
            # if it is not triggered, it means we are still running previous shot
            if scope['client'].triggered() == False:
                scope['delayed_trg'] = True
            else:    
                scope['client'].arm()
                logger.info(f"arming scope {scope['name']} at: {scope['address']}")

    
    def gather_data(self):
        # -------------------------------------------------------
        # here put whatever data you want in the h5 file
        
        now = time.time()
        # pop last file from the queue
        while True:
            try:
                shot = self.filequeue.pop(0)
            except IndexError:
                return
            
            if (now - shot['timestamp']) < 40:
                break
            else:
                logger.info('Shot expired. Retrying...')
        
        _file = shot['filepath']
        logger.info(f'Saving images to {_file}')
        
        with h5py.File(_file) as h5file:
            
            # add raw images
            for c in self.cameras_list:
                images = c.get_img()
                
                for k, v in images.items():
                    h5file[f"data/{c.name}/{k}"] = v
            
            # add scope traces
            for scope in self.scopes:
                # get_traces waits for the trigger to come
                path = scope['client'].get_traces()
                
                # re-arm the scope if the next shot has started already 
                if scope['delayed_trg']:
                    scope['delayed_trg'] = False
                    scope['client'].arm()
                    logger.info(f"(delayed) arming scope {scope['name']} at: {scope['address']}")
                    
                # loading a .npz returns a dictionary-like object, but it needs closing!
                with np.load(scope['filepath']) as data:
                    for _name, _array in data.items():
                        h5file[f"data/{scope['name']}/{_name}"] = _array
                    

        # -------------------------------------------------------
        # submit to lyse
        with open('settings.yaml') as f:
            save_dict = yaml.load(f)
            
        timeout = 2
        if save_dict['submit_to_lyse']:
            try:
                self.submit_to_lyse(_file, timeout)
            except zprocess.utils.TimeoutError:
                logger.warning('lyse is not ON')
        print('END')



class Scanner:
    def __init__(self, files, path='.'):
    
        # provide explicitly a list of files, when all of them have been "moved"
        # the data gathering is started
        self.files = set(files)
        
        self._collected = []
        self.path = Path(path)

        self.event_handler = PatternMatchingEventHandler(
            patterns=['*.json', '*.npz'],
            ignore_directories=True)

        # pass the '_on' methods to the event handler
        for name in dir(self):
            attr = getattr(self, name)
            if name.startswith('_on') and callable(attr):
                setattr(self.event_handler, name[1:], attr)

        self.observer = Observer()
        self.observer.schedule(self.event_handler, str(self.path), recursive=False)

        logger.info('Watching for files %s', self.files)


#    def _on_modified(self, event):
#        filename = Path(event.src_path).name
#        
#        logger.debug(event)
#            
#        if 'tmp' not in filename:
#            self._collected[0].add(filename)
#            logger.info('collected files now:' + str(self._collected))
#      
#        
#        
#        if self._collected[0] == self.files:
#            self.scooper.gather_data()
#            self._collected.pop(0)
        
    def _on_moved(self, event):
        """currently only the last_program.json is seen as moved file"""
        filename = Path(event.dest_path).name
        
        logger.debug(event)
        logger.info(f"collected {filename}")
        
        if filename == 'last_program.json':
            self.scooper.makeh5file()
            self._collected.append({filename})
        
        else:
            try:
                if filename in self.files:
                    self._collected[0].add(filename)
                
                    if self._collected[0] == self.files:
                        self.scooper.gather_data()
                        self._collected.pop(0)
            
            except IndexError as e:
                raise(e)
                logger.error(f"file {filename} has updated without any shot pending!")
                self._collected.pop(0)
        

    def scan(self):
        logger.info('Watchdog starting...')
        self.observer.start()
    
        



if __name__ == '__main__':

    from cameras import cameras_db

    # Select which cameras are in use
    cameras_list = [cameras_db['StingrayHor']]#, cameras_db['HamamatsuVert']]

    # only the files in monitoredfiles will be watched, and all the rest we assume 
    # to be in place when this are updated. Place only vital files for the experiment
    
    monitoredfiles = [c.files.name for c in cameras_list]

    scooper = Scooper('/home/gabriele/sis-fish/last_program.json',
        Path(r'/home/gabriele/NAS542_dataBEC2'),
        Path(r'/backup/img/'),
        cameras_list)
    
    
    scanner = Scanner(['last_program.json'] + monitoredfiles, 
                        path='/home/gabriele/sis-fish/')
    scanner.scooper = scooper

    scanner.scan()
    input("Press enter to quit.\n")
