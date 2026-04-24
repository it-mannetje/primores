import os
import uuid
from functools import wraps
from flask import (Flask, render_template, request, jsonify,
                   redirect, url_for, session, flash, send_from_directory)
from werkzeug.utils import secure_filename
import sqlite3

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'primores-jaarclub-2024-xK9mP3r!')

BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
DB_PATH      = os.path.join(BASE_DIR, 'primores.db')
ALLOWED_EXT  = {'jpg', 'jpeg', 'png', 'gif', 'webp'}
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'primores2024')

app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB

MEMBERS = [
    {'name': 'Bas',        'color': '#3498db'},
    {'name': 'Glenn',      'color': '#27ae60'},
    {'name': 'Eric',       'color': '#9b59b6'},
    {'name': 'Bart',       'color': '#e67e22'},
    {'name': 'Jeroen D',   'color': '#e74c3c'},
    {'name': 'Onno',       'color': '#00b894'},
    {'name': 'Lutze',      'color': '#f0a500'},
    {'name': 'Paul',       'color': '#6c5ce7'},
    {'name': 'Peter',      'color': '#0984e3'},
    {'name': 'Marcel',     'color': '#d35400'},
    {'name': 'Robin',      'color': '#a29bfe'},
    {'name': 'Gert',       'color': '#00cec9'},
    {'name': 'Jeroen R',   'color': '#d63031'},
    {'name': 'Robert-Jan', 'color': '#2980b9'},
]

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS events (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            person_name   TEXT,
            date_year     INTEGER NOT NULL,
            date_month    INTEGER,
            date_day      INTEGER,
            title         TEXT NOT NULL,
            description   TEXT,
            photo_filename TEXT,
            submitted_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
            approved      INTEGER DEFAULT 0,
            is_primores   INTEGER DEFAULT 0
        );
    ''')
    conn.commit()
    conn.close()


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT


def require_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated


def member_by_name(name):
    return next((m for m in MEMBERS if m['name'] == name), None)


def save_photo(file_field):
    photo = request.files.get(file_field)
    if photo and photo.filename and allowed_file(photo.filename):
        ext = photo.filename.rsplit('.', 1)[1].lower()
        filename = f"{uuid.uuid4().hex}.{ext}"
        photo.save(os.path.join(UPLOAD_FOLDER, filename))
        try:
            from PIL import Image
            img_path = os.path.join(UPLOAD_FOLDER, filename)
            with Image.open(img_path) as img:
                img.thumbnail((1200, 900), Image.LANCZOS)
                img.save(img_path, optimize=True, quality=85)
        except Exception:
            pass
        return filename
    return None


def delete_photo(filename):
    if filename:
        path = os.path.join(UPLOAD_FOLDER, filename)
        if os.path.exists(path):
            os.remove(path)


# ── Public routes ────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('timeline.html', members=MEMBERS)


@app.route('/overzicht')
def overzicht():
    person_filter = request.args.get('persoon', 'all')
    conn = get_db()
    if person_filter == 'primores':
        events = conn.execute(
            'SELECT * FROM events WHERE is_primores=1 ORDER BY date_year, COALESCE(date_month,6), COALESCE(date_day,15)'
        ).fetchall()
    elif person_filter != 'all':
        events = conn.execute(
            'SELECT * FROM events WHERE approved=1 AND is_primores=0 AND person_name=? '
            'ORDER BY date_year, COALESCE(date_month,6), COALESCE(date_day,15)',
            (person_filter,)
        ).fetchall()
    else:
        events = conn.execute(
            'SELECT * FROM events WHERE (approved=1 AND is_primores=0) OR is_primores=1 '
            'ORDER BY date_year, COALESCE(date_month,6), COALESCE(date_day,15)'
        ).fetchall()
    conn.close()
    return render_template('overzicht.html', events=events, members=MEMBERS,
                           person_filter=person_filter, member_by_name=member_by_name)


@app.route('/api/events')
def api_events():
    conn = get_db()
    events = conn.execute(
        'SELECT * FROM events WHERE (approved=1 AND is_primores=0) OR is_primores=1 '
        'ORDER BY date_year, COALESCE(date_month,0), COALESCE(date_day,0)'
    ).fetchall()
    conn.close()
    result = []
    for e in events:
        color = '#c9a227'
        if e['person_name']:
            m = member_by_name(e['person_name'])
            if m:
                color = m['color']
        result.append({
            'id': e['id'],
            'person_name': e['person_name'] or 'Primores',
            'is_primores': bool(e['is_primores']),
            'date_year': e['date_year'],
            'date_month': e['date_month'],
            'date_day': e['date_day'],
            'title': e['title'],
            'description': e['description'] or '',
            'photo_url': url_for('uploaded_file', filename=e['photo_filename']) if e['photo_filename'] else None,
            'color': color,
        })
    return jsonify(result)


@app.route('/inzenden')
def inzenden():
    return render_template('inzenden.html', members=MEMBERS)


@app.route('/inzenden/<person_name>', methods=['GET', 'POST'])
def submit(person_name):
    member = next((m for m in MEMBERS if m['name'] == person_name), None)
    if not member:
        return "Persoon niet gevonden", 404

    if request.method == 'POST':
        date_year  = request.form.get('date_year', type=int)
        date_month = request.form.get('date_month', type=int) or None
        date_day   = request.form.get('date_day', type=int) or None
        title       = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()

        errors = []
        if not date_year or not (1940 <= date_year <= 2030):
            errors.append('Voer een geldig jaar in (1940–2030).')
        if not title:
            errors.append('Een titel is verplicht.')
        if date_month and not (1 <= date_month <= 12):
            errors.append('Ongeldige maand.')
        if date_day and not (1 <= date_day <= 31):
            errors.append('Ongeldige dag.')

        if errors:
            for e in errors:
                flash(e, 'error')
            return render_template('submit.html', member=member, members=MEMBERS)

        photo_filename = save_photo('photo')

        conn = get_db()
        conn.execute(
            'INSERT INTO events (person_name, date_year, date_month, date_day, title, description, photo_filename, approved, is_primores) '
            'VALUES (?,?,?,?,?,?,?,0,0)',
            (member['name'], date_year, date_month, date_day, title, description, photo_filename)
        )
        conn.commit()
        conn.close()

        flash('Bedankt! Je bijdrage is ontvangen en verschijnt na goedkeuring op de tijdlijn.', 'success')
        return redirect(url_for('submit', person_name=member['name']))

    return render_template('submit.html', member=member, members=MEMBERS)


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, secure_filename(filename))


# ── Admin routes ─────────────────────────────────────────────────

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form.get('password') == ADMIN_PASSWORD:
            session['admin'] = True
            return redirect(url_for('admin'))
        flash('Onjuist wachtwoord.', 'error')
    return render_template('admin_login.html')


@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect(url_for('index'))


@app.route('/admin')
@require_admin
def admin():
    conn = get_db()
    pending  = conn.execute(
        'SELECT * FROM events WHERE approved=0 AND is_primores=0 ORDER BY submitted_at DESC'
    ).fetchall()
    primores = conn.execute(
        'SELECT * FROM events WHERE is_primores=1 ORDER BY date_year, COALESCE(date_month,0), COALESCE(date_day,0)'
    ).fetchall()
    approved = conn.execute(
        'SELECT * FROM events WHERE approved=1 AND is_primores=0 ORDER BY person_name, date_year, COALESCE(date_month,0)'
    ).fetchall()
    conn.close()
    return render_template('admin.html',
                           pending=pending, primores_events=primores,
                           approved_events=approved, members=MEMBERS,
                           member_by_name=member_by_name)


@app.route('/admin/approve/<int:eid>', methods=['POST'])
@require_admin
def admin_approve(eid):
    conn = get_db()
    conn.execute('UPDATE events SET approved=1 WHERE id=?', (eid,))
    conn.commit()
    conn.close()
    flash('Bijdrage goedgekeurd.', 'success')
    return redirect(url_for('admin'))


@app.route('/admin/reject/<int:eid>', methods=['POST'])
@require_admin
def admin_reject(eid):
    _delete_event(eid)
    flash('Bijdrage afgewezen en verwijderd.', 'success')
    return redirect(url_for('admin'))


@app.route('/admin/delete/<int:eid>', methods=['POST'])
@require_admin
def admin_delete(eid):
    _delete_event(eid)
    flash('Evenement verwijderd.', 'success')
    return redirect(url_for('admin'))


def _delete_event(eid):
    conn = get_db()
    e = conn.execute('SELECT photo_filename FROM events WHERE id=?', (eid,)).fetchone()
    if e:
        delete_photo(e['photo_filename'])
    conn.execute('DELETE FROM events WHERE id=?', (eid,))
    conn.commit()
    conn.close()


@app.route('/admin/primores/add', methods=['POST'])
@require_admin
def admin_add_primores():
    return _upsert_event(None, is_primores=True)


@app.route('/admin/primores/edit/<int:eid>', methods=['POST'])
@require_admin
def admin_edit_primores(eid):
    conn = get_db()
    old = conn.execute('SELECT * FROM events WHERE id=?', (eid,)).fetchone()
    conn.close()

    date_year  = request.form.get('date_year', type=int)
    date_month = request.form.get('date_month', type=int) or None
    date_day   = request.form.get('date_day', type=int) or None
    title       = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()

    photo_filename = old['photo_filename'] if old else None
    new_photo = save_photo('photo')
    if new_photo:
        delete_photo(photo_filename)
        photo_filename = new_photo

    conn = get_db()
    conn.execute(
        'UPDATE events SET date_year=?, date_month=?, date_day=?, title=?, description=?, photo_filename=? WHERE id=?',
        (date_year, date_month, date_day, title, description, photo_filename, eid)
    )
    conn.commit()
    conn.close()
    flash('Evenement bijgewerkt.', 'success')
    return redirect(url_for('admin'))


def _upsert_event(person_name, is_primores):
    date_year  = request.form.get('date_year', type=int)
    date_month = request.form.get('date_month', type=int) or None
    date_day   = request.form.get('date_day', type=int) or None
    title       = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()

    if not date_year or not title:
        flash('Jaar en titel zijn verplicht.', 'error')
        return redirect(url_for('admin'))

    photo_filename = save_photo('photo')

    conn = get_db()
    conn.execute(
        'INSERT INTO events (person_name, date_year, date_month, date_day, title, description, photo_filename, approved, is_primores) '
        'VALUES (?,?,?,?,?,?,?,?,?)',
        (person_name, date_year, date_month, date_day, title, description, photo_filename,
         1 if is_primores else 0, 1 if is_primores else 0)
    )
    conn.commit()
    conn.close()
    flash('Evenement toegevoegd.', 'success')
    return redirect(url_for('admin'))


if __name__ == '__main__':
    init_db()
    from seed_data import seed
    seed(DB_PATH)
    app.run(debug=True, host='0.0.0.0', port=5001)
