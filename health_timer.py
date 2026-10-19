# health_timer.py — прототип 4: питание и долголетие
import customtkinter as ctk
import time
import random
import json
import os
from datetime import date
from plyer import notification

# ── Настройки внешнего вида ──
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ── Константы ──
STATS_FILE = "stats.json"
BREAK_DURATION = 5 * 60
MEAL_INTERVAL = 4 * 60 * 60  # 4 часа для перекуса # НОВОЕ

# ── Список упражнений ──
EXERCISES = [
    "👁 Упражнение для глаз: Посмотрите вверх, вниз, влево, вправо. Повторите 5 раз.",
    "👁 Упражнение для глаз: Зажмурьтесь сильно на 3 секунды, затем откройте глаза. Повторите 5 раз.",
    "👁 Упражнение для глаз: Смотрите на кончик носа 3 секунды, затем на дальний объект за окном. Повторите 5 раз.",
    "👁 Упражнение для глаз: Вращайте глазами по кругу: 5 раз в одну сторону, 5 раз в другую.",
    "🧘 Упражнение для шеи: Медленно наклоните голову вправо, затем влево. Повторите 10 раз.",
    "🧘 Упражнение для спины: Встаньте, потянитесь руками вверх, прогнитесь назад. Подержите 5 секунд.",
    "🧘 Упражнение для спины: Сядьте прямо, сведите лопатки вместе, задержитесь на 5 секунд. Повторите 10 раз.",
    "🧘 Упражнение для шеи: Медленно поверните голову вправо до упора, затем влево. Повторите 10 раз.",
    "💪 Упражнение для кистей: Сожмите кулаки, разожмите. Повторите 15 раз.",
    "💪 Упражнение для кистей: Вращайте кистями по кругу: 10 раз в одну сторону, 10 раз в другую.",
    "💪 Упражнение для плеч: Поднимайте плечи вверх-вниз. Повторите 10 раз.",
    "💪 Упражнение для кистей: Потяните каждый палец, начиная с большого. По 3 секунды на палец.",
]

# ── Список здоровых перекусов (для долголетия) ── # НОВОЕ
SNACKS = [
    "🥜 Горсть орехов (миндаль, грецкие) и зеленое яблоко. Богато полезными жирами и клетчаткой.",
    "🥣 Греческий йогурт с горстью ягод и ложкой меда. Отличный источник белка и антиоксидантов.",
    "🥕 Овощная нарезка (морковь, огурец, болгарский перец) с хумусом. Витамины и хрустящая текстура.",
    "🥑 Половина авокадо с цельнозерновым хлебом. Полезные жиры для сердца и мозга.",
    "🥤 Протеиновый смузи (шпинат, банан, молоко). Легкий, питательный и заряжает энергией.",
    "🍇 Виноград и кусочек сыра (нежирного). Классическое сочетание для быстрого перекуса.",
]

# ── Загрузка и сохранение статистики ──
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

# ── Главное окно ──
app = ctk.CTk()
app.title("Health Timer")
app.geometry("550x600") # Увеличили высоту окна
app.resizable(False, False)

# ── Заголовок ──
title = ctk.CTkLabel(app, text="⏱ Health Timer", font=("Arial", 28, "bold"))
title.pack(pady=(10, 5))

# ── Настройка интервала ──
interval_frame = ctk.CTkFrame(app, fg_color="transparent")
interval_frame.pack(pady=5)

ctk.CTkLabel(interval_frame, text="Интервал:", font=("Arial", 14)).pack(side="left", padx=5)

interval_var = ctk.StringVar(value="1 час")
interval_menu = ctk.CTkOptionMenu(
    interval_frame,
    values=["30 минут", "1 час", "1.5 часа"],
    variable=interval_var,
    command=lambda x: reset(),
    width=120
)
interval_menu.pack(side="left", padx=5)

# ── Статус ──
status_label = ctk.CTkLabel(app, text="Готов к работе", font=("Arial", 16))
status_label.pack(pady=5)

# ── Большой таймер ──
timer_label = ctk.CTkLabel(app, text="00:00:00", font=("Courier New", 48, "bold"), text_color="#4CAF50")
timer_label.pack(pady=10)

# ── Прогресс-бар ──
progress = ctk.CTkProgressBar(app, width=400, height=15)
progress.pack(pady=5)
progress.set(0)

# ── Таймер до перекуса ── # НОВОЕ
meal_label = ctk.CTkLabel(app, text="🍏 До перекуса: 04:00:00", font=("Arial", 16), text_color="#00BCD4")
meal_label.pack(pady=5)

# ── Статистика за сегодня ──
stats = load_stats()
stats_label = ctk.CTkLabel(
    app, 
    text=f"📊 Сегодня вы работали: {stats['total_seconds'] // 60} мин.", 
    font=("Arial", 14), 
    text_color="#888"
)
stats_label.pack(pady=10)

# ── Переменные состояния ──
is_running = False
start_time = None
elapsed = 0
meal_elapsed = 0 # НОВОЕ
break_window = None
meal_window = None # НОВОЕ
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
    
    # Обновляем таймер перекуса # НОВОЕ
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
        
    # Проверка на разминку
    if elapsed >= work_interval:
        start_break()
        return
        
    # Проверка на перекус # НОВОЕ
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

    try:
        notification.notify(
            title="Health Timer",
            message=f"Вы проработали {format_time(elapsed)}. Пора размяться!",
            timeout=10
        )
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
    break_window.resizable(False, False)
    break_window.grab_set()

    ctk.CTkLabel(break_window, text="🧘 Время размяться!", font=("Arial", 24, "bold")).pack(pady=20)

    exercise_label = ctk.CTkLabel(break_window, text="", font=("Arial", 16), wraplength=550, justify="center")
    exercise_label.pack(pady=20, padx=20)

    current_exercise_index = 0
    exercise_label.configure(text=EXERCISES[current_exercise_index])

    def next_exercise():
        global current_exercise_index
        current_exercise_index = (current_exercise_index + 1) % len(EXERCISES)
        exercise_label.configure(text=EXERCISES[current_exercise_index])

    def end_break():
        global break_window
        break_window.destroy()
        break_window = None
        reset()

    btn_frame = ctk.CTkFrame(break_window, fg_color="transparent")
    btn_frame.pack(pady=10)

    ctk.CTkButton(btn_frame, text="🔄 Следующее", width=150, height=40, font=("Arial", 14), command=next_exercise).grid(row=0, column=0, padx=10)
    ctk.CTkButton(btn_frame, text="✅ Закончить перерыв", width=180, height=40, font=("Arial", 14), command=end_break).grid(row=0, column=1, padx=10)


# ── Окно перекуса ── # НОВОЕ
def show_meal_window():
    global meal_window, meal_elapsed
    if meal_window is not None and meal_window.winfo_exists():
        meal_window.focus()
        return

    meal_window = ctk.CTkToplevel(app)
    meal_window.title("Пора перекусить!")
    meal_window.geometry("600x350")
    meal_window.resizable(False, False)
    meal_window.grab_set()

    ctk.CTkLabel(meal_window, text="🍏 Время для полезного перекуса!", font=("Arial", 24, "bold"), text_color="#00BCD4").pack(pady=20)

    # Выбираем случайный перекус
    snack = random.choice(SNACKS)
    snack_label = ctk.CTkLabel(meal_window, text=snack, font=("Arial", 16), wraplength=550, justify="center")
    snack_label.pack(pady=20, padx=20)

    def close_meal():
        global meal_window, meal_elapsed
        meal_window.destroy()
        meal_window = None
        meal_elapsed = 0 # Сбрасываем таймер перекуса
        meal_label.configure(text=f"🍏 До перекуса: {format_time(MEAL_INTERVAL)}")

    ctk.CTkButton(meal_window, text="✅ Съедено, спасибо!", width=200, height=40, font=("Arial", 16), command=close_meal).pack(pady=20)


def start():
    global is_running, start_time, elapsed
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


# ── Кнопки ──
btn_frame = ctk.CTkFrame(app, fg_color="transparent")
btn_frame.pack(pady=15)

start_btn = ctk.CTkButton(btn_frame, text="▶ Старт", width=120, height=40, font=("Arial", 16), command=start)
start_btn.grid(row=0, column=0, padx=10)

pause_btn = ctk.CTkButton(btn_frame, text="⏸ Пауза", width=120, height=40, font=("Arial", 16), command=pause, state="disabled")
pause_btn.grid(row=0, column=1, padx=10)

reset_btn = ctk.CTkButton(btn_frame, text="⟲ Сброс", width=120, height=40, font=("Arial", 16), command=reset)
reset_btn.grid(row=0, column=2, padx=10)

# Кнопка "Разминка"
break_btn = ctk.CTkButton(app, text="🧘 Разминка", width=200, height=40, font=("Arial", 16), fg_color="#FF9800", hover_color="#F57C00", command=show_break_window)
break_btn.pack(pady=5)

# Кнопка "Перекусить" (для ручного вызова)
meal_btn = ctk.CTkButton(app, text="🍏 Перекусить", width=200, height=40, font=("Arial", 16), fg_color="#00BCD4", hover_color="#0097A7", command=show_meal_window)
meal_btn.pack(pady=10)

footer = ctk.CTkLabel(app, text="Модуль 8 · Прототип 4", font=("Arial", 11), text_color="#888")
footer.pack(side="bottom", pady=10)


# ── Запуск ──
if __name__ == "__main__":
    app.mainloop()