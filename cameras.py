#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Database for camera parameters
"""
import os
import numpy as np

class Camera():
    """
    Camera objects for Scooper (hopefully will be the same as vimba?)
    """
    def __init__(self, name, files, h5group = '/', px_size=4.4e-6, get_img=None):
        
        self.name = str(name)
        self.files = files
        self.h5group = h5group
        self.px_size = px_size
        self._get_img = get_img
       
    def get_img(self):
        if self._get_img is not None:
            return self._get_img(self.files)
        else:
           print('what should I do?')


def StingrayGetImg(files):
    "supposes a .sisRAW with 4 images"
    return np.fromfile(files, dtype=np.uint16).reshape((4, 1234, 1624))


StingrayHor = Camera(name = 'StingrayHor',
                    files = os.path.abspath('/home/gabriele/sis-fish/test_0.sisRAW'),
                    h5group = 'data/StingrayHor',
                    px_size = 4.40,
                    get_img = StingrayGetImg)

StingrayHorDemag3 = Camera(name = 'StingrayHorDemag3',
                            files = os.path.abspath('/home/gabriele/sis-fish/test_0.sisRAW'),
                           h5group = "data/StingrayHorDemag3",
                           px_size = 4.40*3.12,
                           get_img = StingrayGetImg)
                           
                           
HamamatsuVert = Camera(name = 'HamamatsuVert',
                       files = os.path.abspath('/home/gabriele/sis-fish/HamamatsuVert.npy'),
                       h5group = "data/HamamatsuVert",
                       px_size = 6.50/2.0,
                       get_img = lambda f : np.load(f))
            
cameras_db = dict([ (cam.name, cam) for cam in [StingrayHor, StingrayHorDemag3, HamamatsuVert]])
