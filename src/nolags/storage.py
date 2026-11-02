import json
import os
import sqlite3
import time
from pathlib import Path

from . import paths


class Storage:
    def __init__(self, base=None):
        self.base = Path(base) if base else paths.data_root()
        self.base.mkdir(parents=True, exist_ok=True)
        self.db_path = self.base / "profile.db"
        self.db = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=NORMAL")
        self._create()

    def _create(self):
        self.db.executescript(
            """
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL,
                title TEXT,
                host TEXT,
                visits INTEGER DEFAULT 1,
                last_visit REAL NOT NULL
            );
            CREATE UNIQUE INDEX IF NOT EXISTS history_url ON history(url);
            CREATE INDEX IF NOT EXISTS history_last ON history(last_visit DESC);
            CREATE TABLE IF NOT EXISTS bookmarks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL UNIQUE,
                title TEXT,
                folder TEXT DEFAULT '',
                position INTEGER DEFAULT 0,
                created REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS downloads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT,
                filename TEXT,
                path TEXT,
                size INTEGER DEFAULT 0,
                state TEXT,
                created REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS tabs (
                id INTEGER PRIMARY KEY,
                slot INTEGER,
                url TEXT,
                title TEXT,
                pinned INTEGER DEFAULT 0,
                created REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT,
                title TEXT,
                body TEXT,
                created REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS meta (
                key TEXT PRIMARY KEY,
                value TEXT
            );
            """
        )
        self.db.commit()

    def close(self):
        try:
            self.db.commit()
            self.db.close()
        except sqlite3.Error:
            pass

    def add_history(self, url, title, host):
        if not url or url.startswith(("nolags:", "about:", "data:")):
            return
        now = time.time()
        self.db.execute(
            """
            INSERT INTO history (url, title, host, visits, last_visit) VALUES (?, ?, ?, 1, ?)
            ON CONFLICT(url) DO UPDATE SET
                title = COALESCE(NULLIF(excluded.title, ''), history.title),
                visits = history.visits + 1,
                last_visit = excluded.last_visit
            """,
            (url, title or "", host or "", now),
        )
        self.db.commit()

    def remove_history(self, url):
        self.db.execute("DELETE FROM history WHERE url = ?", (url,))
        self.db.commit()

    def clear_history(self, since=None):
        if since is None:
            self.db.execute("DELETE FROM history")
        else:
            self.db.execute("DELETE FROM history WHERE last_visit < ?", (since,))
        self.db.commit()

    def history(self, query="", limit=300, offset=0):
        if query:
            like = "%" + query + "%"
            rows = self.db.execute(
                """
                SELECT * FROM history WHERE url LIKE ? OR title LIKE ? OR host LIKE ?
                ORDER BY last_visit DESC LIMIT ? OFFSET ?
                """,
                (like, like, like, limit, offset),
            ).fetchall()
        else:
            rows = self.db.execute(
                "SELECT * FROM history ORDER BY last_visit DESC LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
        return [dict(row) for row in rows]

    def history_by_day(self, days=30):
        cutoff = time.time() - days * 86400
        rows = self.db.execute(
            "SELECT * FROM history WHERE last_visit >= ? ORDER BY last_visit DESC",
            (cutoff,),
        ).fetchall()
        grouped = {}
        for row in rows:
            key = time.strftime("%Y-%m-%d", time.localtime(row["last_visit"]))
            grouped.setdefault(key, []).append(dict(row))
        return grouped

    def top_sites(self, limit=12):
        rows = self.db.execute(
            """
            SELECT host, title, url, SUM(visits) AS score FROM history
            WHERE host != '' AND last_visit > ?
            GROUP BY host ORDER BY score DESC LIMIT ?
            """,
            (time.time() - 90 * 86400, limit),
        ).fetchall()
        return [dict(row) for row in rows]

    def recent_hosts(self, limit=6):
        rows = self.db.execute(
            """
            SELECT host, MAX(last_visit) AS ts, url FROM history
            WHERE host != '' GROUP BY host ORDER BY ts DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]

    def history_host_suggestions(self, text, limit=6):
        like = "%" + text + "%"
        rows = self.db.execute(
            """
            SELECT host, url, title, MAX(visits) AS score FROM history
            WHERE (host LIKE ? OR url LIKE ? OR title LIKE ?) AND host != ''
            GROUP BY host ORDER BY score DESC LIMIT ?
            """,
            (like, like, like, limit),
        ).fetchall()
        return [dict(row) for row in rows]

    def add_bookmark(self, url, title, folder=""):
        now = time.time()
        self.db.execute(
            """
            INSERT INTO bookmarks (url, title, folder, position, created) VALUES (?, ?, ?, 0, ?)
            ON CONFLICT(url) DO UPDATE SET title = excluded.title, folder = excluded.folder
            """,
            (url, title or url, folder, now),
        )
        self.db.commit()

    def remove_bookmark(self, url):
        self.db.execute("DELETE FROM bookmarks WHERE url = ?", (url,))
        self.db.commit()

    def bookmarks(self, folder=None):
        if folder is None:
            rows = self.db.execute(
                "SELECT * FROM bookmarks ORDER BY folder, position, created"
            ).fetchall()
        else:
            rows = self.db.execute(
                "SELECT * FROM bookmarks WHERE folder = ? ORDER BY position, created",
                (folder,),
            ).fetchall()
        return [dict(row) for row in rows]

    def is_bookmarked(self, url):
        row = self.db.execute("SELECT id FROM bookmarks WHERE url = ?", (url,)).fetchone()
        return row is not None

    def bookmark_folders(self):
        rows = self.db.execute(
            "SELECT DISTINCT folder FROM bookmarks WHERE folder != '' ORDER BY folder"
        ).fetchall()
        return [row["folder"] for row in rows]

    def search_bookmarks(self, text, limit=5):
        like = "%" + text + "%"
        rows = self.db.execute(
            "SELECT * FROM bookmarks WHERE url LIKE ? OR title LIKE ? LIMIT ?",
            (like, like, limit),
        ).fetchall()
        return [dict(row) for row in rows]

    def add_download(self, url, filename, path, size, state):
        cur = self.db.execute(
            "INSERT INTO downloads (url, filename, path, size, state, created) VALUES (?, ?, ?, ?, ?, ?)",
            (url, filename, path, size, state, time.time()),
        )
        self.db.commit()
        return cur.lastrowid

    def update_download(self, row_id, state=None, size=None):
        if row_id is None:
            return
        if state is not None and size is not None:
            self.db.execute("UPDATE downloads SET state = ?, size = ? WHERE id = ?", (state, size, row_id))
        elif state is not None:
            self.db.execute("UPDATE downloads SET state = ? WHERE id = ?", (state, row_id))
        elif size is not None:
            self.db.execute("UPDATE downloads SET size = ? WHERE id = ?", (size, row_id))
        self.db.commit()

    def downloads(self, limit=200):
        rows = self.db.execute(
            "SELECT * FROM downloads ORDER BY created DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(row) for row in rows]

    def clear_downloads(self):
        self.db.execute("DELETE FROM downloads")
        self.db.commit()

    def add_note(self, url, title, body):
        self.db.execute(
            "INSERT INTO notes (url, title, body, created) VALUES (?, ?, ?, ?)",
            (url, title, body, time.time()),
        )
        self.db.commit()

    def notes(self, limit=200):
        rows = self.db.execute(
            "SELECT * FROM notes ORDER BY created DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(row) for row in rows]

    def delete_note(self, note_id):
        self.db.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        self.db.commit()

    def save_tabs(self, tabs):
        self.db.execute("DELETE FROM tabs")
        now = time.time()
        for index, tab in enumerate(tabs):
            self.db.execute(
                "INSERT INTO tabs (slot, url, title, pinned, created) VALUES (?, ?, ?, ?, ?)",
                (index, tab.get("url", ""), tab.get("title", ""), 1 if tab.get("pinned") else 0, now),
            )
        self.db.commit()

    def load_tabs(self):
        rows = self.db.execute("SELECT * FROM tabs ORDER BY slot").fetchall()
        return [dict(row) for row in rows]

    def clear_tabs(self):
        self.db.execute("DELETE FROM tabs")
        self.db.commit()

    def meta_set(self, key, value):
        self.db.execute(
            "INSERT INTO meta (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, json.dumps(value)),
        )
        self.db.commit()

    def meta_get(self, key, default=None):
        row = self.db.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
        if not row:
            return default
        try:
            return json.loads(row["value"])
        except ValueError:
            return default

    def stats(self):
        history = self.db.execute("SELECT COUNT(*) AS c FROM history").fetchone()["c"]
        bookmarks = self.db.execute("SELECT COUNT(*) AS c FROM bookmarks").fetchone()["c"]
        downloads = self.db.execute("SELECT COUNT(*) AS c FROM downloads").fetchone()["c"]
        size = 0
        for path in self.base.glob("*"):
            try:
                size += os.path.getsize(path)
            except OSError:
                pass
        return {"history": history, "bookmarks": bookmarks, "downloads": downloads, "db_size": size}

    def export_history(self, path):
        data = [dict(row) for row in self.db.execute("SELECT * FROM history ORDER BY last_visit DESC")]
        Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return len(data)

    def export_bookmarks_json(self, path):
        data = [dict(row) for row in self.db.execute("SELECT * FROM bookmarks")]
        Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return len(data)

    def export_bookmarks_html(self, path):
        rows = self.db.execute("SELECT * FROM bookmarks ORDER BY folder, created").fetchall()
        folders = {}
        for row in rows:
            folders.setdefault(row["folder"] or "", []).append(row)
        parts = [
            "<!DOCTYPE NETSCAPE-Bookmark-file-1>",
            "<META HTTP-EQUIV=\"Content-Type\" CONTENT=\"text/html; charset=UTF-8\">",
            "<TITLE>Bookmarks</TITLE><H1>Bookmarks</H1><DL><p>",
        ]
        for folder, items in folders.items():
            if folder:
                parts.append(f"    <DT><H3>{folder}</H3><DL><p>")
            for item in items:
                title = (item["title"] or item["url"]).replace("<", "&lt;").replace(">", "&gt;")
                parts.append(
                    f'        <DT><A HREF="{item["url"]}" ADD_DATE="{int(item["created"])}">{title}</A>'
                )
            if folder:
                parts.append("    </DL><p>")
        parts.append("</DL><p>")
        Path(path).write_text("\n".join(parts), encoding="utf-8")
        return len(rows)

    def import_bookmarks_html(self, path):
        import re

        text = Path(path).read_text(encoding="utf-8", errors="replace")
        pattern = re.compile(r'<A[^>]+HREF="([^"]+)"[^>]*>(.*?)</A>', re.IGNORECASE | re.DOTALL)
        count = 0
        for url, title in pattern.findall(text):
            title = re.sub(r"<[^>]+>", "", title).strip()
            if url.startswith(("http://", "https://")):
                self.add_bookmark(url, title or url)
                count += 1
        return count

    def vacuum(self):
        try:
            self.db.execute("VACUUM")
            self.db.commit()
        except sqlite3.Error:
            pass

    def wipe(self, what):
        mapping = {
            "history": "DELETE FROM history",
            "bookmarks": "DELETE FROM bookmarks",
            "downloads": "DELETE FROM downloads",
            "notes": "DELETE FROM notes",
            "tabs": "DELETE FROM tabs",
        }
        for key in what:
            sql = mapping.get(key)
            if sql:
                self.db.execute(sql)
        self.db.commit()
