#!/usr/bin/env python3

from datetime import datetime
import os
import subprocess
from subprocess import Popen
import shutil

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

def info(string):
    print("[{}]: {}".format(datetime.now(), string))

dt = datetime.now()

this_file_name = dt.isoformat() + '.sql.gz'
this_backup_path = os.path.join(BACKUP_PATH, this_file_name)

# {{{ Backup and private dump

info("Dumping full database.")

pg_dump = [
    "pg_dump", "-O", "-c", "-U", 
    DATABASES['default']['USER'],
    DATABASES['default']['NAME']
]

with open(this_backup_path, "w") as f:
    p_pg = Popen(pg_dump, stdout=subprocess.PIPE)
    p_gzip = Popen(["gzip"], stdin=p_pg.stdout, stdout=f)
    p_gzip.communicate()

files_path = os.path.join(BACKUP_PATH, 'files')

if not os.path.exists(files_path):
    files = []
else:
    with open(files_path, 'r') as f:
        files = f.readlines()
    files = [f.strip() for f in files if f.strip() != '']
files.append(this_file_name)

if len(files) > 100:
    for f in files[:-100]:
        try:
            os.remove(os.path.join(BACKUP_PATH, f))
        except:
            pass
    files = files[-100:]

with open(files_path, 'w') as f:
    for item in files:
        f.write('%s\n' % item)

full_path = os.path.join(DUMP_PATH, 'full.sql.gz')

info("Copying to dump dir.")

shutil.copy(this_backup_path, full_path)
# }}}

# {{{ Public dump

info("Dumping public database.")

public_path = os.path.join(DUMP_PATH, 'aligulac.sql')

pub_pg_dump = pg_dump[:5]

for tbl in public_tables:
    pub_pg_dump.extend(['-t', tbl])

pub_pg_dump.append(pg_dump[-1])

with open(public_path, 'w') as f:
    subprocess.call(pub_pg_dump, stdout=f)

# }}}

# {{{ Compress/decompress files

def compress_file(source):
    info("Compressing {}".format(source))
    with open(source, "r") as src:
        with open(source + ".gz", "w") as dst:
            subprocess.call(["gzip"], stdin=src, stdout=dst)

def decompress_file(source):
    info("Decompressing {}".format(source))
    with open(source, "r") as src:
        with open(source[:-3], "w") as dst:
            subprocess.call(["gunzip"], stdin=src, stdout=dst)


compress_file(public_path)
decompress_file(full_path)

# }}}
