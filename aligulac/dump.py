#!/usr/bin/python

'''
This script performs automatic backups and database dumps.
'''

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
    os.system('rm /usr/local/www/aligulac/backup/%s' % files[0])
    files = files[1:]

with open('/usr/local/www/aligulac/backup/files', 'w') as f:
    for item in files:
        f.write('%s\n' % item)

os.system('mysqldump -u aligulac -pv3ll3mp3t4 aligulac ' +\
        '--ignore-table=aligulac.auth_group ' +\
        '--ignore-table=aligulac.auth_group_permissions ' +\
        '--ignore-table=aligulac.auth_permission ' +\
        '--ignore-table=aligulac.auth_user ' +\
        '--ignore-table=aligulac.auth_user_groups ' +\
        '--ignore-table=aligulac.auth_user_user_permissions ' +\
        '--ignore-table=aligulac.django_admin_log ' +\
        '--ignore-table=aligulac.django_content_type ' +\
        '--ignore-table=aligulac.django_session ' +\
        '--ignore-table=aligulac.django_site ' +\
        '--ignore-table=aligulac.faq_post ' +\
        '--ignore-table=aligulac.blog_post ' +\
        '--ignore-table=aligulac.ratings_prematch ' +\
        '--ignore-table=aligulac.ratings_premathgroup ' +\
        '> /usr/local/www/media/al/aligulac.sql')
