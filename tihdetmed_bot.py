from vkbottle.bot import Bot, Message
from vkbottle import Keyboard, KeyboardButtonColor, Text
import logging
import sqlite3
from datetime import datetime, timedelta
from flask import Flask, request
import json

# app = Flask(__name__)
#
# @app.route('/', methods=['POST'])
# def webhook():
#     data = request.json
#     if data['type'] == 'confirmation':
#         return 'ваш_код_подтверждения'
#     elif data['type'] == 'message_new':
#         # Обработка сообщения
#         return 'ok'
#     return 'ok'
#
# if __name__ == '__main__':
#     app.run(host='0.0.0.0', port=5000)
# # Настройка логирования
# logging.basicConfig(level=logging.INFO)

# Токен твоей группы
bot = Bot(
    token="vk1.a.EqaeP08Qq7AXX-An1o6UaMThR0_Rixz_ycXzJ9rRw28BHuWjTJJa_wxaOBZGRlazgcFbKw81J_FgiH5PW1Q_QmkG5De9HwUvVLBIG5Mj7veX-TpH57C_k-l2BaE1ebCbixF-iqYtg1A3-Pqcedorz0_RACtEshxdE1OZ13UD519OnwwBRiRRu_osswqhPcDqKQTUmgIbB0c0SBOeuWL-nQ")  # Вставь свой токен


# Создаем базу данных для записей
def init_db():
    conn = sqlite3.connect('appointments.db')
    cursor = conn.cursor()
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


init_db()

# Главное меню
main_keyboard = Keyboard()
main_keyboard.add(Text("📝 Проверить доступные записи"), color=KeyboardButtonColor.POSITIVE)
main_keyboard.row()
main_keyboard.add(Text("📋 Мои записи"), color=KeyboardButtonColor.PRIMARY)
main_keyboard.add(Text("❓ Помощь"), color=KeyboardButtonColor.SECONDARY)

# Клавиатура с врачами
doctors_keyboard = Keyboard()
doctors_keyboard.add(Text("👶 Педиатр"))
doctors_keyboard.add(Text("🧠 Невролог"))
doctors_keyboard.row()
doctors_keyboard.add(Text("👂 ЛОР"))
doctors_keyboard.add(Text("👁️ Окулист"))
doctors_keyboard.row()
doctors_keyboard.add(Text("🦷 Стоматолог"))
doctors_keyboard.add(Text("🔙 Назад"))

# Клавиатура с адресами
address_keyboard = Keyboard()
address_keyboard.add(Text("🏥 Московская ул., 225"))
address_keyboard.add(Text("🏥 ул. Ударников, 12А"))

# Клавиатура для возврата в главное меню
back_keyboard = Keyboard()
back_keyboard.add(Text("🔙 В главное меню"))


# Обработчик команды "начать"
@bot.on.private_message(text=["/start", "начать", "привет", "старт"])
async def start_handler(message: Message):
    user_name = message.sender.first_name
    await message.answer(
        f"👋 Привет, {user_name}!\n\n"
        "Я бот для проверки доступных записей к детскому врачу в Тихорецке.\n"
        "Выберите действие:",
        keyboard=main_keyboard
    )


# Обработчик записи к врачу
@bot.on.private_message(text="📝 Проверить доступные записи")
async def book_handler(message: Message):
    await message.answer(
        "Выберите специалиста:",
        keyboard=doctors_keyboard
    )


# Обработчик выбора врача
@bot.on.private_message(text=["👶 Педиатр", "🧠 Невролог", "👂 ЛОР", "👁️ Окулист", "🦷 Стоматолог"])
async def doctor_handler(message: Message):
    doctor_name = message.text

    # Завтрашняя дата для примера
    tomorrow = datetime.now() + timedelta(days=1)
    next_day = datetime.now() + timedelta(days=2)

    await message.answer(
        f"Вы выбрали {doctor_name}\n\n"
        f"Доступные даты:\n"
        f"📅 {tomorrow.strftime('%d %B')} (завтра) - 10:00, 11:30, 14:00\n"
        f"📅 {next_day.strftime('%d %B')} - 09:00, 12:30, 16:00\n\n"
        "Напишите дату и время, например: 25 марта 11:30",
        keyboard=back_keyboard
    )


# Обработчик возврата в главное меню
@bot.on.private_message(text="🔙 В главное меню")
async def back_handler(message: Message):
    await message.answer(
        "Возвращаемся в главное меню:",
        keyboard=main_keyboard
    )


# Обработчик "Мои записи"
@bot.on.private_message(text="📋 Мои записи")
async def my_appointments_handler(message: Message):
    # Здесь будет логика получения записей из БД
    await message.answer(
        "📋 Ваши записи:\n\n"
        "У вас пока нет активных записей.",
        keyboard=main_keyboard
    )


# Обработчик помощи
@bot.on.private_message(text="❓ Помощь")
async def help_handler(message: Message):
    await message.answer(
        "🆘 Помощь по боту:\n\n"
        "• Запись к врачу - выберите специалиста и удобное время\n"
        "• Мои записи - просмотр активных записей\n"
        "• Отмена записи - напишите 'отмена' и номер записи\n\n"
        "Если возникли проблемы, позвоните в регистратуру: 8 (861) 123-45-67",
        keyboard=main_keyboard
    )


# Обработчик для записи времени
@bot.on.private_message()
async def booking_handler(message: Message):
    text = message.text.lower()

    # Проверяем, похоже ли сообщение на запись времени
    if any(month in text for month in ["марта", "апреля", "мая", "июня", "января", "февраля"]):
        await message.answer(
            "✅ Ваша запись принята!",
            keyboard=main_keyboard
        )
    else:
        # Проверяем, не является ли сообщение кнопкой
        if text not in ["📝 Проверить доступные записи", "📋 мои записи", "❓ помощь",
                        "👶 педиатр", "🧠 невролог", "👂 лор", "👁️ окулист", "🦷 стоматолог",
                        "🏥 московская ул., 225", "🏥 ул. ударников, 12а", "🔙 назад"]:
            await message.answer(
                "Я не понял команду. Используйте кнопки меню:",
                keyboard=main_keyboard
            )


if __name__ == "__main__":
    print("✅ Бот запущен и готов к работе!")
    print("📱 Группа: Помощь с записью ребенка в поликлинику Тихорецк")
    bot.run_forever()