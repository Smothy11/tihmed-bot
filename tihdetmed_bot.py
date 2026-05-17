# -*- coding: utf-8 -*-

from vkbottle.bot import Bot, Message
from vkbottle import Keyboard, KeyboardButtonColor, Text
import logging
import sqlite3
from datetime import datetime, timedelta
import locale

# --- ПРИНУДИТЕЛЬНАЯ УСТАНОВКА РУССКОЙ ЛОКАЛИ ---
try:
    locale.setlocale(locale.LC_ALL, 'ru_RU.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_ALL, 'Russian_Russia.1251')
    except:
        logging.warning("Не удалось установить русскую локаль, используем ручное преобразование")

# --- НАСТРОЙКИ ---
ADMIN_ID = 496292338
TOKEN = "vk1.a.EqaeP08Qq7AXX-An1o6UaMThR0_Rixz_ycXzJ9rRw28BHuWjTJJa_wxaOBZGRlazgcFbKw81J_FgiH5PW1Q_QmkG5De9HwUvVLBIG5Mj7veX-TpH57C_k-l2BaE1ebCbixF-iqYtg1A3-Pqcedorz0_RACtEshxdE1OZ13UD519OnwwBRiRRu_osswqhPcDqKQTUmgIbB0c0SBOeuWL-nQ"

bot = Bot(token=TOKEN)
logging.basicConfig(level=logging.INFO)

user_states = {}

# --- СЛОВАРЬ ДЛЯ РУЧНОГО ПРЕОБРАЗОВАНИЯ МЕСЯЦЕВ (ЕСЛИ ЛОКАЛЬ НЕ РАБОТАЕТ) ---
MONTHS_RU = {
    'January': 'января', 'February': 'февраля', 'March': 'марта',
    'April': 'апреля', 'May': 'мая', 'June': 'июня',
    'July': 'июля', 'August': 'августа', 'September': 'сентября',
    'October': 'октября', 'November': 'ноября', 'December': 'декабря'
}


def format_date_russian(date_obj):
    """Форматирует дату на русском языке"""
    day = date_obj.day
    month_eng = date_obj.strftime('%B')
    month_ru = MONTHS_RU.get(month_eng, month_eng)
    return f"{day} {month_ru}"


def format_date_for_db(date_obj):
    """Форматирует дату для хранения в БД (число месяц)"""
    day = date_obj.day
    month_eng = date_obj.strftime('%B')
    month_ru = MONTHS_RU.get(month_eng, month_eng)
    return f"{day} {month_ru}"


# --- БАЗА ДАННЫХ ---
def init_db():
    conn = sqlite3.connect('appointments.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS available_slots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doctor TEXT,
            slot_date TEXT,
            slot_time TEXT,
            is_available INTEGER DEFAULT 1
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            user_name TEXT,
            doctor TEXT,
            appointment_date TEXT,
            appointment_time TEXT,
            created_at TEXT
        )
    ''')
    conn.commit()
    conn.close()


def get_available_slots(doctor_name):
    """Получает слоты только на ближайшие 14 дней"""
    conn = sqlite3.connect('appointments.db')
    cursor = conn.cursor()

    # Вычисляем даты для фильтрации (сегодня и следующие 14 дней)
    today = datetime.now().date()

    dates_range = []
    for i in range(15):
        date_str = format_date_for_db(today + timedelta(days=i))
        dates_range.append(date_str)

    # Создаем плейсхолдеры для SQL
    placeholders = ','.join('?' * len(dates_range))

    cursor.execute(f'''
        SELECT slot_date, slot_time FROM available_slots 
        WHERE doctor = ? AND is_available = 1 AND slot_date IN ({placeholders})
        ORDER BY slot_date, slot_time
    ''', (doctor_name, *dates_range))

    result = cursor.fetchall()
    conn.close()
    logging.info(f"Найдено слотов для {doctor_name} (ближайшие 14 дней): {len(result)}")
    return result


def book_slot(doctor_name, date, time, user_id, user_name):
    conn = sqlite3.connect('appointments.db')
    cursor = conn.cursor()
    try:
        cursor.execute('BEGIN')
        cursor.execute('''
            UPDATE available_slots SET is_available = 0 
            WHERE doctor = ? AND slot_date = ? AND slot_time = ? AND is_available = 1
        ''', (doctor_name, date, time))

        if cursor.rowcount == 0:
            conn.rollback()
            logging.warning(f"Слот уже занят: {doctor_name} {date} {time}")
            return False

        cursor.execute('''
            INSERT INTO appointments (user_id, user_name, doctor, appointment_date, appointment_time, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, user_name, doctor_name, date, time, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        conn.commit()
        logging.info(f"Запись создана: {user_name} -> {doctor_name} {date} {time}")
        return True
    except Exception as e:
        conn.rollback()
        logging.error(f"Ошибка бронирования: {e}")
        return False
    finally:
        conn.close()


def get_user_appointments(user_id):
    conn = sqlite3.connect('appointments.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM appointments WHERE user_id = ? ORDER BY created_at DESC', (user_id,))
    result = cursor.fetchall()
    conn.close()
    return result


def cancel_appointment(user_id, appointment_id):
    conn = sqlite3.connect('appointments.db')
    cursor = conn.cursor()
    try:
        cursor.execute(
            'SELECT doctor, appointment_date, appointment_time FROM appointments WHERE id = ? AND user_id = ?',
            (appointment_id, user_id))
        app = cursor.fetchone()
        if not app:
            return False, None

        doctor, date, time = app
        cursor.execute('DELETE FROM appointments WHERE id = ? AND user_id = ?', (appointment_id, user_id))
        cursor.execute('''
            UPDATE available_slots SET is_available = 1 
            WHERE doctor = ? AND slot_date = ? AND slot_time = ?
        ''', (doctor, date, time))
        conn.commit()
        return True, (doctor, date, time)
    except Exception as e:
        conn.rollback()
        logging.error(f"Ошибка отмены: {e}")
        return False, None
    finally:
        conn.close()


def add_new_slot(doctor, date, time):
    conn = sqlite3.connect('appointments.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR IGNORE INTO available_slots (doctor, slot_date, slot_time, is_available)
        VALUES (?, ?, ?, 1)
    ''', (doctor, date, time))
    conn.commit()
    success = cursor.rowcount > 0
    conn.close()
    return success


def seed_available_slots():
    """Заполняет базу слотами на 30 дней вперед (с русскими датами)"""
    logging.info("Заполнение базы слотов...")
    doctors_list = ["Педиатр", "Невролог", "ЛОР", "Окулист", "Стоматолог"]
    times_list = ["09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00"]

    for i in range(30):
        current_date = datetime.now().date() + timedelta(days=i)
        date_str = format_date_for_db(current_date)  # Используем русский формат

        for doctor in doctors_list:
            for time in times_list:
                add_new_slot(doctor, date_str, time)

    logging.info("База слотов заполнена русскими датами!")


def check_db_empty():
    conn = sqlite3.connect('appointments.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM available_slots')
    count = cursor.fetchone()[0]
    conn.close()
    return count == 0


# --- КЛАВИАТУРЫ ---

def get_main_keyboard(is_admin=False):
    keyboard = Keyboard(one_time=False, inline=False)
    if is_admin:
        keyboard.add(Text("📊 Статистика"), color=KeyboardButtonColor.PRIMARY)
        keyboard.add(Text("➕ Добавить слот"), color=KeyboardButtonColor.POSITIVE)
        keyboard.row()
        keyboard.add(Text("🔙 Главное меню"), color=KeyboardButtonColor.SECONDARY)
    else:
        keyboard.add(Text("📝 Записаться к врачу"), color=KeyboardButtonColor.POSITIVE)
        keyboard.row()
        keyboard.add(Text("📋 Мои записи"), color=KeyboardButtonColor.PRIMARY)
        keyboard.add(Text("❌ Отменить запись"), color=KeyboardButtonColor.NEGATIVE)
        keyboard.row()
        keyboard.add(Text("❓ Помощь"), color=KeyboardButtonColor.SECONDARY)
    return keyboard


def get_doctors_keyboard():
    keyboard = Keyboard(one_time=False, inline=False)
    keyboard.add(Text("👶 Педиатр"), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("🧠 Невролог"), color=KeyboardButtonColor.PRIMARY)
    keyboard.row()
    keyboard.add(Text("👂 ЛОР"), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("👁️ Окулист"), color=KeyboardButtonColor.PRIMARY)
    keyboard.row()
    keyboard.add(Text("🦷 Стоматолог"), color=KeyboardButtonColor.PRIMARY)
    keyboard.row()
    keyboard.add(Text("🔙 На главную"), color=KeyboardButtonColor.SECONDARY)
    return keyboard


def get_dates_keyboard(dates):
    """
    Клавиатура с датами.
    Ограничение: максимум 10 рядов, 4 кнопки в ряду.
    """
    keyboard = Keyboard(one_time=False, inline=False)

    # Ограничиваем количество дат (максимум 20 = 5 рядов по 4 кнопки)
    max_dates = min(len(dates), 20)
    limited_dates = dates[:max_dates]

    for i in range(0, len(limited_dates), 4):
        row_dates = limited_dates[i:i + 4]
        for date in row_dates:
            keyboard.add(Text(f"📅 {date}"), color=KeyboardButtonColor.PRIMARY)
        keyboard.row()

    keyboard.add(Text("🔙 На главную"), color=KeyboardButtonColor.SECONDARY)
    return keyboard


def get_times_keyboard(times):
    """
    Клавиатура с временем.
    Ограничение: максимум 10 рядов, 4 кнопки в ряду.
    """
    keyboard = Keyboard(one_time=False, inline=False)

    # Ограничиваем количество времени (максимум 16 = 4 ряда по 4 кнопки)
    max_times = min(len(times), 16)
    limited_times = times[:max_times]

    for i in range(0, len(limited_times), 4):
        row_times = limited_times[i:i + 4]
        for t in row_times:
            keyboard.add(Text(f"⏰ {t[0]}"), color=KeyboardButtonColor.POSITIVE)
        keyboard.row()

    keyboard.add(Text("🔙 На главную"), color=KeyboardButtonColor.SECONDARY)
    return keyboard


def get_admin_keyboard():
    keyboard = Keyboard(one_time=False, inline=False)
    keyboard.add(Text("📊 Статистика"), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("➕ Добавить слот"), color=KeyboardButtonColor.POSITIVE)
    keyboard.row()
    keyboard.add(Text("🔙 Главное меню"), color=KeyboardButtonColor.SECONDARY)
    return keyboard


# --- ОСНОВНОЙ ОБРАБОТЧИК ---

@bot.on.private_message()
async def handle_all(message: Message):
    text = message.text.strip()
    user_id = message.from_id

    users = await bot.api.users.get(user_ids=user_id)
    user_name = users[0].first_name

    logging.info(f"Сообщение от {user_id}: {text}")

    # --- АДМИН-РЕЖИМ ---
    if user_id == ADMIN_ID:

        if user_states.get(user_id, {}).get("awaiting_slot"):
            parts = text.split(maxsplit=3)
            if len(parts) >= 4:
                doctor = parts[0]
                date = f"{parts[1]} {parts[2]}"
                time = parts[3]
                if add_new_slot(doctor, date, time):
                    await message.answer(
                        f"✅ Слот добавлен: {doctor} | {date} {time}",
                        keyboard=get_admin_keyboard()
                    )
                else:
                    await message.answer(
                        f"❌ Слот уже существует",
                        keyboard=get_admin_keyboard()
                    )
            else:
                await message.answer(
                    "❌ Неверный формат. Пример: `Педиатр 25 декабря 11:30`",
                    keyboard=get_admin_keyboard()
                )
            user_states.pop(user_id, None)
            return

        if text == "📊 Статистика":
            conn = sqlite3.connect('appointments.db')
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM appointments')
            total = cursor.fetchone()[0]
            cursor.execute('SELECT COUNT(*) FROM available_slots WHERE is_available = 1')
            free = cursor.fetchone()[0]
            cursor.execute('SELECT COUNT(*) FROM available_slots')
            all_slots = cursor.fetchone()[0]
            conn.close()
            await message.answer(
                f"📊 **Статистика**\n\n"
                f"✅ Всего записей: {total}\n"
                f"🟢 Свободных слотов: {free}\n"
                f"📋 Всего слотов в БД: {all_slots}",
                keyboard=get_admin_keyboard()
            )
            return

        if text == "➕ Добавить слот":
            await message.answer(
                "ℹ️ Введите данные нового слота в формате:\n\n"
                "`Врач Дата Время`\n\n"
                "Пример: `Педиатр 25 декабря 11:30`\n\n"
                "Доступные врачи: Педиатр, Невролог, ЛОР, Окулист, Стоматолог",
                keyboard=get_admin_keyboard()
            )
            user_states[user_id] = {"awaiting_slot": True}
            return

    # --- ОБЩИЕ КОМАНДЫ ---

    if text in ["/start", "начать", "привет", "старт", "Начать", "Старт", "🔙 Главное меню"]:
        if user_id == ADMIN_ID:
            await message.answer(
                f"👋 Здравствуйте, {user_name} (Администратор)!\n\nВыберите действие:",
                keyboard=get_admin_keyboard()
            )
        else:
            await message.answer(
                f"👋 Привет, {user_name}!\n\n🤖 Я помогу записать ребёнка к врачу в Тихорецке.\n\nВыберите действие:",
                keyboard=get_main_keyboard()
            )
        user_states.pop(user_id, None)
        return

    if text == "🔙 На главную":
        if user_id == ADMIN_ID:
            await message.answer("🏠 Главное меню:", keyboard=get_admin_keyboard())
        else:
            await message.answer("🏠 Главное меню:", keyboard=get_main_keyboard())
        user_states.pop(user_id, None)
        return

    if text == "❓ Помощь":
        await message.answer(
            "🆘 **Помощь по боту**\n\n"
            "📝 **Записаться:**\n"
            "   Нажмите 'Записаться' → выберите врача → дату → время\n\n"
            "📋 **Мои записи:**\n"
            "   Показывает все ваши записи с ID\n\n"
            "❌ **Отменить запись:**\n"
            "   Нажмите 'Отменить запись' → введите ID записи\n\n"
            "📍 Бот работает 24/7",
            keyboard=get_main_keyboard()
        )
        return

    if text == "📝 Записаться к врачу":
        await message.answer("🩺 Выберите специалиста:", keyboard=get_doctors_keyboard())
        return

    # Выбор врача
    if text in ["👶 Педиатр", "🧠 Невролог", "👂 ЛОР", "👁️ Окулист", "🦷 Стоматолог"]:
        doctor_name = text.split()[-1]
        user_states[user_id] = {"step": "doctor", "doctor": doctor_name}

        slots = get_available_slots(doctor_name)
        if not slots:
            await message.answer(
                f"❌ Свободных слотов для {doctor_name} на ближайшие 14 дней нет.\n\n"
                f"Попробуйте позже или обратитесь к администратору.",
                keyboard=get_main_keyboard()
            )
            return

        dates = sorted(set(s[0] for s in slots))
        await message.answer(
            f"📅 Выберите дату для записи к **{doctor_name}** (доступно {len(dates)} дат):",
            keyboard=get_dates_keyboard(dates)
        )
        return

    # Выбор даты
    if text.startswith("📅 ") and user_states.get(user_id, {}).get("step") == "doctor":
        date = text.replace("📅 ", "").strip()
        doctor = user_states[user_id]["doctor"]

        conn = sqlite3.connect('appointments.db')
        cursor = conn.cursor()
        cursor.execute('''
            SELECT slot_time FROM available_slots 
            WHERE doctor = ? AND slot_date = ? AND is_available = 1
            ORDER BY slot_time
        ''', (doctor, date))
        times = cursor.fetchall()
        conn.close()

        if not times:
            await message.answer(
                f"❌ На {date} нет свободных слотов у {doctor}.\nВыберите другую дату.",
                keyboard=get_main_keyboard()
            )
            user_states.pop(user_id, None)
            return

        user_states[user_id]["step"] = "time"
        user_states[user_id]["date"] = date

        await message.answer(
            f"⏰ Выберите время для **{doctor}** на **{date}**:",
            keyboard=get_times_keyboard(times)
        )
        return

    # Выбор времени (подтверждение записи)
    if text.startswith("⏰ ") and user_states.get(user_id, {}).get("step") == "time":
        time = text.replace("⏰ ", "").strip()
        doctor = user_states[user_id]["doctor"]
        date = user_states[user_id]["date"]

        success = book_slot(doctor, date, time, user_id, user_name)

        if success:
            await message.answer(
                f"✅ **Запись успешно оформлена!**\n\n"
                f"🩺 Врач: {doctor}\n"
                f"📅 Дата: {date}\n"
                f"⏰ Время: {time}\n\n"
                f"Приходите вовремя! 🏥",
                keyboard=get_main_keyboard()
            )
        else:
            await message.answer(
                f"❌ Извините, слот **{doctor} | {date} {time}** уже занят.\nПопробуйте выбрать другое время.",
                keyboard=get_main_keyboard()
            )
        user_states.pop(user_id, None)
        return

    # Мои записи
    if text == "📋 Мои записи":
        apps = get_user_appointments(user_id)
        if not apps:
            await message.answer(
                "📋 У вас пока нет активных записей.\n\nНажмите 'Записаться к врачу', чтобы создать запись.",
                keyboard=get_main_keyboard()
            )
        else:
            lines = ["📋 **Ваши активные записи:**\n"]
            for app in apps:
                lines.append(f"🔹 **ID {app[0]}** | {app[2]} | {app[3]} в {app[4]}")
            lines.append("\n❌ Чтобы отменить запись — нажмите 'Отменить запись' и введите ID")
            await message.answer("\n".join(lines), keyboard=get_main_keyboard())
        return

    # Отменить запись
    if text == "❌ Отменить запись":
        apps = get_user_appointments(user_id)
        if not apps:
            await message.answer(
                "❌ У вас нет записей для отмены.",
                keyboard=get_main_keyboard()
            )
        else:
            lines = ["❌ **Отмена записи**\n\nВаши записи:"]
            for app in apps:
                lines.append(f"• ID {app[0]}: {app[2]} | {app[3]} в {app[4]}")
            lines.append("\n✏️ **Введите ID записи, которую хотите отменить** (например: 5)")
            await message.answer("\n".join(lines), keyboard=get_main_keyboard())
            user_states[user_id] = {"step": "cancel"}
        return

    # Обработка ввода ID для отмены
    if user_states.get(user_id, {}).get("step") == "cancel" and text.isdigit():
        app_id = int(text)
        success, info = cancel_appointment(user_id, app_id)
        if success:
            doctor, date, time = info
            await message.answer(
                f"✅ Запись к **{doctor}** на **{date} в {time}** успешно отменена.\n\nСлот снова доступен для записи.",
                keyboard=get_main_keyboard()
            )
        else:
            await message.answer(
                "❌ Не удалось отменить запись. Проверьте правильность ID.",
                keyboard=get_main_keyboard()
            )
        user_states.pop(user_id, None)
        return

    # Если ничего не подошло
    if user_id != ADMIN_ID:
        await message.answer(
            "🤔 **Я не понял команду**\n\n"
            "Пожалуйста, используйте кнопки под полем ввода:\n\n"
            "• 📝 Записаться к врачу\n"
            "• 📋 Мои записи\n"
            "• ❌ Отменить запись\n"
            "• ❓ Помощь",
            keyboard=get_main_keyboard()
        )


# --- ЗАПУСК ---
if __name__ == "__main__":
    init_db()

    if check_db_empty():
        print("📦 База данных пуста. Заполняем слотами...")
        seed_available_slots()
        print("✅ База заполнена русскими датами!")

        # Выводим пример дат для проверки
        conn = sqlite3.connect('appointments.db')
        cursor = conn.cursor()
        cursor.execute('SELECT DISTINCT slot_date FROM available_slots LIMIT 5')
        sample_dates = cursor.fetchall()
        conn.close()
        print(f"📅 Пример дат в БД: {[d[0] for d in sample_dates]}")
    else:
        print("📋 База данных уже содержит слоты.")

    print("✅ Бот успешно запущен!")
    print(f"📱 Ссылка: https://vk.com/club236802713")
    print(f"👑 Админ ID: {ADMIN_ID}")
    bot.run_forever()