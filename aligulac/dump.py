#!/usr/bin/env python3

from datetime import datetime
import os

from aligulac.settings import (
    BACKUP_PATH,
    DATABASES,
    DUMP_PATH,
)

public_tables = [
    'alias',
    'earnings',
    'event',
    'eventadjacency',
    'group',
    'groupmembership',
    'match',
    'message',
    'period',
    'player',
    'rating',
    'story',
]

dt = datetime.now()
table_string = ' '.join(['-t ' + tbl for tbl in public_tables])
call = 'pg_dump -U %s' % DATABASES['default']['USER']

# {{{ Backup and private dump
os.system(call + ' aligulac > ' + BACKUP_PATH + dt.isoformat() + '.sql')

with open(BACKUP_PATH + 'files', 'r') as f:
    files = f.readlines()
files = [f.strip() for f in files if f.strip() != '']
files.append(dt.isoformat() + '.sql')
if len(files) > 100:
    os.system('rm ' + BACKUP_PATH + files[0])
    files = files[1:]
with open(BACKUP_PATH + 'files', 'w') as f:
    for item in files:
        f.write('%s\n' % item)

os.system('cp ' + BACKUP_PATH + dt.isoformat() + '.sql ' + DUMP_PATH + 'full.sql')
# }}}

# {{{ Public dump
os.system(call + ' ' + table_string + ' aligulac > ' + DUMP_PATH + 'aligulac.sql')
# }}}
