#!/usr/bin/python

'''
This script performs automatic backups and database dumps.
'''

import os
import datetime

from aligulac.settings import DATABASES

# These tables should not be included in the public dump
ignore_tables = ['auth_group',\
                 'auth_group_permissions',\
                 'auth_permission',\
                 'auth_user',\
                 'auth_user_groups',\
                 'auth_user_user_permissions',\
                 'django_admin_log',\
                 'django_content_type',\
                 'django_session',\
                 'django_site',\
                 'faq_post',\
                 'blog_post',\
                 'ratings_prematch',\
                 'ratings_prematchgroup',\
                 'ratings_rating',\
                 'ratings_period']

# Locations for public dump, backup dump and backup list
private_location = '/usr/local/www/media/al/full.sql'
public_location = '/usr/local/www/media/al/aligulac.sql'
backup_location = '/usr/local/www/aligulac/backup/{filename}.sql'
backup_list = '/usr/local/www/aligulac/backup/files'

# To access the database
username = DATABASES['default']['USER']
password = DATABASES['default']['PASSWORD']
database = DATABASES['default']['NAME']

# Basic mysqldump call
command = 'mysqldump -u {username} -p{password} {database}'.format(\
        username=username, password=password, database=database)

# Backup dump
dt = datetime.datetime.now()
os.system(command + ' > ' + backup_location.format(filename = dt.isoformat()))

# Store the new file in the backup list
with open(backup_list, 'r') as f:
    files = f.readlines()
files = [f.strip() for f in files if f.strip() != '']
files.append('{filename}'.format(filename=dt.isoformat()))

# Update the private dump
os.system('cp ' + backup_location.format(filename=dt.isoformat()) + ' ' + private_location)

# If there are more than 100 stored backups, delete the earliest one
if len(files) > 100:
    os.system('rm ' + backup_location.format(filename=files[0]))
    files = files[1:]

# Write the backup list
with open(backup_list, 'w') as f:
    for item in files:
        f.write('%s\n' % item)

# Public dump
public_command = command
for table in ignore_tables:
    public_command += ' --ignore-table={database}.{table}'.format(database=database, table=table)
public_command += ' > ' + public_location
os.system(public_command)
