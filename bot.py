#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Music Playlist Bot — bot.py

import asyncio
import logging
import io
import csv
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    Message, CallbackQuery,
    BufferedInputFile
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

from config import Config
from database import Database
from keyboards import Keyboards

# Логирование
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# FSM состояния
class UserStates(StatesGroup):
    waiting_for_song = State()       # Ожидание ввода названия песни
    waiting_delete_num = State()     # Ожидание номера песни для удаления
    admin_waiting_limit = State()    # Ожидание нового лимита от админа


# ─────────────────────────── HELPERS ───────────────────────────

def build_progress_bar(current: int, maximum: int, length: int = 20) -> str:
    """Строит текстовый прогресс-бар."""
    if maximum == 0:
        return "⬜" * length
    filled = int(length * current / maximum)
    empty = length - filled
    percent = int(100 * current / maximum)
    bar = "🥮" * filled + "⬜" * empty
    return f"{bar} {percent}%"


async def get_playlist_text(db: Database, user_id: int) -> str:
    """Формирует текст плейлиста пользователя."""
    songs = await db.get_songs(user_id)
    limit = await db.get_limit()
    count = len(songs)
    bar = build_progress_bar(count, limit)

    if not songs:
        songs_text = "  🎵 Плейлист пуст. Добавьте первую песню!"
    else:
        songs_text = ""
        for i, song in enumerate(songs, 1):
            songs_text += f"  {i}. 🎵 {song['title']}\n"

    text = (
        f"🎵 Ваш плейлист\n\n"
        f"{songs_text}\n"
        f"📊 Прогресс: {count}/{limit}\n"
        f"{bar}"
    )
    return text


# ─────────────────────────── HANDLERS ──────────────────────────

def register_handlers(dp: Dispatcher, db: Database):
    kb = Keyboards()

    # /start
    @dp.message(CommandStart())
    async def cmd_start(message: Message, state: FSMContext):
        await state.clear()
        user_id = message.from_user.id
        name = message.from_user.first_name or "друг"
        await db.ensure_user(user_id, message.from_user.username)
        limit = await db.get_limit()
        songs = await db.get_songs(user_id)
        count = len(songs)
        bar = build_progress_bar(count, limit)

        text = (
            f"🎵 Добро пожаловать, {name}!\n\n"
            f"Это GachiParty Music — твой помощник в повышении шансов на победу в Покер турнире!.\n\n"
            f"Добавь песни для поднятия моджо, и в нужный момент тузик дойдет 🂡.\n\n"
            f"📊 Твой плейлист: {count}/{limit} песен\n"
            f"{bar}\n\n"
            f"Используй кнопки ниже для управления плейлистом 👇"
        )
        await message.answer(text, reply_markup=kb.main_menu(), parse_mode="HTML")

    # /help
    @dp.message(Command("help"))
    async def cmd_help(message: Message):
        text = (
            "📖 Помощь по командам:\n\n"
            "➕ Добавить песню — добавить новую песню в плейлист\n"
            "📋 Мой плейлист — просмотр всех добавленных песен\n"
            "🗑 Удалить песню — удалить песню по номеру\n"
            "🗑🗑 Очистить плейлист — удалить все песни\n\n"
            "Команды:\n"
            "/start — главное меню\n"
            "/help — эта справка\n"
            "/playlist — просмотр плейлиста\n\n"
            "💡 Формат добавления:\n"
            "Исполнитель - Название\n"
            "Пример: Queen - Bohemian Rhapsody"
        )
        await message.answer(text, parse_mode="HTML")

    # /playlist
    @dp.message(Command("playlist"))
    async def cmd_playlist(message: Message, state: FSMContext):
        await state.clear()
        user_id = message.from_user.id
        await db.ensure_user(user_id, message.from_user.username)
        text = await get_playlist_text(db, user_id)
        await message.answer(text, reply_markup=kb.main_menu(), parse_mode="HTML")

    # ── Callback: Просмотр плейлиста ──
    @dp.callback_query(F.data == "view_playlist")
    async def cb_view_playlist(call: CallbackQuery, state: FSMContext):
        await state.clear()
        user_id = call.from_user.id
        await db.ensure_user(user_id, call.from_user.username)
        text = await get_playlist_text(db, user_id)
        await call.message.edit_text(text, reply_markup=kb.playlist_actions(), parse_mode="HTML")
        await call.answer()

    # ── Callback: Добавить песню ──
    @dp.callback_query(F.data == "add_song")
    async def cb_add_song(call: CallbackQuery, state: FSMContext):
        user_id = call.from_user.id
        songs = await db.get_songs(user_id)
        limit = await db.get_limit()

        if len(songs) >= limit:
            await call.answer(
                f"❌ Плейлист заполнен! Максимум {limit} песен.", show_alert=True
            )
            return

        await state.set_state(UserStates.waiting_for_song)
        remaining = limit - len(songs)
        await call.message.edit_text(
            f"🎵 Добавление песни\n\n"
            f"Введите название песни и исполнителя:\n\n"
            f"💡 Пример: Queen - Bohemian Rhapsody\n\n"
            f"📊 Осталось мест: {remaining}/{limit}",
            reply_markup=kb.cancel_button(),
            parse_mode="HTML"
        )
        await call.answer()

    # ── Получение текста песни ──
    @dp.message(UserStates.waiting_for_song)
    async def process_song_input(message: Message, state: FSMContext):
        user_id = message.from_user.id
        title = message.text.strip()

        if not title:
            await message.answer("⚠️ Название не может быть пустым. Введите название песни:")
            return

        if len(title) > 200:
            await message.answer("⚠️ Слишком длинное название (макс. 200 символов). Попробуйте ещё раз:")
            return

        songs = await db.get_songs(user_id)
        limit = await db.get_limit()

        if len(songs) >= limit:
            await state.clear()
            await message.answer(
                f"❌ Плейлист уже заполнен ({limit} песен)!\nУдалите песню, чтобы добавить новую.",
                reply_markup=kb.main_menu()
            )
            return

        # Проверка дублей
        existing_titles = [s['title'].lower() for s in songs]
        if title.lower() in existing_titles:
            await message.answer(
                f"⚠️ Песня {title} уже есть в вашем плейлисте!\nВведите другое название:",
                parse_mode="HTML"
            )
            return

        await db.add_song(user_id, title)
        await state.clear()

        songs_new = await db.get_songs(user_id)
        count = len(songs_new)
        bar = build_progress_bar(count, limit)

        await message.answer(
            f"✅ Добавлено: {title}\n\n"
            f"📊 Плейлист: {count}/{limit}\n"
            f"{bar}",
            reply_markup=kb.main_menu(),
            parse_mode="HTML"
        )

    # ── Callback: Удалить песню ──
    @dp.callback_query(F.data == "delete_song")
    async def cb_delete_song(call: CallbackQuery, state: FSMContext):
        user_id = call.from_user.id
        songs = await db.get_songs(user_id)

        if not songs:
            await call.answer("❌ Плейлист уже пуст!", show_alert=True)
            return

        songs_list = ""
        for i, s in enumerate(songs, 1):
            songs_list += f"{i}. {s['title']}\n"

        await state.set_state(UserStates.waiting_delete_num)
        await call.message.edit_text(
            f"🗑 Удаление песни\n\n"
            f"Ваш плейлист:\n{songs_list}\n"
            f"Введите номер песни для удаления (1–{len(songs)}):",
            reply_markup=kb.cancel_button(),
            parse_mode="HTML"
        )
        await call.answer()

    # ── Получение номера для удаления ──
    @dp.message(UserStates.waiting_delete_num)
    async def process_delete_num(message: Message, state: FSMContext):
        user_id = message.from_user.id
        songs = await db.get_songs(user_id)

        try:
            num = int(message.text.strip())
            if not (1 <= num <= len(songs)):
                raise ValueError
        except ValueError:
            await message.answer(
                f"⚠️ Введите число от 1 до {len(songs)}:"
            )
            return

        song = songs[num - 1]
        await db.delete_song(song['id'], user_id)
        await state.clear()

        limit = await db.get_limit()
        songs_new = await db.get_songs(user_id)
        bar = build_progress_bar(len(songs_new), limit)

        await message.answer(
            f"✅ Удалено: {song['title']}\n\n"
            f"📊 Плейлист: {len(songs_new)}/{limit}\n"
            f"{bar}",
            reply_markup=kb.main_menu(),
            parse_mode="HTML"
        )

    # ── Callback: Очистить весь плейлист ──
    @dp.callback_query(F.data == "clear_playlist")
    async def cb_clear_playlist(call: CallbackQuery):
        await call.message.edit_text(
            "⚠️ Вы уверены?\nЭто удалит ВСЕ песни из вашего плейлиста!",
            reply_markup=kb.confirm_clear(),
            parse_mode="HTML"
        )
        await call.answer()

    @dp.callback_query(F.data == "confirm_clear")
    async def cb_confirm_clear(call: CallbackQuery):
        user_id = call.from_user.id
        await db.clear_playlist(user_id)
        limit = await db.get_limit()
        bar = build_progress_bar(0, limit)
        await call.message.edit_text(
            f"🗑 Плейлист очищен.\n\n📊 0/{limit}\n{bar}",
            reply_markup=kb.main_menu(),
            parse_mode="HTML"
        )
        await call.answer("✅ Плейлист очищен")

    # ── Callback: Назад в меню ──
    @dp.callback_query(F.data == "back_to_menu")
    async def cb_back_menu(call: CallbackQuery, state: FSMContext):
        await state.clear()
        user_id = call.from_user.id
        name = call.from_user.first_name or "друг"
        songs = await db.get_songs(user_id)
        limit = await db.get_limit()
        bar = build_progress_bar(len(songs), limit)
        text = (
            f"🎵 Главное меню, {name}!\n\n"
            f"📊 Плейлист: {len(songs)}/{limit}\n"
            f"{bar}"
        )
        await call.message.edit_text(text, reply_markup=kb.main_menu(), parse_mode="HTML")
        await call.answer()

    # ── Callback: Отмена ──
    @dp.callback_query(F.data == "cancel")
    async def cb_cancel(call: CallbackQuery, state: FSMContext):
        await state.clear()
        user_id = call.from_user.id
        songs = await db.get_songs(user_id)
        limit = await db.get_limit()
        bar = build_progress_bar(len(songs), limit)
        await call.message.edit_text(
            f"❌ Отменено.\n\n📊 Плейлист: {len(songs)}/{limit}\n{bar}",
            reply_markup=kb.main_menu(),
            parse_mode="HTML"
        )
        await call.answer()

    # ═══════════════ ADMIN HANDLERS ════════════════

    def is_admin(user_id: int) -> bool:
        return user_id in Config.ADMIN_IDS

    # /admin
    @dp.message(Command("admin"))
    async def cmd_admin(message: Message, state: FSMContext):
        if not is_admin(message.from_user.id):
            await message.answer("🚫 Нет доступа.")
            return
        await state.clear()
        limit = await db.get_limit()
        stats = await db.get_global_stats()
        text = (
            "🔐 Панель администратора\n\n"
            f"👥 Пользователей: {stats['users']}\n"
            f"🎵 Всего песен: {stats['songs']}\n"
            f"📊 Лимит плейлиста: {limit}\n\n"
            "Выберите действие:"
        )
        await message.answer(text, reply_markup=kb.admin_menu(), parse_mode="HTML")

    # ── Admin: все плейлисты ──
    @dp.callback_query(F.data == "admin_view_all")
    async def admin_view_all(call: CallbackQuery):
        if not is_admin(call.from_user.id):
            await call.answer("🚫 Нет доступа")
            return
        all_data = await db.get_all_playlists()
        limit = await db.get_limit()

        if not all_data:
            await call.answer("📭 Плейлистов нет", show_alert=True)
            return

        text = "📋 Все плейлисты:\n\n"
        for user_data in all_data:
            uname = user_data['username'] or f"id:{user_data['user_id']}"
            songs = user_data['songs']
            bar = build_progress_bar(len(songs), limit, 10)
            text += f"👤 @{uname} ({len(songs)}/{limit}) {bar}\n"
            for i, s in enumerate(songs, 1):
                text += f"  {i}. {s}\n"
            text += "\n"

        if len(text) > 4000:
            text = text[:4000] + "\n... (список слишком длинный, используйте экспорт)"

        await call.message.edit_text(text, reply_markup=kb.admin_back(), parse_mode="HTML")
        await call.answer()

    # ── Admin: экспорт CSV ──
    @dp.callback_query(F.data == "admin_export")
    async def admin_export(call: CallbackQuery):
        if not is_admin(call.from_user.id):
            await call.answer("🚫 Нет доступа")
            return
        await call.answer("📤 Генерирую CSV...")

        all_data = await db.get_all_playlists()
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["user_id", "username", "song_number", "song_title", "added_at"])

        for user_data in all_data:
            for i, song in enumerate(user_data['songs_full'], 1):
                writer.writerow([
                    user_data['user_id'],
                    user_data['username'] or "",
                    i,
                    song['title'],
                    song['added_at']
                ])

        csv_bytes = output.getvalue().encode("utf-8-sig")
        filename = f"playlists_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        await call.message.answer_document(
            BufferedInputFile(csv_bytes, filename=filename),
            caption=f"📊 Экспорт плейлистов от {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        )

    # ── Admin: изменить лимит ──
    @dp.callback_query(F.data == "admin_set_limit")
    async def admin_set_limit(call: CallbackQuery, state: FSMContext):
        if not is_admin(call.from_user.id):
            await call.answer("🚫 Нет доступа")
            return
        limit = await db.get_limit()
        await state.set_state(UserStates.admin_waiting_limit)
        await call.message.edit_text(
            f"⚙️ Изменение лимита\n\nТекущий лимит: {limit} песен\n\nВведите новое значение (1–200):",
            reply_markup=kb.cancel_button(),
            parse_mode="HTML"
        )
        await call.answer()

    @dp.message(UserStates.admin_waiting_limit)
    async def process_admin_limit(message: Message, state: FSMContext):
        if not is_admin(message.from_user.id):
            return
        try:
            new_limit = int(message.text.strip())
            if not (1 <= new_limit <= 200):
                raise ValueError
        except ValueError:
            await message.answer("⚠️ Введите число от 1 до 200:")
            return

        await db.set_limit(new_limit)
        await state.clear()
        await message.answer(
            f"✅ Лимит изменён на {new_limit} песен!",
            reply_markup=kb.admin_menu(),
            parse_mode="HTML"
        )

    # ── Admin: статистика ──
    @dp.callback_query(F.data == "admin_stats")
    async def admin_stats(call: CallbackQuery):
        if not is_admin(call.from_user.id):
            await call.answer("🚫 Нет доступа")
            return
        stats = await db.get_global_stats()
        limit = await db.get_limit()
        text = (
            "📈 Статистика бота\n\n"
            f"👥 Всего пользователей: {stats['users']}\n"
            f"🎵 Всего песен в базе: {stats['songs']}\n"
            f"📊 Текущий лимит: {limit} песен\n"
            f"📅 Дата генерации: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        )
        await call.message.edit_text(text, reply_markup=kb.admin_back(), parse_mode="HTML")
        await call.answer()

    @dp.callback_query(F.data == "admin_back")
    async def admin_back(call: CallbackQuery, state: FSMContext):
        await state.clear()
        limit = await db.get_limit()
        stats = await db.get_global_stats()
        text = (
            "🔐 Панель администратора\n\n"
            f"👥 Пользователей: {stats['users']}\n"
            f"🎵 Всего песен: {stats['songs']}\n"
            f"📊 Лимит: {limit}\n\n"
            "Выберите действие:"
        )
        await call.message.edit_text(text, reply_markup=kb.admin_menu(), parse_mode="HTML")
        await call.answer()


# ────────────────────── MAIN ──────────────────────────

async def main():
    db = Database("data/playlist.db")
    await db.init()

    bot = Bot(token=Config.BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    register_handlers(dp, db)

    logger.info("🎵 Music Playlist Bot запускается...")
    await dp.start_polling(bot, skip_updates=True)


if __name__ == "__main__":
    asyncio.run(main())