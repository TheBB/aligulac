# Path of the folder where manage.py is located
PROJECT_PATH = '/home/efonn/repos/aligulac/aligulac/'

# Path of folder where database dumps are saved
# If you never call dump.py this is not necessary
DUMP_PATH = '/home/efonn/repos/aligulac/untracked/'

# Path of folder where backups are saved
# If you never call dump.py this is not necessary
BACKUP_PATH = '/home/efonn/repos/aligulac/untracked/backup/'

# Random string, 50 characters
SECRET_KEY =

# Database username and password
DB_USER =
DB_PASSWORD =

# Folder where the templates are stored
TEMPLATE_DIRS = ('/home/efonn/repos/aligulac/templates/',)

# Necessary for django debug toolbar to work
INTERNAL_IPS = ('127.0.0.1',)

# Cache backend (use DummyCache in development)
CACHE_BACKEND = 'django.core.cache.backends.dummy.DummyCache'
