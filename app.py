import os
import uuid
import secrets

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))
except ImportError:
    pass
import smtplib
from datetime import datetime, timedelta
from email.message import EmailMessage
from functools import wraps
from flask import (Flask, render_template, request, jsonify,
                   redirect, url_for, session, flash, send_from_directory)
from werkzeug.utils import secure_filename
import sqlite3

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY') or 'primores-jaarclub-local-dev-only'

BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
DB_PATH       = os.path.join(BASE_DIR, 'primores.db')
ALLOWED_EXT   = {'jpg', 'jpeg', 'png', 'gif', 'webp', 'heic', 'heif'}

app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB

MEMBERS = [
    {'name': 'Bart',       'color': '#e67e22'},
    {'name': 'Bas',        'color': '#3498db'},
    {'name': 'Eric',       'color': '#9b59b6'},
    {'name': 'Gert',       'color': '#00cec9'},
    {'name': 'Glenn',      'color': '#27ae60'},
    {'name': 'Jeroen D',   'color': '#e74c3c'},
    {'name': 'Jeroen R',   'color': '#d63031'},
    {'name': 'Lutze',      'color': '#f0a500'},
    {'name': 'Marcel',     'color': '#d35400'},
    {'name': 'Onno',       'color': '#00b894'},
    {'name': 'Paul',       'color': '#6c5ce7'},
    {'name': 'Peter',      'color': '#0984e3'},
    {'name': 'Robert-Jan', 'color': '#2980b9'},
    {'name': 'Robin',      'color': '#a29bfe'},
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
        CREATE TABLE IF NOT EXISTS profiles (
            person_name    TEXT PRIMARY KEY,
            photo_filename TEXT
        );
        CREATE TABLE IF NOT EXISTS users (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            email      TEXT UNIQUE NOT NULL COLLATE NOCASE,
            name       TEXT NOT NULL DEFAULT '',
            role       TEXT NOT NULL DEFAULT 'user',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS magic_tokens (
            token      TEXT PRIMARY KEY,
            user_id    INTEGER NOT NULL,
            expires_at TEXT NOT NULL
        );
    ''')
    for col_def in ['location_name TEXT', 'location_lat REAL', 'location_lng REAL', 'url TEXT']:
        try:
            conn.execute(f'ALTER TABLE events ADD COLUMN {col_def}')
        except Exception:
            pass
    existing = conn.execute("SELECT id FROM users WHERE email='eric@it-mannetje.nl'").fetchone()
    if not existing:
        conn.execute("INSERT INTO users (email, name, role) VALUES (?, ?, ?)",
                     ('eric@it-mannetje.nl', 'Eric', 'admin'))
    conn.commit()
    conn.close()


def get_member_photos():
    conn = get_db()
    rows = conn.execute('SELECT person_name, photo_filename FROM profiles').fetchall()
    conn.close()
    return {r['person_name']: r['photo_filename'] for r in rows}


@app.context_processor
def inject_context():
    current_user = None
    if session.get('user_id'):
        current_user = {
            'id':    session['user_id'],
            'email': session.get('user_email', ''),
            'name':  session.get('user_name', ''),
            'role':  session.get('user_role', 'user'),
        }
    try:
        photos = get_member_photos()
        member_photos = {
            name: url_for('uploaded_file', filename=fn)
            for name, fn in photos.items() if fn
        }
    except Exception:
        member_photos = {}
    return dict(member_photos=member_photos, current_user=current_user)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT


# ── Auth decorators ───────────────────────────────────────────────

def require_login(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('user_id'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated


def require_superuser(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('user_id'):
            return redirect(url_for('admin_login'))
        if session.get('user_role') not in ('admin', 'superuser'):
            flash('Je hebt geen toegang tot deze functie.', 'error')
            return redirect(url_for('admin'))
        return f(*args, **kwargs)
    return decorated


def require_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('user_id'):
            return redirect(url_for('admin_login'))
        if session.get('user_role') != 'admin':
            flash('Je hebt geen toegang tot deze functie.', 'error')
            return redirect(url_for('admin'))
        return f(*args, **kwargs)
    return decorated


# ── Helpers ───────────────────────────────────────────────────────

def member_by_name(name):
    return next((m for m in MEMBERS if m['name'] == name), None)


def save_photo(file_field):
    photo = request.files.get(file_field)
    if photo and photo.filename and allowed_file(photo.filename):
        ext = photo.filename.rsplit('.', 1)[1].lower()
        if ext in ('heic', 'heif'):
            ext = 'jpg'
        filename = f"{uuid.uuid4().hex}.{ext}"
        img_path = os.path.join(UPLOAD_FOLDER, filename)
        photo.save(img_path)
        try:
            from PIL import Image, ImageOps
            with Image.open(img_path) as img:
                img = ImageOps.exif_transpose(img)
                img.thumbnail((1200, 900), Image.LANCZOS)
                save_kwargs = {'optimize': True}
                if img.format != 'PNG':
                    save_kwargs['quality'] = 85
                img.save(img_path, **save_kwargs)
        except Exception:
            pass
        return filename
    return None


def delete_photo(filename):
    if filename:
        path = os.path.join(UPLOAD_FOLDER, filename)
        if os.path.exists(path):
            os.remove(path)


def send_magic_link(to_email, magic_url):
    """Send magic link email. Set MAIL_DEBUG=1 to log the link instead of sending."""
    if os.environ.get('MAIL_DEBUG') == '1':
        app.logger.warning('MAIL_DEBUG: magic link for %s → %s', to_email, magic_url)
        return True

    mail_server   = os.environ.get('MAIL_SERVER', 'localhost')
    mail_port     = int(os.environ.get('MAIL_PORT', '587'))
    mail_username = os.environ.get('MAIL_USERNAME', '')
    mail_password = os.environ.get('MAIL_PASSWORD', '')
    mail_from     = os.environ.get('MAIL_FROM') or mail_username
    use_tls       = os.environ.get('MAIL_USE_TLS', '1') == '1'

    msg = EmailMessage()
    msg['Subject'] = 'Inloglink Canon Primores'
    msg['From']    = mail_from
    msg['To']      = to_email

    text_body = (
        f'Klik op de volgende link om in te loggen bij de Canon Primores beheeromgeving:\n\n'
        f'{magic_url}\n\n'
        f'Deze link is 15 minuten geldig en kan slechts eenmalig gebruikt worden.\n'
        f'Heb je deze link niet aangevraagd? Doe dan niets.'
    )
    html_body = f'''
<div style="font-family:sans-serif;max-width:520px;margin:0 auto;padding:2rem">
  <h2 style="color:#8B6914;margin-bottom:.5rem">Canon Primores</h2>
  <p style="color:#444">Klik op de onderstaande knop om in te loggen bij de beheeromgeving.</p>
  <p style="margin:2rem 0">
    <a href="{magic_url}"
       style="background:#8B6914;color:#fff;padding:.75rem 1.75rem;text-decoration:none;
              border-radius:6px;font-weight:600;display:inline-block">
      Inloggen
    </a>
  </p>
  <p style="color:#888;font-size:.85rem">
    Of kopieer deze link in je browser:<br>
    <span style="color:#555;word-break:break-all">{magic_url}</span>
  </p>
  <hr style="border:none;border-top:1px solid #eee;margin:1.5rem 0">
  <p style="color:#aaa;font-size:.8rem">
    Deze link is 15 minuten geldig en eenmalig te gebruiken.<br>
    Heb je deze link niet aangevraagd? Dan hoef je niets te doen.
  </p>
</div>'''

    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype='html')

    try:
        with smtplib.SMTP(mail_server, mail_port) as server:
            if use_tls:
                server.starttls()
            if mail_username:
                server.login(mail_username, mail_password)
            server.send_message(msg)
        return True
    except Exception as exc:
        import traceback
        app.logger.error('Failed to send magic link to %s: %s\n%s',
                         to_email, exc, traceback.format_exc())
        return False


# ── Public routes ─────────────────────────────────────────────────

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
        color = '#B91C1C'
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
            'location_name': e['location_name'],
            'location_lat':  e['location_lat'],
            'location_lng':  e['location_lng'],
            'url':           e['url'],
        })
    return jsonify(result)


@app.route('/kaart')
def kaart():
    return render_template('kaart.html', members=MEMBERS)


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
        title         = request.form.get('title', '').strip()
        description   = request.form.get('description', '').strip()
        location_name = request.form.get('location_name', '').strip() or None
        location_lat  = request.form.get('location_lat', type=float)
        location_lng  = request.form.get('location_lng', type=float)
        url           = request.form.get('url', '').strip() or None

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
            'INSERT INTO events (person_name, date_year, date_month, date_day, title, description, '
            'photo_filename, approved, is_primores, location_name, location_lat, location_lng, url) '
            'VALUES (?,?,?,?,?,?,?,0,0,?,?,?,?)',
            (member['name'], date_year, date_month, date_day, title, description, photo_filename,
             location_name, location_lat, location_lng, url)
        )
        conn.commit()
        conn.close()

        flash('Bedankt! Je bijdrage is ontvangen en verschijnt na goedkeuring op de tijdlijn.', 'success')
        return redirect(url_for('submit', person_name=member['name']))

    return render_template('submit.html', member=member, members=MEMBERS)


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, secure_filename(filename))


# ── Admin auth routes ─────────────────────────────────────────────

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if session.get('user_id'):
        return redirect(url_for('admin'))
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        conn = get_db()
        user = conn.execute('SELECT * FROM users WHERE email=?', (email,)).fetchone()
        if user:
            token = secrets.token_urlsafe(32)
            expires_at = (datetime.utcnow() + timedelta(minutes=15)).isoformat()
            conn.execute('DELETE FROM magic_tokens WHERE user_id=?', (user['id'],))
            conn.execute('INSERT INTO magic_tokens (token, user_id, expires_at) VALUES (?,?,?)',
                         (token, user['id'], expires_at))
            conn.commit()
            magic_url = url_for('admin_auth', token=token, _external=True)
            send_magic_link(email, magic_url)
        conn.close()
        return render_template('admin_login.html', sent=True, email=email)
    return render_template('admin_login.html', sent=False)


@app.route('/admin/auth/<token>')
def admin_auth(token):
    conn = get_db()
    row = conn.execute(
        'SELECT t.*, u.id AS uid, u.email, u.name, u.role '
        'FROM magic_tokens t JOIN users u ON u.id = t.user_id WHERE t.token=?',
        (token,)
    ).fetchone()
    if not row:
        conn.close()
        flash('Ongeldige of verlopen inloglink.', 'error')
        return redirect(url_for('admin_login'))
    if datetime.utcnow().isoformat() > row['expires_at']:
        conn.execute('DELETE FROM magic_tokens WHERE token=?', (token,))
        conn.commit()
        conn.close()
        flash('Deze inloglink is verlopen. Vraag een nieuwe aan.', 'error')
        return redirect(url_for('admin_login'))
    conn.execute('DELETE FROM magic_tokens WHERE token=?', (token,))
    conn.commit()
    conn.close()
    session['user_id']    = row['uid']
    session['user_email'] = row['email']
    session['user_name']  = row['name']
    session['user_role']  = row['role']
    return redirect(url_for('admin'))


@app.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect(url_for('index'))


# ── Admin routes ──────────────────────────────────────────────────

@app.route('/admin')
@require_login
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
    users = []
    if session.get('user_role') == 'admin':
        users = conn.execute('SELECT * FROM users ORDER BY role, name').fetchall()
    conn.close()
    return render_template('admin.html',
                           pending=pending, primores_events=primores,
                           approved_events=approved, members=MEMBERS,
                           member_by_name=member_by_name, users=users)


@app.route('/admin/approve/<int:eid>', methods=['POST'])
@require_superuser
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


@app.route('/admin/profiles/upload/<person_name>', methods=['POST'])
@require_superuser
def admin_upload_profile(person_name):
    if not member_by_name(person_name):
        return 'Persoon niet gevonden', 404
    photo = request.files.get('photo')
    if photo and photo.filename and allowed_file(photo.filename):
        ext = photo.filename.rsplit('.', 1)[1].lower()
        slug = person_name.lower().replace(' ', '_').replace('-', '_')
        filename = f'profile_{slug}.{ext}'
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        photo.save(filepath)
        try:
            from PIL import Image
            with Image.open(filepath) as img:
                w, h = img.size
                size = min(w, h)
                img = img.crop(((w-size)//2, (h-size)//2, (w+size)//2, (h+size)//2))
                img = img.resize((300, 300), Image.LANCZOS)
                img.save(filepath, optimize=True, quality=90)
        except Exception:
            pass
        conn = get_db()
        old = conn.execute('SELECT photo_filename FROM profiles WHERE person_name=?',
                           (person_name,)).fetchone()
        if old and old['photo_filename'] and old['photo_filename'] != filename:
            delete_photo(old['photo_filename'])
        conn.execute('INSERT OR REPLACE INTO profiles (person_name, photo_filename) VALUES (?,?)',
                     (person_name, filename))
        conn.commit()
        conn.close()
        flash(f'Profielfoto voor {person_name} bijgewerkt.', 'success')
    return redirect(url_for('admin') + '?tab=profiles')


@app.route('/admin/profiles/delete/<person_name>', methods=['POST'])
@require_admin
def admin_delete_profile(person_name):
    conn = get_db()
    row = conn.execute('SELECT photo_filename FROM profiles WHERE person_name=?',
                       (person_name,)).fetchone()
    if row and row['photo_filename']:
        delete_photo(row['photo_filename'])
    conn.execute('DELETE FROM profiles WHERE person_name=?', (person_name,))
    conn.commit()
    conn.close()
    flash(f'Profielfoto voor {person_name} verwijderd.', 'success')
    return redirect(url_for('admin') + '?tab=profiles')


@app.route('/admin/approved/edit/<int:eid>', methods=['POST'])
@require_superuser
def admin_edit_approved(eid):
    conn = get_db()
    old = conn.execute('SELECT * FROM events WHERE id=?', (eid,)).fetchone()
    conn.close()

    date_year     = request.form.get('date_year', type=int)
    date_month    = request.form.get('date_month', type=int) or None
    date_day      = request.form.get('date_day', type=int) or None
    title         = request.form.get('title', '').strip()
    description   = request.form.get('description', '').strip()
    location_name = request.form.get('location_name', '').strip() or None
    location_lat  = request.form.get('location_lat', type=float)
    location_lng  = request.form.get('location_lng', type=float)
    url           = request.form.get('url', '').strip() or None

    photo_filename = old['photo_filename'] if old else None
    new_photo = save_photo('photo')
    if new_photo:
        delete_photo(photo_filename)
        photo_filename = new_photo

    conn = get_db()
    conn.execute(
        'UPDATE events SET date_year=?, date_month=?, date_day=?, title=?, description=?, '
        'photo_filename=?, location_name=?, location_lat=?, location_lng=?, url=? WHERE id=?',
        (date_year, date_month, date_day, title, description, photo_filename,
         location_name, location_lat, location_lng, url, eid)
    )
    conn.commit()
    conn.close()
    flash('Bijdrage bijgewerkt.', 'success')
    return redirect(url_for('admin') + '?tab=approved')


@app.route('/admin/primores/add', methods=['POST'])
@require_superuser
def admin_add_primores():
    return _upsert_event(None, is_primores=True)


@app.route('/admin/primores/edit/<int:eid>', methods=['POST'])
@require_superuser
def admin_edit_primores(eid):
    conn = get_db()
    old = conn.execute('SELECT * FROM events WHERE id=?', (eid,)).fetchone()
    conn.close()

    date_year  = request.form.get('date_year', type=int)
    date_month = request.form.get('date_month', type=int) or None
    date_day   = request.form.get('date_day', type=int) or None
    title         = request.form.get('title', '').strip()
    description   = request.form.get('description', '').strip()
    location_name = request.form.get('location_name', '').strip() or None
    location_lat  = request.form.get('location_lat', type=float)
    location_lng  = request.form.get('location_lng', type=float)
    url           = request.form.get('url', '').strip() or None

    photo_filename = old['photo_filename'] if old else None
    new_photo = save_photo('photo')
    if new_photo:
        delete_photo(photo_filename)
        photo_filename = new_photo

    conn = get_db()
    conn.execute(
        'UPDATE events SET date_year=?, date_month=?, date_day=?, title=?, description=?, '
        'photo_filename=?, location_name=?, location_lat=?, location_lng=?, url=? WHERE id=?',
        (date_year, date_month, date_day, title, description, photo_filename,
         location_name, location_lat, location_lng, url, eid)
    )
    conn.commit()
    conn.close()
    flash('Evenement bijgewerkt.', 'success')
    return redirect(url_for('admin') + '?tab=primores')


def _upsert_event(person_name, is_primores):
    date_year  = request.form.get('date_year', type=int)
    date_month = request.form.get('date_month', type=int) or None
    date_day   = request.form.get('date_day', type=int) or None
    title         = request.form.get('title', '').strip()
    description   = request.form.get('description', '').strip()
    location_name = request.form.get('location_name', '').strip() or None
    location_lat  = request.form.get('location_lat', type=float)
    location_lng  = request.form.get('location_lng', type=float)
    url           = request.form.get('url', '').strip() or None

    if not date_year or not title:
        flash('Jaar en titel zijn verplicht.', 'error')
        return redirect(url_for('admin') + '?tab=primores')

    photo_filename = save_photo('photo')

    conn = get_db()
    conn.execute(
        'INSERT INTO events (person_name, date_year, date_month, date_day, title, description, '
        'photo_filename, approved, is_primores, location_name, location_lat, location_lng, url) '
        'VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',
        (person_name, date_year, date_month, date_day, title, description, photo_filename,
         1 if is_primores else 0, 1 if is_primores else 0,
         location_name, location_lat, location_lng, url)
    )
    conn.commit()
    conn.close()
    flash('Evenement toegevoegd.', 'success')
    return redirect(url_for('admin') + '?tab=primores')


# ── User management routes (admin only) ──────────────────────────

@app.route('/admin/users/add', methods=['POST'])
@require_admin
def admin_users_add():
    email = request.form.get('email', '').strip().lower()
    name  = request.form.get('name', '').strip()
    role  = request.form.get('role', 'user')
    if role not in ('admin', 'superuser', 'user'):
        role = 'user'
    if not email:
        flash('E-mailadres is verplicht.', 'error')
        return redirect(url_for('admin') + '?tab=users')
    conn = get_db()
    try:
        conn.execute('INSERT INTO users (email, name, role) VALUES (?,?,?)', (email, name, role))
        conn.commit()
        flash(f'Gebruiker {email} toegevoegd.', 'success')
    except Exception:
        flash('Dit e-mailadres is al in gebruik.', 'error')
    conn.close()
    return redirect(url_for('admin') + '?tab=users')


@app.route('/admin/users/edit/<int:uid>', methods=['POST'])
@require_admin
def admin_users_edit(uid):
    name = request.form.get('name', '').strip()
    role = request.form.get('role', 'user')
    if role not in ('admin', 'superuser', 'user'):
        role = 'user'
    conn = get_db()
    if role != 'admin':
        admin_count = conn.execute("SELECT COUNT(*) FROM users WHERE role='admin'").fetchone()[0]
        current = conn.execute("SELECT role FROM users WHERE id=?", (uid,)).fetchone()
        if current and current['role'] == 'admin' and admin_count <= 1:
            flash('Er moet altijd minimaal één beheerder zijn.', 'error')
            conn.close()
            return redirect(url_for('admin') + '?tab=users')
    conn.execute('UPDATE users SET name=?, role=? WHERE id=?', (name, role, uid))
    conn.commit()
    conn.close()
    flash('Gebruiker bijgewerkt.', 'success')
    return redirect(url_for('admin') + '?tab=users')


@app.route('/admin/users/delete/<int:uid>', methods=['POST'])
@require_admin
def admin_users_delete(uid):
    if uid == session.get('user_id'):
        flash('Je kunt jezelf niet verwijderen.', 'error')
        return redirect(url_for('admin') + '?tab=users')
    conn = get_db()
    conn.execute('DELETE FROM magic_tokens WHERE user_id=?', (uid,))
    conn.execute('DELETE FROM users WHERE id=?', (uid,))
    conn.commit()
    conn.close()
    flash('Gebruiker verwijderd.', 'success')
    return redirect(url_for('admin') + '?tab=users')


if __name__ == '__main__':
    init_db()
    from seed_data import seed, seed_locations
    seed(DB_PATH)
    seed_locations(DB_PATH)
    app.run(debug=True, host='0.0.0.0', port=5001)
