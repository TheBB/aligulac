#!/usr/bin/python

'''
Quick and dirty script to recompute all ratings.
'''

import os, sys

for i in range(1,int(sys.argv[1])+1):
    os.system('./period.py %i' % i)

os.system('./domination.py')
