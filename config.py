#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Music Playlist Bot — config.py

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Telegram Bot Token (обязательно)
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")

    # ID администраторов (через запятую, например: "123456789,987654321")
    _admin_ids_raw: str = os.getenv("ADMIN_IDS", "")
    ADMIN_IDS: list[int] = [
        int(x.strip())
        for x in _admin_ids_raw.split(",")
        if x.strip().isdigit()
    ]

    if not BOT_TOKEN:
        raise ValueError("❌ BOT_TOKEN не задан в .env!")

    if not ADMIN_IDS:
        raise ValueError("❌ ADMIN_IDS не задан в .env!")