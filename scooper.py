#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Scooper script to interface with lyse"""
#mv test_0.sis test_0a.sis ;  mv test_1.sis test_1a.sis ; mv test_0a.sis test_0.sis ; mv test_1a.sis test_1.sis

from filewatch import FileChangeNotifier
import os
import h5py

def ShotReady():
    print("hey dude, shot is ready!")
    

basedir = os.getcwd()
### Full path to incoming image-files
monitoredfiles = [os.path.join(basedir, 'test_0.sis'),
                os.path.join(basedir, 'test_1.sis')]
def main():
    FileWatcher = FileChangeNotifier(files= monitoredfiles,
                                    callback= ShotReady)
    FileWatcher.setEnabled(True)

if __name__ == '__main__':
    main()
    input("Press enter to quit.")
