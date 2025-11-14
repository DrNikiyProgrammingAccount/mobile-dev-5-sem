import os
import random
from datetime import datetime

from dotenv import load_dotenv
import telebot
from telebot import types
from db import init_db, add_note, list_notes, update_note, delete_note, find_notes, list_all_notes, \
    get_combined_stats, list_models, get_active_model, set_active_model, get_user_character, list_characters, \
    set_user_character, get_character_by_id, get_model_by_id
from openrouter import chat_once, OpenRouterError

load_dotenv()
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise RuntimeError("В .env файле нет TOKEN")

bot = telebot.TeleBot(TOKEN)

init_db()
def create_main_keyboard():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("/start", "/help", "/note_add", "/note_list", "/note_find", "/note_edit", "/note_del", "/note_export", "/stats", "/ask_model")
    return kb

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Привет! Я бот для заметок. Используй /help для списка команд.", reply_markup=create_main_keyboard())

@bot.message_handler(commands=['help'])
def help_cmd(message):
    help_text = """
Доступные команды:
/note_add <текст> - Добавить заметку
/note_list - Показать все заметки
/note_find <запрос> - Найти заметку
/note_edit <id> <новый текст> - Изменить заметку
/note_del <id> - Удалить заметку
/note_export - Экспорт в файл
/stats - Cтатистика
/models - Список моделей
/model <id> - Изменить модель/показать текущую
/ask <текст> - Спросить модель
/ask_model <ID> <Текст> - Спросить модель с конкретным ID
"""
    bot.reply_to(message, help_text)



@bot.message_handler(commands=['note_list'])
def note_list(message):
    user_id = message.from_user.id
    user_notes = list_notes(user_id)

    if not user_notes:
        bot.reply_to(message, "Заметок пока нет.")
        return

    response = "Ваши заметки:\n" + "\n".join([f"{note['id']}: {note['text']}" for note in user_notes])
    bot.reply_to(message, response)






@bot.message_handler(commands=['note_add'])
def note_add_start(message):
    bot.reply_to(message, "Введите текст для новой заметки:")
    bot.register_next_step_handler(message, on_note_add_text)

def on_note_add_text(message):
    text = message.text.strip()
    if not text:
        bot.reply_to(message, "Текст не может быть пустым. Попробуйте еще раз: /note_add")
        return

    user_id = message.from_user.id
    note_id = add_note(user_id, text)

    if note_id > 0:
        bot.reply_to(message, f"✅ Заметка #{note_id} добавлена!")
    else:
        bot.reply_to(message, f"❌ Достигнут лимит заметок ({50} шт.). Удалите старые, чтобы добавить новые.")

@bot.message_handler(commands=['note_find'])
def note_find_start(message):
    bot.reply_to(message, "Введите текст для поиска:")
    bot.register_next_step_handler(message, on_note_find_query)

def on_note_find_query(message):
    query_text = message.text.strip()
    if not query_text:
        bot.reply_to(message, "Поисковый запрос не может быть пустым. Попробуйте еще раз: /note_find")
        return

    user_id = message.from_user.id
    found_notes = find_notes(user_id, query_text)

    if not found_notes:
        bot.reply_to(message, f"Ничего не найдено по запросу «{query_text}».")
        return

    response = "🔍 Результаты поиска:\n" + "\n".join([f"{note['id']}: {note['text']}" for note in found_notes])
    bot.reply_to(message, response)

@bot.message_handler(commands=['note_del'])
def note_del_start(message):
    bot.reply_to(message, "Введите ID заметки, которую хотите удалить:")
    bot.register_next_step_handler(message, on_note_del_id)

def on_note_del_id(message):
    try:
        note_id = int(message.text.strip())
    except ValueError:
        bot.reply_to(message, "ID должен быть числом. Попробуйте еще раз: /note_del")
        return

    user_id = message.from_user.id
    success = delete_note(user_id, note_id)

    if success:
        bot.reply_to(message, f"🗑️ Заметка #{note_id} удалена.")
    else:
        bot.reply_to(message, f"❌ Заметка #{note_id} не найдена или у вас нет прав для её удаления.")

@bot.message_handler(commands=['note_edit'])
def note_edit_start(message):
    bot.reply_to(message, "Введите ID заметки для редактирования:")
    bot.register_next_step_handler(message, on_note_edit_id)

def on_note_edit_id(message):
    try:
        note_id = int(message.text.strip())
    except ValueError:
        bot.reply_to(message, "ID должен быть числом. Попробуйте еще раз: /note_edit")
        return

    user_notes = list_all_notes(message.from_user.id)
    if not any(note['id'] == note_id for note in user_notes):
        bot.reply_to(message, f"❌ Заметка #{note_id} не найдена. Попробуйте еще раз: /note_edit")
        return

    bot.reply_to(message, f"Теперь введите новый текст для заметки #{note_id}:")
    bot.register_next_step_handler(message, on_note_edit_text, note_id=note_id)

def on_note_edit_text(message, note_id: int):
    new_text = message.text.strip()
    if not new_text:
        bot.reply_to(message, "Текст не может быть пустым. Редактирование отменено. Попробуйте еще раз: /note_edit")
        return

    user_id = message.from_user.id
    success = update_note(user_id, note_id, new_text)

    if success:
        bot.reply_to(message, f"✍️ Заметка #{note_id} успешно изменена.")
    else:
        bot.reply_to(message, f"❌ Произошла ошибка при изменении заметки #{note_id}.")


@bot.message_handler(commands=['note_export'])
def note_export_detailed(message):
    user_id = message.from_user.id
    username = message.from_user.username or f"user_{user_id}"

    stats = get_combined_stats(user_id)
    all_notes = list_all_notes(user_id)

    if not all_notes:
        bot.reply_to(message, "У вас нет заметок для экспорта.")
        return

    today_str = datetime.now().strftime('%Y-%m-%d %H:%M')
    content = f"# Экспорт заметок для пользователя @{username}\n"
    content += f"Дата экспорта: {today_str}\n\n"

    content += "## 📊 Сводная статистика\n\n"
    content += f"* **Занято слотов:** {stats['total_notes']} / {50}\n"
    content += f"* **Суммарный объем:** {stats['total_chars']:,} символов\n\n"

    content += "### История действий (за всё время)\n"
    content += f"* ✅ Создано: **{stats['total_created']}**\n"
    content += f"* ✍️ Изменено: **{stats['total_edited']}**\n"
    content += f"* ❌ Удалено: **{stats['total_deleted']}**\n\n"

    content += "### Активность за последнюю неделю\n"
    content += f"* ✅ Создано: **{stats['weekly_created']}**\n"
    content += f"* ✍️ Изменено: **{stats['weekly_edited']}**\n"
    content += f"* ❌ Удалено: **{stats['weekly_deleted']}**\n\n"

    content += "---\n\n"
    content += f"## 📝 Ваши заметки ({len(all_notes)} шт.)\n\n"

    for note in all_notes:
        content += f"### Заметка #{note['id']}\n"
        content += f"* **Дата создания:** {note['created_at']}\n\n"
        note_text_quoted = "> " + note['text'].replace('\n', '\n> ')
        content += f"{note_text_quoted}\n\n"
        content += "---\n\n"

    file_path = f"export_{username}_{datetime.now().strftime('%Y%m%d')}.md"

    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        with open(file_path, 'rb') as f:
            bot.send_document(
                message.chat.id,
                f,
                caption=f"Ваш подробный экспорт готов.\nФайл содержит {len(all_notes)} заметок и полную статистику."
            )

    except Exception as e:
        print(f"Ошибка при экспорте заметок для user_id {user_id}: {e}")
        bot.reply_to(message, "Произошла ошибка при создании файла экспорта.")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

@bot.message_handler(commands=['stats'])
def note_stats(message):
    user_id = message.from_user.id
    stats = get_combined_stats(user_id)

    total_notes = stats['total_notes']

    BAR_CHAR_FILLED = '█'
    BAR_CHAR_EMPTY = '░'
    BAR_LENGTH = 20

    filled_count = int((total_notes / 50) * BAR_LENGTH)
    empty_count = BAR_LENGTH - filled_count

    histogram = f"{BAR_CHAR_FILLED * filled_count}{BAR_CHAR_EMPTY * empty_count}"

    response_text = (
        f"📊 **Ваша статистика**\n\n"
        f"**Занято места для заметок:**\n"
        f"`{histogram}`\n"
        f"Использовано **{total_notes}** из **{50}** слотов.\n"
        f"📝 **Суммарный объем:** `{stats['total_chars']:,}` символов\n"
        f"────────────────────\n"
        f"**История действий (всего):**\n"
        f"✅ Создано: **{stats['total_created']}**\n"
        f"✍️ Изменено: **{stats['total_edited']}**\n"
        f"❌ Удалено: **{stats['total_deleted']}**\n"
        f"────────────────────\n"
        f"**Активность за неделю:**\n"
        f"✅ Создано: **{stats['weekly_created']}**\n"
        f"✍️ Изменено: **{stats['weekly_edited']}**\n"
        f"❌ Удалено: **{stats['weekly_deleted']}**"
    )

    bot.reply_to(message, response_text, parse_mode='Markdown')



@bot.message_handler(commands=["models"])
def cmd_models(message: types.Message) -> None:
    items = list_models()
    if not items:
        bot.reply_to(message, "Список моделей пуст.")
        return
    lines = ["Доступные модели:"]
    for m in items:
        star = "★" if m["active"] else " "
        lines.append(f"{star} {m['id']}. {m['label']}  [{m['key']}]")
    lines.append("\nАктивировать: /model <ID>")
    bot.reply_to(message, "\n".join(lines))

@bot.message_handler(commands=["model"])
def cmd_model(message: types.Message) -> None:
    arg = message.text.replace("/model", "", 1).strip()

    if not arg:
        active = get_active_model()
        bot.reply_to(message, text=f"Текущая активная модель: {active['label']} [{active['key']}]\n(сменить: /model <ID> или /models)")
        return

    if not arg.isdigit():
        bot.reply_to(message, text="Использование: /model <ID из /models>")
        return

    try:
        active = set_active_model(int(arg))
        bot.reply_to(message, text=f"Активная модель переключена: {active['label']} [{active['key']}]")
    except ValueError:
        bot.reply_to(message, text="Неизвестный ID модели. Сначала /models.")


@bot.message_handler(commands=["ask"])
def cmd_ask(message: types.Message) -> None:
    q = message.text.replace("/ask", "", 1).strip()
    if not q:
        bot.reply_to(message, text="Использование: /ask <вопрос>")
        return

    msgs = _build_messages(message.from_user.id, q[:600])
    model_key = get_active_model()["key"]

    try:
        text, ms = chat_once(msgs, model=model_key, temperature=0.2, max_tokens=400)
        out = (text or "").strip()[:4000]  # не переполняем сообщение Telegram
        bot.reply_to(message, text=f"{out}\n\n({ms} мс; модель: {model_key})")
    except OpenRouterError as e:
        bot.reply_to(message, text=f"Ошибка: {e}")
    except Exception:
        bot.reply_to(message, text="Непредвиденная ошибка.")


def _build_messages(user_id: int, user_text: str) -> list[dict]:
    p = get_user_character(user_id)
    system = (
        f"Ты отвечаешь строго в образе персонажа: {p['name']}.\n"
        f"{p['prompt']}\n\n"
        "Правила:\n"
        "1) Всегда держи стиль и манеру речи выбранного персонажа. При необходимости - переформулируй.\n"
        "2) Технические ответы давай корректно и по пунктам, но в характерной манере.\n"
        "3) Не раскрывай, что ты 'играешь роль'.\n"
        "4) Не используй длинные дословные цитаты из фильмов/книг (>10 слов).\n"
        "5) Если стиль персонажа выражен слабо - переформулируй ответ и усили характер персонажа, сохраняя фактическую точность.\n"
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user_text},
    ]

def _build_messages_for_character(character: dict, user_text: str) -> list[dict]:
    system = (
        f"Ты отвечаешь строго в образе персонажа: {character['name']}.\n"
        f"{character['prompt']}\n"
        "Правила:\n"
        "1) Всегда держи стиль и манеру речи выбранного персонажа. При необходимости – переформулируй.\n"
        "2) Технические ответы давай корректно и по пунктам, но в характерной манере.\n"
        "3) Не раскрывай, что ты 'играешь роль'.\n"
        "4) Не используй длинные дословные цитаты из фильмов/книг (>10 слов).\n"
        "5) Если стиль персонажа выражен слабо – переформулируй ответ и усили характер персонажа, сохраняя фактическую точность.\n"
    )

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user_text},
    ]


@bot.message_handler(commands=["characters"])
def cmd_characters(message: types.Message) -> None:
    user_id = message.from_user.id
    items = list_characters()
    if not items:
        bot.reply_to(message, text="Каталог персонажей пуст.")
        return

    try:
        current = get_user_character(user_id)["id"]
    except Exception:
        current = None

    lines = ["Доступные персонажи:"]
    for p in items:
        star = "★" if current is not None and p["id"] == current else ""
        lines.append(f"{star}{p['id']}. {p['name']}")
    lines.append("\nВыбор: /character <ID>")
    bot.reply_to(message, "\n".join(lines))


@bot.message_handler(commands=["character"])
def cmd_character(message: types.Message) -> None:
    user_id = message.from_user.id
    arg = message.text.replace("/character", "", 1).strip()
    if not arg:
        p = get_user_character(user_id)
        bot.reply_to(message, f"Текущий персонаж: {p['name']}\n(сменить: /characters, затем /character <ID>)")
        return
    if not arg.isdigit():
        bot.reply_to(message, text="Использование: /character <ID из /characters>")
        return

    try:
        p = set_user_character(user_id, int(arg))
        bot.reply_to(message, text=f"Персонаж установлен: {p['name']}")
    except ValueError:
        bot.reply_to(message, text="Неизвестный ID персонажа. Сначала /characters.")


@bot.message_handler(commands=["whoami"])
def cmd_whoami(message: types.Message) -> None:
    character = get_user_character(message.from_user.id)
    model = get_active_model()
    bot.reply_to(message, text=f"Модель: {model['label']} [{model['key']}]\nПерсонаж: {character['name']}")



@bot.message_handler(commands=["ask_random"])
def cmd_ask_random(message: types.Message) -> None:
    q = message.text.replace("/ask_random","", 1).strip()
    if not q:
        bot.reply_to(message, text="Использование: /ask_random <вопрос>")
        return
    q = q[:600]

    items = list_characters()
    if not items:
        bot.reply_to(message, text="Каталог персонажей пуст.")
        return
    chosen = random.choice(items)
    character = get_character_by_id(chosen["id"]) # получаем prompt

    msgs = _build_messages_for_character(character, q)
    model_key = get_active_model()["key"]

    try:
        text, ms = chat_once(msgs, model=model_key, temperature=0.2, max_tokens=400)
        out = (text or "").strip()[:4000]
        bot.reply_to(message, text=f"{out}\n\n{ms} мс; модель: {model_key}; как: {character['name']}")
    except OpenRouterError as e:
        bot.reply_to(message, text=f"Ошибка: {e}")
    except Exception:
        bot.reply_to(message, text="Непредвиденная ошибка.")


@bot.message_handler(commands=["ask_model"])
def cmd_ask_model(message: types.Message) -> None:
    parts = message.text.split(maxsplit=2)

    if len(parts) < 3:
        bot.reply_to(message, text="Использование: /ask_model <ID модели> <вопрос>")
        return

    model_id_str, q = parts[1], parts[2].strip()

    if not model_id_str.isdigit():
        bot.reply_to(message, text="ID модели должен быть числом. Посмотрите ID в /models.")
        return

    model_id = int(model_id_str)

    target_model = get_model_by_id(model_id)
    if not target_model:
        bot.reply_to(message, text=f"Модель с ID {model_id} не найдена. Используйте /models для просмотра списка.")
        return

    msgs = _build_messages(message.from_user.id, q[:600])
    model_key = target_model["key"]
    model_label = target_model["label"]

    try:
        text, ms = chat_once(msgs, model=model_key, temperature=0.2, max_tokens=400)
        out = (text or "").strip()[:4000]
        bot.reply_to(message, text=f"{out}\n\n({ms} мс; модель: {model_label})")
    except OpenRouterError as e:
        bot.reply_to(message, text=f"Ошибка: {e}")
    except Exception:
        bot.reply_to(message, text="Непредвиденная ошибка.")


if __name__ == "__main__":
    print("Бот запускается...")
    bot.infinity_polling(skip_pending=True)