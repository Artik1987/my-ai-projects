# health_timer.py — полная версия с вкладками и звуком
import customtkinter as ctk
import time
import json
import os
import winsound  # <-- Добавлено для звука
from datetime import date, datetime
from plyer import notification
from health_db import init_db, seed_db, get_recipes, get_exercises, add_recipe
init_db()
seed_db()  # <-- Заполняет примерами, если база пустая


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

app = ctk.CTk()
app.title("Health App")
app.geometry("750x650")

# ── Функция звукового уведомления ──
def play_sound():
    try:
        # Воспроизводит системный звук (работает только на Windows)
        winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
    except Exception as e:
        print(f"Звук не сработал: {e}")

# Создаём вкладки
tabview = ctk.CTkTabview(app, width=730, height=620)
tabview.pack(padx=10, pady=10)

tab_timer = tabview.add("Таймер")
tab_food = tabview.add("Питание")
tab_exercise = tabview.add("Упражнения")

# ========== ВКЛАДКА ТАЙМЕР ==========
timer_frame = ctk.CTkFrame(tab_timer)
timer_frame.pack(fill="both", expand=True)

STATS_FILE = "stats.json"
BREAK_DURATION = 5 * 60
MEAL_INTERVAL = 4 * 60 * 60

SNACKS = [
    "🥜 Горсть миндаля и зелёное яблоко. Полезные жиры и клетчатка.",
    "🥣 Греческий йогурт с ягодами и ложкой мёда. Белок и антиоксиданты.",
    "🥕 Морковь и огурец с хумусом. Витамины и хрустящая текстура.",
    "🥑 Половина авокадо с цельнозерновым хлебом. Жиры для сердца и мозга.",
    "🥤 Смузи из шпината, банана и молока. Легко и питательно.",
    "🍇 Виноград и кусочек нежирного сыра. Классика быстрого перекуса.",
    "🥚 Варёное яйцо и помидор. Белок и витамины.",
    "🍎 Яблоко с ложкой арахисовой пасты. Клетчатка и полезные жиры.",
    "🥜 Грецкие орехи и чернослив. Для работы мозга и пищеварения.",
    "🍌 Банан и горсть тыквенных семечек. Энергия и магний.",
    "🥛 Кефир с семенами льна. Для микрофлоры кишечника.",
    "🧀 Творог с зеленью и огурцом. Белок без лишних углеводов.",
    "🍊 Апельсин и миндаль. Витамин C и жиры.",
    "🥗 Небольшой салат из тунца и листьев салата. Лёгкий белок.",
    "🍓 Клубника со сливками (нежирными). Антиоксиданты и кальций.",
    "🥒 Огурец с творожным сыром и зеленью. Свежо и низкокалорийно.",
    "🌰 Каштан или финики с чаем. Быстрый источник энергии.",
    "🥜 Арахис (несолёный) и яблоко. Белок и клетчатка.",
    "🍵 Зелёный чай с ложкой мёда и орехами. Антиоксиданты.",
    "🥕 Морковные палочки с гуакамоле. Витамин A и жиры.",
    "🍇 Горсть винограда и 10 миндальных орехов. Лёгкий перекус.",
    "🥣 Овсянка с ягодами (маленькая порция). Долгое насыщение.",
    "🧀 Ломтик сыра и груша. Сочетание вкуса и пользы.",
    "🥚 Омлет из 1 яйца с зеленью. Белок для восстановления.",
    "🍎 Печёное яблоко с корицей. Десерт без сахара.",
    "🥜 Кедровые орехи и изюм. Микроэлементы и энергия.",
    "🥛 Ряженка с отрубями. Для пищеварения.",
    "🍌 Банан с ложкой какао-порошка. Настроение и магний.",
    "🥗 Листья салата с оливковым маслом и лимоном. Витамины.",
    "🍊 Грейпфрут и горсть фундука. Витамин C и жиры."
]

def load_stats():
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if data.get("date") != str(date.today()):
                return {"date": str(date.today()), "total_seconds": 0}
            return data
    return {"date": str(date.today()), "total_seconds": 0}

def save_stats(total_seconds):
    data = {"date": str(date.today()), "total_seconds": total_seconds}
    with open(STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# --- Виджеты таймера ---
title = ctk.CTkLabel(timer_frame, text="⏱ Health Timer", font=("Arial", 28, "bold"))
title.pack(pady=(15, 5))

interval_frame = ctk.CTkFrame(timer_frame, fg_color="transparent")
interval_frame.pack(pady=5)
ctk.CTkLabel(interval_frame, text="Интервал:", font=("Arial", 14)).pack(side="left", padx=5)
interval_var = ctk.StringVar(value="1 час")
interval_menu = ctk.CTkOptionMenu(interval_frame, values=["30 минут", "1 час", "1.5 часа"], variable=interval_var, width=120)
interval_menu.pack(side="left", padx=5)

status_label = ctk.CTkLabel(timer_frame, text="Готов к работе", font=("Arial", 16))
status_label.pack(pady=5)

timer_label = ctk.CTkLabel(timer_frame, text="00:00:00", font=("Courier New", 48, "bold"), text_color="#4CAF50")
timer_label.pack(pady=10)

progress = ctk.CTkProgressBar(timer_frame, width=400, height=15)
progress.pack(pady=5)
progress.set(0)

meal_label = ctk.CTkLabel(timer_frame, text="🍏 До перекуса: 04:00:00", font=("Arial", 16), text_color="#00BCD4")
meal_label.pack(pady=5)

stats = load_stats()
stats_label = ctk.CTkLabel(timer_frame, text=f"📊 Сегодня вы работали: {stats['total_seconds'] // 60} мин.", font=("Arial", 14), text_color="#888")
stats_label.pack(pady=10)

is_running = False
start_time = None
elapsed = 0
meal_elapsed = 0
break_window = None
meal_window = None
current_exercise_index = 0
today_total_seconds = stats["total_seconds"]

def get_work_interval():
    choice = interval_var.get()
    if choice == "30 минут":
        return 30 * 60
    elif choice == "1.5 часа":
        return 90 * 60
    return 60 * 60

def format_time(seconds):
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"

def update_stats_display():
    stats_label.configure(text=f"📊 Сегодня вы работали: {today_total_seconds // 60} мин.")

def tick():
    global elapsed, today_total_seconds, meal_elapsed
    if not is_running:
        return
    elapsed = int(time.time() - start_time)
    timer_label.configure(text=format_time(elapsed))
    meal_elapsed += 1
    time_to_meal = max(0, MEAL_INTERVAL - meal_elapsed)
    meal_label.configure(text=f"🍏 До перекуса: {format_time(time_to_meal)}")
    work_interval = get_work_interval()
    p = min(elapsed / work_interval, 1.0)
    progress.set(p)
    if p < 0.5:
        timer_label.configure(text_color="#4CAF50")
    elif p < 0.8:
        timer_label.configure(text_color="#FFC107")
    else:
        timer_label.configure(text_color="#F44336")
    if elapsed >= work_interval:
        start_break()
        return
    if meal_elapsed >= MEAL_INTERVAL:
        show_meal_window()
        return
    app.after(1000, tick)

def start_break():
    global is_running, today_total_seconds
    is_running = False
    today_total_seconds += elapsed
    save_stats(today_total_seconds)
    update_stats_display()
    status_label.configure(text="🔔 Пора сделать разминку!", text_color="#F44336")
    timer_label.configure(text="ПЕРЕРЫВ", text_color="#F44336")
    
    play_sound() # <-- Звук при перерыве
    
    try:
        notification.notify(title="Health Timer", message=f"Вы проработали {format_time(elapsed)}. Пора размяться!", timeout=10)
    except Exception as e:
        print(f"Уведомление не сработало: {e}")
    show_break_window()

def show_break_window():
    global break_window, current_exercise_index
    if break_window is not None and break_window.winfo_exists():
        break_window.focus()
        return
    break_window = ctk.CTkToplevel(app)
    break_window.title("Разминка")
    break_window.geometry("600x400")
    break_window.grab_set()
    ctk.CTkLabel(break_window, text="🧘 Время размяться!", font=("Arial", 24, "bold")).pack(pady=20)
    exercise_label = ctk.CTkLabel(break_window, text="", font=("Arial", 16), wraplength=550, justify="center")
    exercise_label.pack(pady=20, padx=20)
    current_exercise_index = 0
    exercise_label.configure(text=SNACKS[current_exercise_index] if SNACKS else "Упражнение")
    def next_exercise():
        global current_exercise_index
        current_exercise_index = (current_exercise_index + 1) % len(SNACKS)
        exercise_label.configure(text=SNACKS[current_exercise_index])
    def end_break():
        global break_window
        break_window.destroy()
        break_window = None
        reset()
    btn_frame = ctk.CTkFrame(break_window, fg_color="transparent")
    btn_frame.pack(pady=10)
    ctk.CTkButton(btn_frame, text="🔄 Следующее", width=150, height=40, command=next_exercise).grid(row=0, column=0, padx=10)
    ctk.CTkButton(btn_frame, text="✅ Закончить перерыв", width=180, height=40, command=end_break).grid(row=0, column=1, padx=10)

def show_meal_window():
    global meal_window, meal_elapsed
    if meal_window is not None and meal_window.winfo_exists():
        meal_window.focus()
        return
    meal_window = ctk.CTkToplevel(app)
    meal_window.title("Пора перекусить!")
    meal_window.geometry("600x350")
    meal_window.grab_set()
    
    play_sound() # <-- Звук при перекусе
    
    ctk.CTkLabel(meal_window, text="🍏 Время для полезного перекуса!", font=("Arial", 24, "bold"), text_color="#00BCD4").pack(pady=20)
    day_index = date.today().day - 1
    snack = SNACKS[day_index % len(SNACKS)]
    ctk.CTkLabel(meal_window, text=snack, font=("Arial", 16), wraplength=550, justify="center").pack(pady=20, padx=20)
    def close_meal():
        global meal_window, meal_elapsed
        meal_window.destroy()
        meal_window = None
        meal_elapsed = 0
        meal_label.configure(text=f"🍏 До перекуса: {format_time(MEAL_INTERVAL)}")
    ctk.CTkButton(meal_window, text="✅ Съедено, спасибо!", width=200, height=40, command=close_meal).pack(pady=20)

def start():
    global is_running, start_time
    if is_running:
        return
    is_running = True
    start_time = time.time() - elapsed
    status_label.configure(text="⏳ Работа идёт...", text_color="#4CAF50")
    start_btn.configure(state="disabled")
    pause_btn.configure(state="normal")
    reset_btn.configure(state="normal")
    tick()

def pause():
    global is_running
    is_running = False
    status_label.configure(text="⏸ Пауза", text_color="#FFC107")
    start_btn.configure(state="normal")
    pause_btn.configure(state="disabled")

def reset():
    global is_running, elapsed, start_time, meal_elapsed
    is_running = False
    elapsed = 0
    meal_elapsed = 0
    start_time = None
    timer_label.configure(text="00:00:00", text_color="#4CAF50")
    status_label.configure(text="Готов к работе", text_color="white")
    progress.set(0)
    meal_label.configure(text=f"🍏 До перекуса: {format_time(MEAL_INTERVAL)}")
    start_btn.configure(state="normal")
    pause_btn.configure(state="disabled")
    reset_btn.configure(state="normal")

btn_frame = ctk.CTkFrame(timer_frame, fg_color="transparent")
btn_frame.pack(pady=15)
start_btn = ctk.CTkButton(btn_frame, text="▶ Старт", width=120, height=40, command=start)
start_btn.grid(row=0, column=0, padx=10)
pause_btn = ctk.CTkButton(btn_frame, text="⏸ Пауза", width=120, height=40, command=pause, state="disabled")
pause_btn.grid(row=0, column=1, padx=10)
reset_btn = ctk.CTkButton(btn_frame, text="⟲ Сброс", width=120, height=40, command=reset)
reset_btn.grid(row=0, column=2, padx=10)

break_btn = ctk.CTkButton(timer_frame, text="🧘 Разминка", width=200, height=40, fg_color="#FF9800", hover_color="#F57C00", command=show_break_window)
break_btn.pack(pady=5)
meal_btn = ctk.CTkButton(timer_frame, text="🍏 Перекусить", width=200, height=40, fg_color="#00BCD4", hover_color="#0097A7", command=show_meal_window)
meal_btn.pack(pady=10)

# ========== ВКЛАДКА ПИТАНИЕ ==========
food_frame = ctk.CTkFrame(tab_food)
food_frame.pack(fill="both", expand=True)

ctk.CTkLabel(food_frame, text="🍏 Питание", font=("Arial", 24, "bold")).pack(pady=10)

# Форма добавления рецепта
add_frame = ctk.CTkFrame(food_frame)
add_frame.pack(pady=10, fill="x", padx=20)

ctk.CTkLabel(add_frame, text="➕ Добавить свой рецепт:", font=("Arial", 14, "bold")).pack(anchor="w")

name_entry = ctk.CTkEntry(add_frame, placeholder_text="Название (например, Овсянка)")
name_entry.pack(fill="x", pady=2)

ing_entry = ctk.CTkEntry(add_frame, placeholder_text="Ингредиенты (через запятую)")
ing_entry.pack(fill="x", pady=2)

cal_entry = ctk.CTkEntry(add_frame, placeholder_text="Калории (число)")
cal_entry.pack(fill="x", pady=2)

cat_add_var = ctk.StringVar(value="завтрак")
cat_add_menu = ctk.CTkOptionMenu(add_frame, values=["завтрак", "обед", "перекус", "ужин"], variable=cat_add_var)
cat_add_menu.pack(pady=5)

def add_new_recipe():
    name = name_entry.get()
    ing = ing_entry.get()
    cal = cal_entry.get()
    cat = cat_add_var.get()
    
    if name and cal.isdigit():
        add_recipe(name, ing, int(cal), cat)
        name_entry.delete(0, 'end')
        ing_entry.delete(0, 'end')
        cal_entry.delete(0, 'end')
        show_recipes()

ctk.CTkButton(add_frame, text="Сохранить рецепт", command=add_new_recipe).pack(pady=5)

# Выбор категории
cat_frame = ctk.CTkFrame(food_frame, fg_color="transparent")
cat_frame.pack(pady=5)
ctk.CTkLabel(cat_frame, text="Категория:").pack(side="left", padx=5)
cat_var = ctk.StringVar(value="завтрак")
cat_menu = ctk.CTkOptionMenu(cat_frame, values=["завтрак", "обед", "перекус", "ужин"], variable=cat_var)
cat_menu.pack(side="left", padx=5)

# Выбор продуктов (чекбоксы)
prod_frame = ctk.CTkFrame(food_frame)
prod_frame.pack(pady=10)
ctk.CTkLabel(prod_frame, text="Выберите продукты:", font=("Arial", 14)).pack(anchor="w")

cb_container = ctk.CTkFrame(prod_frame, fg_color="transparent")
cb_container.pack()

products = ["курица", "говядина", "рыба", "яйца", "овощи", "фрукты", "орехи", "молочное"]
prod_vars = {}
for i, prod in enumerate(products):
    var = ctk.BooleanVar(value=False)
    cb = ctk.CTkCheckBox(cb_container, text=prod, variable=var)
    cb.grid(row=i//4, column=i%4, padx=10, pady=2, sticky="w")
    prod_vars[prod] = var

# Список рецептов
recipes_frame = ctk.CTkScrollableFrame(food_frame, width=650, height=300)
recipes_frame.pack(pady=10)

def show_recipes():
    for widget in recipes_frame.winfo_children():
        widget.destroy()
    category = cat_var.get()
    recipes = get_recipes(category=category)
    selected_products = [prod for prod, var in prod_vars.items() if var.get()]
    for rec in recipes:
        id_, name, ingredients, calories, cat = rec
        if selected_products:
            if not any(prod.lower() in ingredients.lower() for prod in selected_products):
                continue
        text = f"{name} — {calories} ккал\n{ingredients}"
        ctk.CTkLabel(recipes_frame, text=text, wraplength=600, justify="left", anchor="w").pack(fill="x", pady=5)

ctk.CTkButton(food_frame, text="🔍 Подобрать рецепты", command=show_recipes).pack(pady=5)
show_recipes()

# ========== ВКЛАДКА УПРАЖНЕНИЯ ==========
exercise_frame = ctk.CTkFrame(tab_exercise)
exercise_frame.pack(fill="both", expand=True)

ctk.CTkLabel(exercise_frame, text="🏋️ Упражнения", font=("Arial", 24, "bold")).pack(pady=10)

filter_frame = ctk.CTkFrame(exercise_frame)
filter_frame.pack(pady=5)
ctk.CTkLabel(filter_frame, text="Уровень:").pack(side="left", padx=5)
level_var = ctk.StringVar(value="новичок")
level_menu = ctk.CTkOptionMenu(filter_frame, values=["новичок", "средний", "профи"], variable=level_var)
level_menu.pack(side="left", padx=5)

ctk.CTkLabel(filter_frame, text="Тип:").pack(side="left", padx=5)
type_var = ctk.StringVar(value="силовое")
type_menu = ctk.CTkOptionMenu(filter_frame, values=["силовое", "для глаз", "растяжка"], variable=type_var)
type_menu.pack(side="left", padx=5)

exercise_list_frame = ctk.CTkScrollableFrame(exercise_frame, width=650, height=350)
exercise_list_frame.pack(pady=10)

def show_exercises():
    for widget in exercise_list_frame.winfo_children():
        widget.destroy()
    level = level_var.get()
    type_ = type_var.get()
    exercises = get_exercises(level=level, type_=type_)
    if not exercises:
        ctk.CTkLabel(exercise_list_frame, text="Нет упражнений с такими параметрами.").pack()
        return
    for ex in exercises:
        id_, name, desc, lvl, typ = ex
        text = f"{name} ({typ}) — {desc} [Уровень: {lvl}]"
        ctk.CTkLabel(exercise_list_frame, text=text, anchor="w", wraplength=600).pack(fill="x", pady=3)

ctk.CTkButton(exercise_frame, text="Показать упражнения", command=show_exercises).pack(pady=5)
show_exercises()

app.mainloop()