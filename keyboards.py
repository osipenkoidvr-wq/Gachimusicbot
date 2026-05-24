#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Music Playlist Bot — keyboards.py

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


class Keyboards:

    def main_menu(self) -> InlineKeyboardMarkup:
        """Главное меню пользователя."""
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="➕ Добавить песню", callback_data="add_song"),
            InlineKeyboardButton(text="📋 Мой плейлист", callback_data="view_playlist")
        )
        builder.row(
            InlineKeyboardButton(text="🗑 Удалить песню", callback_data="delete_song"),
            InlineKeyboardButton(text="🗑🗑 Очистить всё", callback_data="clear_playlist")
        )
        return builder.as_markup()

    def playlist_actions(self) -> InlineKeyboardMarkup:
        """Меню действий при просмотре плейлиста."""
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="➕ Добавить", callback_data="add_song"),
            InlineKeyboardButton(text="🗑 Удалить", callback_data="delete_song")
        )
        builder.row(
            InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_menu")
        )
        return builder.as_markup()

    def cancel_button(self) -> InlineKeyboardMarkup:
        """Кнопка отмены."""
        builder = InlineKeyboardBuilder()
        builder.button(text="❌ Отмена", callback_data="cancel")
        return builder.as_markup()

    def confirm_clear(self) -> InlineKeyboardMarkup:
        """Подтверждение очистки плейлиста."""
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="✅ Да, удалить всё", callback_data="confirm_clear"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="back_to_menu")
        )
        return builder.as_markup()

    def admin_menu(self) -> InlineKeyboardMarkup:
        """Меню администратора."""
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="📋 Все плейлисты", callback_data="admin_view_all"),
            InlineKeyboardButton(text="📈 Статистика", callback_data="admin_stats")
        )
        builder.row(
            InlineKeyboardButton(text="📤 Экспорт CSV", callback_data="admin_export"),
            InlineKeyboardButton(text="⚙️ Изменить лимит", callback_data="admin_set_limit")
        )
        return builder.as_markup()

    def admin_back(self) -> InlineKeyboardMarkup:
        """Кнопка назад для админ-панели."""
        builder = InlineKeyboardBuilder()
        builder.button(text="⬅️ Назад в панель", callback_data="admin_back")
        return builder.as_markup()