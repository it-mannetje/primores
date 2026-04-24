import sys
import os

path = '/home/itmannetje/primores'
if path not in sys.path:
    sys.path.insert(0, path)

os.environ.setdefault('SECRET_KEY', 'primores-canon-2024-xK9mP3r!')
os.environ.setdefault('ADMIN_PASSWORD', 'primores2024')

from app import app as application, init_db, DB_PATH
from seed_data import seed

init_db()
seed(DB_PATH)
