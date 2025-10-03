import logging
import os
from dotenv import load_dotenv
import telebot
from telebot import types
import requests

logging.basicConfig(
    level=logging.INFO,
    filename="lesson1_homework.log",
    format="%(asctime)s - %(levelname)s - %(message)s"
)

load_dotenv()
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    logging.critical(f"Не найден токен!")
    raise RuntimeError("Не найден токен!")
bot = telebot.TeleBot(TOKEN)


def parse_ints_from_text(message):
    parts = message.split()
    numbers = []

    for p in parts[:]:
        if p.isdigit():  # только положительные целые
            numbers.append(int(p))

    return numbers


def make_main_Kb() -> types.ReplyKeyboardMarkup:
    # Создаём клавиатуру с автоподгонкой размера
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    # Добавляем кнопки по рядам kb.row "О боте", "Сумма")
    kb.row("/start", "/about", "/sum", "/max", "/hide", "/show", "/weather")
    return kb


def on_sum_numbers(m: types.Message) -> None:
    nums = parse_ints_from_text(m.text)
    logging.info("KB-sum next step from id=%s text=%r -> %r", m.from_user.id if m.from_user else "?", m.text, nums)
    if not nums:
        bot.reply_to(m, "Не вижу чисел. Пример: 2 3 10")
    else:
        bot.reply_to(m, f"Сумма: {sum(nums)}")


def on_max_numbers(m: types.Message) -> None:
    nums = parse_ints_from_text(m.text)
    logging.info("KB-sum next step from id=%s text=%r -> %r", m.from_user.id if m.from_user else "?", m.text, nums)
    if not nums:
        bot.reply_to(m, "Не вижу чисел. Пример: 2 3 10")
    else:
        bot.reply_to(m, f"Максимум: {max(nums)}")


def fetch_weather_moscow_open_meteo() -> str:
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": 61.23174578279055,
        "longitude": -48.0984177129272,
        "current": "temperature_2m",
        "timezone": "Europe/Moscow"
    }
    try:
        r = requests.get(url, params=params, timeout=5)
        r.raise_for_status()
        t = r.json()["current"]["temperature_2m"]
        return f"Кангеллингуит: сейчас {round(t)}°C"
    except Exception:
        return "Не удалось получить погоду."


@bot.message_handler(commands=['start'])
def start(message):
    logging.info(f"Пользователь {message.from_user.username} (ID: {message.from_user.id}) вызвал /start")
    bot.reply_to(message, "Привет! Напиши /help\n"
                          "чтобы узнать\n"
                          "зачем\n"
                          "я\n"
                          "нужен...", reply_markup=make_main_Kb())


@bot.message_handler(commands=['help'])
def help_cmd(message):
    logging.info(f"Пользователь {message.from_user.username} (ID: {message.from_user.id}) вызвал /help")
    bot.reply_to(message, "Всё очень просто, смотри!\n"
                          "/start - начать\n"
                          "/help - помогите...\n"
                          "/about - узнать обо мне побольше\n"
                          "/ping - попинговать меня")


@bot.message_handler(commands=['about'])
def help_cmd(message):
    logging.info(f"Пользователь {message.from_user.username} (ID: {message.from_user.id}) вызвал /about")
    bot.reply_to(message, "Бот создан Андрюшиным Никитой Сергеевичем, "
                          "и создан для демонстрации возможностей библиотеки pytelegrambotapi, "
                          "с перспективой на реализацию полезного бота для решения конкретной проблемы"
                          "Версия: 1.1.homework")


@bot.message_handler(commands=['ping'])
def help_cmd(message):
    logging.info(f"Пользователь {message.from_user.username} (ID: {message.from_user.id}) вызвал /ping")
    bot.reply_to(message, "Понг. Я работаю. Пока что")


@bot.message_handler(commands=['sum'])
def cmd_sum(m):
    bot.send_message(m.chat.id, "Введи числа через пробел или запятую:")
    bot.register_next_step_handler(m, on_sum_numbers)


@bot.message_handler(commands=['max'])
def cmd_sum(m):
    bot.send_message(m.chat.id, "Введи числа через пробел или запятую:")
    bot.register_next_step_handler(m, on_max_numbers)


@bot.message_handler(commands=['hide'])
def hide_kb(m):
    rm = types.ReplyKeyboardRemove()
    bot.send_message(m.chat.id, "Спрятал клавиатуру.", reply_markup=rm)


@bot.message_handler(commands=['show'])
def hide_kb(m):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("/start", "/about", "/sum", "/max", "/hide", "/show")
    bot.send_message(m.chat.id, "Клавиатура показана.", reply_markup=kb)


@bot.message_handler(commands=['confirm'])
def confirm_cmd(m):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("Дa", callback_data="confirm:yes"),
           types.InlineKeyboardButton("Нет", callback_data="confirm:no"))
    bot.send_message(m.chat.id, "Показать погоду?", reply_markup=kb)


@bot.message_handler(commands=['weather'])
def confirm_cmd(m):
    bot.send_message(m.chat.id, "Введите /confirm")


@bot.callback_query_handler(func=lambda c: c.data.startswith("confirm:"))
def on_confirm(c):  # Извлекаем выбор пользователя
    choice = c.data.split(":", 1)[1]
    bot.answer_callback_query(c.id, "Принято")
    bot.edit_message_reply_markup(c.message.chat.id, c.message.message_id, reply_markup=None)
    bot.send_message(c.message.chat.id, fetch_weather_moscow_open_meteo() if choice == "yes" else "Отменено.")


if __name__ == "__main__":
    bot.infinity_polling(skip_pending=True)
