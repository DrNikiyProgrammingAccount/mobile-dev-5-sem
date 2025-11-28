def test_character_upsert(db_module):
    db = db_module
    # Предполагаем, что список персонажей уже есть. Берём любую существующую запись.
    characters = db.list_characters() if hasattr(db, "list_characters") else db.list_characters()
    assert characters, "Список персонажей пуст - проверь schema в db.py"
    any_id = characters[0]["id"]

    uid = 777001
    db.set_user_character(uid, any_id)
    p1 = db.get_user_character(uid)
    assert p1["id"] == any_id

    # Выберем другого персонажа и убедимся, что запись обновилась
    other_id = characters[-1]["id"] if characters[-1]["id"] != any_id else characters[1]["id"]
    db.set_user_character(uid, other_id)
    p2 = db.get_user_character(uid)
    assert p2["id"] == other_id

def test_models_single_active_switch(db_module):
    db = db_module
    models = db.list_models()
    assert len(models) >= 2, "Нужно >= 2 моделей в списке"
    a, b = models[0]["id"], models[1]["id"]

    # Сделать активной A
    db.set_active_model(a)
    act = db.get_active_model()
    assert act["id"] == a

    # Сделать активной B
    db.set_active_model(b)
    act2 = db.get_active_model()
    assert act2["id"] == b

    # Ровно одна активная
    with db._connect() as conn:
        cnt = conn.execute("SELECT COUNT(*) FROM models WHERE active=1").fetchone()[0]
        assert cnt == 1, "Должна быть ровно одна активная модель"


import pytest

def test_set_active_model_rejects_unknown_id(db_module):
    db = db_module

    # Берём гарантированно несуществующий ID (например, очень большое число)
    unknown_id = 999999

    with pytest.raises(ValueError) as excinfo:
        db.set_active_model(unknown_id)

    # Сообщение об ошибке из db.py:
    assert "Неизвестный ID модели" in str(excinfo.value)


def test_set_user_character_rejects_unknown_id(db_module):

    db = db_module

    user_id = 777002

    unknown_character_id = 999999

    with pytest.raises(ValueError) as excinfo:
        db.set_user_character(user_id, unknown_character_id)

    assert "Неизвестный ID персонажа" in str(excinfo.value)


def test_get_user_character_falls_back_to_default(db_module):
    db = db_module

    # Берём пользователя, для которого мы точно ничего не записывали
    uid = 999001

    # Вызов без предварительного set_user_character
    ch = db.get_user_character(uid)

    # Ожидание: нам вернётся существующий персонаж из таблицы characters
    all_chars = db.list_characters()
    assert all_chars, "Список персонажей пуст - проверь schema в db.py"

    ids = {c["id"] for c in all_chars}
    assert ch["id"] in ids, "get_user_character должен возвращать одного из существующих персонажей"


def test_add_note_success(db_module):
    db = db_module
    uid = 888001
    text = "Моя первая заметка"

    note_id = db.add_note(uid, text)

    assert note_id > 0, "add_note должен вернуть положительный ID"

    # Проверяем, что заметка реально создалась
    notes = db.list_notes(uid)
    assert any(n[0] == note_id and n[1] == text for n in notes)


def test_add_note_creates_stats_record(db_module):
    db = db_module
    uid = 888002

    note_id = db.add_note(uid, "Тестовая заметка")

    # Проверяем запись в stats
    with db._connect() as conn:
        stat = conn.execute(
            "SELECT action FROM stats WHERE user_id = ? AND note_id = ?",
            (uid, note_id)
        ).fetchone()

    assert stat is not None, "Должна быть запись в stats"
    assert stat[0] == "create"


def test_add_note_limit_50(db_module):
    db = db_module
    uid = 888003

    # Добавляем 50 заметок
    for i in range(50):
        result = db.add_note(uid, f"Заметка {i}")
        assert result > 0, f"Заметка {i} должна добавиться"

    # 51-я должна вернуть 0
    result = db.add_note(uid, "Лишняя заметка")
    assert result == 0, "При превышении лимита должен вернуться 0"


def test_add_note_limit_per_user(db_module):
    db = db_module
    uid1 = 888004
    uid2 = 888005

    # Забиваем лимит первому
    for i in range(50):
        db.add_note(uid1, f"Заметка {i}")

    # Второй всё ещё может добавлять
    result = db.add_note(uid2, "Заметка другого пользователя")
    assert result > 0, "Лимит считается для каждого user_id отдельно"


def test_list_notes_returns_notes(db_module):
    db = db_module
    uid = 888006

    db.add_note(uid, "Первая")
    db.add_note(uid, "Вторая")
    db.add_note(uid, "Третья")

    notes = db.list_notes(uid)

    assert len(notes) == 3
    texts = [n[1] for n in notes]
    assert set(texts) == {"Первая", "Вторая", "Третья"}


def test_list_notes_order_desc(db_module):
    db = db_module
    uid = 888007

    id1 = db.add_note(uid, "Первая")
    id2 = db.add_note(uid, "Вторая")
    id3 = db.add_note(uid, "Третья")

    notes = db.list_notes(uid)
    ids = [n[0] for n in notes]

    assert ids == [id3, id2, id1], "Заметки должны идти от новых к старым"


def test_list_notes_respects_limit(db_module):
    db = db_module
    uid = 888008

    for i in range(5):
        db.add_note(uid, f"Заметка {i}")

    notes = db.list_notes(uid, limit=3)

    assert len(notes) == 3, "Должно вернуться не более limit записей"


def test_list_notes_empty_for_new_user(db_module):
    db = db_module
    uid = 888009

    notes = db.list_notes(uid)

    assert notes == [], "Для нового пользователя — пустой список"


def test_list_notes_returns_correct_structure(db_module):
    db = db_module
    uid = 888010

    db.add_note(uid, "Тест структуры")
    notes = db.list_notes(uid)

    assert len(notes) == 1
    note = notes[0]
    assert len(note) == 3, "Кортеж должен содержать (id, text, created_at)"
    assert isinstance(note[0], int)      # id
    assert note[1] == "Тест структуры"   # text
    assert note[2] is not None           # created_at


def test_update_note_success(db_module):
    db = db_module
    uid = 888011

    note_id = db.add_note(uid, "Оригинал")
    result = db.update_note(uid, note_id, "Обновлено")

    assert result is True

    notes = db.list_notes(uid)
    note = next(n for n in notes if n[0] == note_id)
    assert note[1] == "Обновлено"


def test_update_note_creates_edit_stats(db_module):
    db = db_module
    uid = 888012

    note_id = db.add_note(uid, "Текст")
    db.update_note(uid, note_id, "Новый текст")

    with db._connect() as conn:
        cnt = conn.execute(
            "SELECT COUNT(*) FROM stats WHERE user_id = ? AND note_id = ? AND action = 'edit'",
            (uid, note_id)
        ).fetchone()[0]

    assert cnt == 1, "Должна быть ровно одна запись 'edit' в stats"


def test_update_note_nonexistent_returns_false(db_module):
    db = db_module
    uid = 888013

    result = db.update_note(uid, 999999, "Какой-то текст")

    assert result is False


def test_update_note_wrong_user_returns_false(db_module):
    db = db_module
    uid1 = 888014
    uid2 = 888015

    note_id = db.add_note(uid1, "Заметка первого")

    # Попытка обновить чужую заметку
    result = db.update_note(uid2, note_id, "Хакер атакует")

    assert result is False, "Нельзя редактировать чужую заметку"

    # Проверяем, что оригинал не изменился
    notes = db.list_notes(uid1)
    note = next(n for n in notes if n[0] == note_id)
    assert note[1] == "Заметка первого"


def test_update_note_no_stats_on_failure(db_module):
    db = db_module
    uid = 888016

    # Пытаемся обновить несуществующую заметку
    db.update_note(uid, 999999, "Текст")

    with db._connect() as conn:
        cnt = conn.execute(
            "SELECT COUNT(*) FROM stats WHERE user_id = ? AND action = 'edit'",
            (uid,)
        ).fetchone()[0]

    assert cnt == 0, "При неудачном update не должно быть записи в stats"