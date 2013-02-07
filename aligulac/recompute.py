#!/usr/bin/python

'''
Quick and dirty script to recompute all ratings.
'''

import os

for i in range(1,78):
    os.system('./period.py %i' % i)

os.system('./domination.py')
