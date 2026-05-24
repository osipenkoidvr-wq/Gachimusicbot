#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Music Playlist Bot — database.py

import aiosqlite
import logging

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path

    async def init(self):
        """Создаёт таблицы при первом запуске."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id   INTEGER PRIMARY KEY,
                    username  TEXT,
                    joined_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS songs (
                    id        INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id   INTEGER NOT NULL,
                    title     TEXT NOT NULL,
                    added_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key   TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)
            # Дефолтный лимит = 30
            await db.execute("""
                INSERT OR IGNORE INTO settings (key, value)
                VALUES ('max_songs', '30')
            """)
            await db.commit()
        logger.info("✅ База данных инициализирована: %s", self.db_path)

    async def ensure_user(self, user_id: int, username: str | None):
        """Создаёт запись пользователя, если её нет."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)",
                (user_id, username)
            )
            # Обновляем username если изменился
            await db.execute(
                "UPDATE users SET username = ? WHERE user_id = ?",
                (username, user_id)
            )
            await db.commit()

    async def get_limit(self) -> int:
        """Возвращает текущий лимит песен в плейлисте."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT value FROM settings WHERE key = 'max_songs'"
            ) as cursor:
                row = await cursor.fetchone()
                return int(row[0]) if row else 30

    async def set_limit(self, new_limit: int):
        """Устанавливает новый лимит песен."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE settings SET value = ? WHERE key = 'max_songs'",
                (str(new_limit),)
            )
            await db.commit()

    async def get_songs(self, user_id: int) -> list[dict]:
        """Возвращает список песен пользователя."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT id, title, added_at FROM songs WHERE user_id = ? ORDER BY added_at ASC",
                (user_id,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]

    async def add_song(self, user_id: int, title: str):
        """Добавляет песню в плейлист пользователя."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO songs (user_id, title) VALUES (?, ?)",
                (user_id, title)
            )
            await db.commit()

    async def delete_song(self, song_id: int, user_id: int):
        """Удаляет конкретную песню (с проверкой принадлежности)."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "DELETE FROM songs WHERE id = ? AND user_id = ?",
                (song_id, user_id)
            )
            await db.commit()

    async def clear_playlist(self, user_id: int):
        """Очищает весь плейлист пользователя."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "DELETE FROM songs WHERE user_id = ?",
                (user_id,)
            )
            await db.commit()

    async def get_all_playlists(self) -> list[dict]:
        """Возвращает все плейлисты всех пользователей (для админа)."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT user_id, username FROM users ORDER BY joined_at") as cur:
                users = await cur.fetchall()

            result = []
            for user in users:
                uid = user["user_id"]
                async with db.execute(
                    "SELECT id, title, added_at FROM songs WHERE user_id = ? ORDER BY added_at",
                    (uid,)
                ) as scur:
                    songs = await scur.fetchall()

                result.append({
                    "user_id": uid,
                    "username": user["username"],
                    "songs": [s["title"] for s in songs],
                    "songs_full": [
                        {"title": s["title"], "added_at": s["added_at"]}
                        for s in songs
                    ]
                })
            return result

    async def get_global_stats(self) -> dict:
        """Возвращает глобальную статистику для админа."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT COUNT(*) FROM users") as c:
                users_count = (await c.fetchone())[0]
            async with db.execute("SELECT COUNT(*) FROM songs") as c:
                songs_count = (await c.fetchone())[0]
        return {"users": users_count, "songs": songs_count}