# health_db.py — управление базой данных приложения
import sqlite3

def init_db():
    conn = sqlite3.connect('health_app.db')
    cursor = conn.cursor()
    
    # Таблица рецептов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS recipes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            ingredients TEXT,
            calories INTEGER,
            category TEXT
        )
    ''')
    
    # Таблица упражнений
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

def add_recipe(name, ingredients, calories, category):
    conn = sqlite3.connect('health_app.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO recipes (name, ingredients, calories, category) VALUES (?, ?, ?, ?)',
                   (name, ingredients, calories, category))
    conn.commit()
    conn.close()

def get_recipes(category=None):
    conn = sqlite3.connect('health_app.db')
    cursor = conn.cursor()
    if category:
        cursor.execute('SELECT * FROM recipes WHERE category = ?', (category,))
    else:
        cursor.execute('SELECT * FROM recipes')
    rows = cursor.fetchall()
    conn.close()
    return rows

def add_exercise(name, description, level, type_):
    conn = sqlite3.connect('health_app.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO exercises (name, description, level, type) VALUES (?, ?, ?, ?)',
                   (name, description, level, type_))
    conn.commit()
    conn.close()

def get_exercises(level=None, type_=None):
    conn = sqlite3.connect('health_app.db')
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

# Инициализация при первом запуске
if __name__ == '__main__':
    init_db()
    # Примеры рецептов
    add_recipe('Овсянка с ягодами', 'Овсянка, молоко, черника, мёд', 350, 'завтрак')
    add_recipe('Омлет с овощами', 'Яйца, помидор, перец, лук', 300, 'завтрак')
    add_recipe('Куриная грудка с гречкой', 'Куриная грудка, гречка, овощи', 550, 'обед')
    add_recipe('Салат с тунцом', 'Тунец, листья салата, огурец, оливковое масло', 400, 'обед')
    add_recipe('Греческий йогурт', 'Йогурт, орехи, мёд', 200, 'перекус')
    add_recipe('Яблоко с арахисовой пастой', 'Яблоко, арахисовая паста', 250, 'перекус')
    add_recipe('Лосось на пару с овощами', 'Лосось, брокколи, морковь', 600, 'ужин')
    add_recipe('Творог с зеленью', 'Творог, огурец, зелень', 300, 'ужин')

    # Примеры упражнений
    add_exercise('Приседания', '20 повторений', 'новичок', 'силовое')
    add_exercise('Отжимания от стены', '15 повторений', 'новичок', 'силовое')
    add_exercise('Планка', '30 секунд', 'средний', 'силовое')
    add_exercise('Выпады', '15 на каждую ногу', 'средний', 'силовое')
    add_exercise('Подтягивания', '10 повторений', 'профи', 'силовое')
    add_exercise('Упражнение для глаз: вверх-вниз', 'Смотреть вверх, вниз, влево, вправо', 'новичок', 'для глаз')
    add_exercise('Упражнение для глаз: круг', 'Вращать глазами по кругу', 'средний', 'для глаз')
    add_exercise('Наклоны головы', '10 наклонов вправо и влево', 'новичок', 'растяжка')
    add_exercise('Растяжка спины', 'Наклониться вперёд, потянуться', 'средний', 'растяжка')
    print("База данных создана и заполнена примерами!")