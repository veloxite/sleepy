"""SQLite persistence for text/settings; never stores screen images."""
import json
import sqlite3
import uuid
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"

class Store:
    def __init__(self, path=None):
        path = Path(path) if path else DATA_DIR / "agent.sqlite3"
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path=path
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.executescript('''
            PRAGMA foreign_keys = ON;
            CREATE TABLE IF NOT EXISTS chats (id TEXT PRIMARY KEY, title TEXT NOT NULL,
                updated TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY,
                chat_id TEXT REFERENCES chats(id) ON DELETE CASCADE,
                role TEXT NOT NULL, content TEXT NOT NULL, screen INTEGER DEFAULT 0);
            CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS messages_chat_id ON messages(chat_id,id);
        ''')

    def new_chat(self):
        # An empty composer is not a saved conversation.
        return uuid.uuid4().hex

    def chats(self):
        return [dict(r) for r in self.db.execute('SELECT * FROM chats WHERE EXISTS (SELECT 1 FROM messages WHERE chat_id=chats.id) ORDER BY updated DESC, rowid DESC')]

    def messages(self, cid):
        return [dict(r) for r in self.db.execute('SELECT role,content,screen FROM messages WHERE chat_id=? ORDER BY id', (cid,))]

    def recent_context(self,cid,limit=16):
        rows=self.db.execute("SELECT role,content,screen FROM messages WHERE chat_id=? AND role IN ('user','assistant') ORDER BY id DESC LIMIT ?",(cid,limit)).fetchall()
        return [dict(r) for r in reversed(rows)]

    def add(self, cid, role, content, screen=False):
        with self.db:
            self.db.execute('INSERT OR IGNORE INTO chats(id,title) VALUES (?,?)', (cid, 'New conversation'))
            cursor = self.db.execute('INSERT INTO messages(chat_id,role,content,screen) VALUES (?,?,?,?)', (cid, role, content, int(screen)))
            if role == 'user' and self.db.execute("SELECT COUNT(*) FROM messages WHERE chat_id=? AND role='user'", (cid,)).fetchone()[0] == 1:
                self.db.execute('UPDATE chats SET title=? WHERE id=?', (content.replace('\n', ' ')[:60], cid))
            self.db.execute('UPDATE chats SET updated=CURRENT_TIMESTAMP WHERE id=?', (cid,))
        return cursor.lastrowid

    def mark_screen(self, message_id):
        with self.db:
            self.db.execute('UPDATE messages SET screen=1 WHERE id=?', (message_id,))

    def delete(self, cid):
        with self.db:
            self.db.execute('DELETE FROM chats WHERE id=?', (cid,))
            self.db.execute('DELETE FROM settings WHERE key=?', ('draft:' + cid,))

    def rename(self,cid,title):
        with self.db:
            self.db.execute('UPDATE chats SET title=? WHERE id=?',(title,cid))

    def get(self, key, default=None):
        row = self.db.execute('SELECT value FROM settings WHERE key=?', (key,)).fetchone()
        return json.loads(row[0]) if row else default

    def set(self, key, value):
        with self.db:
            self.db.execute('INSERT INTO settings(key,value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value WHERE settings.value != excluded.value', (key, json.dumps(value)))

    def close(self):
        self.db.close()
