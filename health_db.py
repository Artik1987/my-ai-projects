# health_db.py — управление базой данных (с примерами и поддержкой .exe)
import sqlite3
import os
import sys

def get_db_path():
    """Возвращает правильный путь к базе данных (рядом с .exe или скриптом)."""
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, "health_app.db")

def init_db():
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS recipes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            ingredients TEXT,
            calories INTEGER,
            category TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS exercises (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            level TEXT,
            type TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

def seed_db():
    """Заполняет базу примерами, если она пустая."""
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    
    # Проверяем, есть ли уже рецепты
    cursor.execute('SELECT COUNT(*) FROM recipes')
    recipes_count = cursor.fetchone()[0]
    
    if recipes_count == 0:
        # Примеры рецептов
        recipes = [
            ('Овсянка с ягодами', 'Овсянка, молоко, черника, мёд', 350, 'завтрак'),
            ('Омлет с овощами', 'Яйца, помидор, перец, лук', 300, 'завтрак'),
            ('Куриная грудка с гречкой', 'Куриная грудка, гречка, овощи', 550, 'обед'),
            ('Салат с тунцом', 'Тунец, листья салата, огурец, оливковое масло', 400, 'обед'),
            ('Греческий йогурт', 'Йогурт, орехи, мёд', 200, 'перекус'),
            ('Яблоко с арахисовой пастой', 'Яблоко, арахисовая паста', 250, 'перекус'),
            ('Лосось на пару с овощами', 'Лосось, брокколи, морковь', 600, 'ужин'),
            ('Творог с зеленью', 'Творог, огурец, зелень', 300, 'ужин'),
        ]
        cursor.executemany(
            'INSERT INTO recipes (name, ingredients, calories, category) VALUES (?, ?, ?, ?)',
            recipes
        )
    
    # Проверяем, есть ли уже упражнения
    cursor.execute('SELECT COUNT(*) FROM exercises')
    exercises_count = cursor.fetchone()[0]
    
    if exercises_count == 0:
        # Примеры упражнений
        exercises = [
            ('Приседания', '20 повторений', 'новичок', 'силовое'),
            ('Отжимания от стены', '15 повторений', 'новичок', 'силовое'),
            ('Планка', '30 секунд', 'средний', 'силовое'),
            ('Выпады', '15 на каждую ногу', 'средний', 'силовое'),
            ('Подтягивания', '10 повторений', 'профи', 'силовое'),
            ('Упражнение для глаз: вверх-вниз', 'Смотреть вверх, вниз, влево, вправо', 'новичок', 'для глаз'),
            ('Упражнение для глаз: круг', 'Вращать глазами по кругу', 'средний', 'для глаз'),
            ('Наклоны головы', '10 наклонов вправо и влево', 'новичок', 'растяжка'),
            ('Растяжка спины', 'Наклониться вперёд, потянуться', 'средний', 'растяжка'),
        ]
        cursor.executemany(
            'INSERT INTO exercises (name, description, level, type) VALUES (?, ?, ?, ?)',
            exercises
        )
    
    conn.commit()
    conn.close()

# ... остальные функции (add_recipe, get_recipes, add_exercise, get_exercises) без изменений

def add_recipe(name, ingredients, calories, category):
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    cursor.execute('INSERT INTO recipes (name, ingredients, calories, category) VALUES (?, ?, ?, ?)',
                   (name, ingredients, calories, category))
    conn.commit()
    conn.close()

def get_recipes(category=None):
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    if category:
        cursor.execute('SELECT * FROM recipes WHERE category = ?', (category,))
    else:
        cursor.execute('SELECT * FROM recipes')
    rows = cursor.fetchall()
    conn.close()
    return rows

def add_exercise(name, description, level, type_):
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    cursor.execute('INSERT INTO exercises (name, description, level, type) VALUES (?, ?, ?, ?)',
                   (name, description, level, type_))
    conn.commit()
    conn.close()

def get_exercises(level=None, type_=None):
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    query = 'SELECT * FROM exercises'
    params = []
    conditions = []
    if level:
        conditions.append('level = ?')
        params.append(level)
    if type_:
        conditions.append('type = ?')
        params.append(type_)
    if conditions:
        query += ' WHERE ' + ' AND '.join(conditions)
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return rows

if __name__ == '__main__':
    init_db()
    seed_db()
    print("✅ База данных создана и заполнена примерами!")