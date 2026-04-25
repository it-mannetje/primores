import sys
import os

path = '/home/itmannetje/primores'
if path not in sys.path:
    sys.path.insert(0, path)

def _load_env(env_path):
    """Load .env without requiring python-dotenv."""
    if not os.path.exists(env_path):
        return
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, _, value = line.partition('=')
            os.environ.setdefault(key.strip(), value.strip())

_load_env(os.path.join(path, '.env'))

# Required environment variables (set these in the PythonAnywhere web app config):
#   SECRET_KEY    — random secret for session signing
#   MAIL_SERVER   — e.g. smtp.gmail.com
#   MAIL_PORT     — e.g. 587
#   MAIL_USERNAME — SMTP login
#   MAIL_PASSWORD — SMTP password
#   MAIL_FROM     — sender address (optional, defaults to MAIL_USERNAME)

from app import app as application, init_db, DB_PATH
from seed_data import seed, seed_locations

init_db()
seed(DB_PATH)
seed_locations(DB_PATH)
