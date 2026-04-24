from app import app, init_db, DB_PATH
from seed_data import seed

init_db()
seed(DB_PATH)

if __name__ == '__main__':
    app.run()
