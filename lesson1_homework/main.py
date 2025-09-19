import logging
import os
from dotenv import load_dotenv
import telebot

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

@bot.message_handler(commands=['start'])
def start(message):
    logging.info(f"Пользователь {message.from_user.username} (ID: {message.from_user.id}) вызвал /start")
    bot.reply_to(message, "Привет! Напиши /help\n"
                          "чтобы узнать\n"
                          "зачем\n"
                          "я\n"
                          "нужен...")
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
if __name__ == "__main__":
    bot.infinity_polling(skip_pending=True)

