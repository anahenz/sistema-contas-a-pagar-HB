from contextlib import contextmanager
import hashlib
import hmac
import secrets
import sqlite3
import time


def password_hash(password):
    if not isinstance(password, str) or not 12 <= len(password) <= 256:
        raise ValueError('Use uma senha com 12 a 256 caracteres.')
    salt = secrets.token_hex(16)
    digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1).hex()
    return salt + ':' + digest


def verify(password, saved):
    salt, digest = saved.split(':')
    actual = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1).hex()
    return hmac.compare_digest(actual, digest)


class Security:
    def __init__(self, path, email, password):
        self.path = str(path)
        with self.connection() as c:
            c.executescript('''
                CREATE TABLE IF NOT EXISTS users (
                  id INTEGER PRIMARY KEY, email TEXT UNIQUE NOT NULL,
                  password TEXT NOT NULL, role TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1);
                CREATE TABLE IF NOT EXISTS sessions (
                  digest TEXT PRIMARY KEY, user_id INTEGER NOT NULL, expires REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS attempts (
                  email TEXT PRIMARY KEY, count INTEGER NOT NULL, until REAL NOT NULL);
            ''')
            if not c.execute('SELECT 1 FROM users LIMIT 1').fetchone():
                self.add_user(email, password, 'admin')
        self.dummy = password_hash(secrets.token_urlsafe(24))

    @contextmanager
    def connection(self):
        c = sqlite3.connect(self.path, timeout=30)
        c.row_factory = sqlite3.Row
        try:
            with c:
                yield c
        finally:
            c.close()

    def add_user(self, email, password, role='editor'):
        email = email.strip().lower()
        if '@' not in email or len(email) > 200 or role not in ('admin', 'editor'):
            raise ValueError('Informe e-mail e perfil válidos.')
        hashed = password_hash(password)
        with self.connection() as c:
            try:
                c.execute('INSERT INTO users(email,password,role) VALUES (?,?,?)', (email, hashed, role))
            except sqlite3.IntegrityError:
                raise ValueError('Este e-mail já está cadastrado.') from None

    def login(self, email, password):
        email = email.strip().lower()
        with self.connection() as c:
            attempt = c.execute('SELECT * FROM attempts WHERE email=?', (email,)).fetchone()
            if attempt and attempt['count'] >= 8 and attempt['until'] > time.time():
                raise ValueError('Muitas tentativas. Aguarde 15 minutos.')
            user = c.execute('SELECT * FROM users WHERE email=? AND active=1', (email,)).fetchone()
            valid = verify(password, user['password'] if user else self.dummy)
            if not user or not valid:
                count = attempt['count'] + 1 if attempt and attempt['until'] > time.time() else 1
                c.execute('INSERT OR REPLACE INTO attempts VALUES (?,?,?)', (email, count, time.time()+900))
                c.commit()
                raise ValueError('E-mail ou senha incorretos.')
            c.execute('DELETE FROM attempts WHERE email=?', (email,))
            c.execute('DELETE FROM sessions WHERE expires<?', (time.time(),))
            token = secrets.token_urlsafe(48)
            c.execute('INSERT INTO sessions VALUES (?,?,?)', (self.digest(token), user['id'], time.time()+12*3600))
            return {'token': token, 'email': user['email'], 'role': user['role']}

    @staticmethod
    def digest(token):
        return hashlib.sha256(token.encode()).hexdigest()

    def user(self, token):
        with self.connection() as c:
            row = c.execute('''SELECT u.id,u.email,u.role FROM users u JOIN sessions s ON s.user_id=u.id
                WHERE s.digest=? AND s.expires>? AND u.active=1''', (self.digest(token), time.time())).fetchone()
            return dict(row) if row else None

    def logout(self, token):
        with self.connection() as c:
            c.execute('DELETE FROM sessions WHERE digest=?', (self.digest(token),))

    def users(self):
        with self.connection() as c:
            return [dict(r) for r in c.execute('SELECT id,email,role,active FROM users ORDER BY email')]

    def update(self, user_id, password=None, active=None):
        with self.connection() as c:
            if not c.execute('SELECT 1 FROM users WHERE id=?', (user_id,)).fetchone():
                raise ValueError('Usuário não encontrado.')
            if password is not None:
                c.execute('UPDATE users SET password=? WHERE id=?', (password_hash(password), user_id))
            if active is not None:
                c.execute('UPDATE users SET active=? WHERE id=?', (int(active), user_id))
            c.execute('DELETE FROM sessions WHERE user_id=?', (user_id,))
