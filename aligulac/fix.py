#!/usr/bin/python
import os
import datetime

dt = datetime.datetime.now()

os.system('mysqldump -u aligulac -pv3ll3mp3t4 aligulac ' +\
        '> /usr/local/www/aligulac/backup/%s.sql' % dt.isoformat())

with open('/usr/local/www/aligulac/backup/files', 'r') as f:
    files = f.readlines()

files = [f.strip() for f in files if f.strip() != '']
files.append('%s.sql' % dt.isoformat())

if len(files) > 40:
    os.system('rm /usr/local/www/aligulac/backup/%s.sql' % files[0])
    files = files[1:]

with open('/usr/local/www/aligulac/backup/files', 'w') as f:
    for item in files:
        f.write('%s\n' % item)
