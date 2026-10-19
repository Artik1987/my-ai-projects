# health_timer.py — прототип 2: с упражнениями для разминки
import customtkinter as ctk
import time
import random
from plyer import notification

# ── Настройки внешнего вида ──
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ── Константы ──
WORK_INTERVAL = 60 * 60   # 1 час в секундах (для теста можно 60)
BREAK_DURATION = 5 * 60   # 5 минут перерыва

# ── Список упражнений ──
EXERCISES = [
    # Глаза
    "👁 Упражнение для глаз: Посмотрите вверх, вниз, влево, вправо. Повторите 5 раз.",
    "👁 Упражнение для глаз: Зажмурьтесь сильно на 3 секунды, затем откройте глаза. Повторите 5 раз.",
    "👁 Упражнение для глаз: Смотрите на кончик носа 3 секунды, затем на дальний объект за окном. Повторите 5 раз.",
    "👁 Упражнение для глаз: Вращайте глазами по кругу: 5 раз в одну сторону, 5 раз в другую.",
    # Спина и шея
    "🧘 Упражнение для шеи: Медленно наклоните голову вправо, затем влево. Повторите 10 раз.",
    "🧘 Упражнение для спины: Встаньте, потянитесь руками вверх, прогнитесь назад. Подержите 5 секунд.",
    "🧘 Упражнение для спины: Сядьте прямо, сведите лопатки вместе, задержитесь на 5 секунд. Повторите 10 раз.",
    "🧘 Упражнение для шеи: Медленно поверните голову вправо до упора, затем влево. Повторите 10 раз.",
    # Кисти и плечи
    "💪 Упражнение для кистей: Сожмите кулаки, разожмите. Повторите 15 раз.",
    "💪 Упражнение для кистей: Вращайте кистями по кругу: 10 раз в одну сторону, 10 раз в другую.",
    "💪 Упражнение для плеч: Поднимайте плечи вверх-вниз. Повторите 10 раз.",
    "💪 Упражнение для кистей: Потяните каждый палец, начиная с большого. По 3 секунды на палец.",
]

# ── Главное окно ──
app = ctk.CTk()
app.title("Health Timer")
app.geometry("550x450")
app.resizable(False, False)

# ── Заголовок ──
title = ctk.CTkLabel(app, text="⏱ Health Timer", font=("Arial", 28, "bold"))
title.pack(pady=(20, 10))

# ── Статус ──
status_label = ctk.CTkLabel(app, text="Готов к работе", font=("Arial", 16))
status_label.pack(pady=5)

# ── Большой таймер ──
timer_label = ctk.CTkLabel(app, text="00:00:00", font=("Courier New", 48, "bold"), text_color="#4CAF50")
timer_label.pack(pady=20)

# ── Прогресс-бар ──
progress = ctk.CTkProgressBar(app, width=400, height=15)
progress.pack(pady=10)
progress.set(0)

# ── Переменные состояния ──
is_running = False
start_time = None
elapsed = 0
break_window = None
current_exercise_index = 0


def format_time(seconds):
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def tick():
    global elapsed
    if not is_running:
        return
    elapsed = int(time.time() - start_time)
    timer_label.configure(text=format_time(elapsed))
    p = min(elapsed / WORK_INTERVAL, 1.0)
    progress.set(p)
    if p < 0.5:
        timer_label.configure(text_color="#4CAF50")
    elif p < 0.8:
        timer_label.configure(text_color="#FFC107")
    else:
        timer_label.configure(text_color="#F44336")
    if elapsed >= WORK_INTERVAL:
        start_break()
        return
    app.after(1000, tick)


def start_break():
    """Запускает перерыв: показывает уведомление и окно с упражнениями."""
    global is_running, break_window
    is_running = False
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
    """Открывает окно с упражнениями."""
    global break_window, current_exercise_index
    if break_window is not None and break_window.winfo_exists():
        break_window.focus()
        return

    break_window = ctk.CTkToplevel(app)
    break_window.title("Разминка")
    break_window.geometry("600x400")
    break_window.resizable(False, False)
    break_window.grab_set()  # блокирует главное окно

    ctk.CTkLabel(
        break_window,
        text="🧘 Время размяться!",
        font=("Arial", 24, "bold")
    ).pack(pady=20)

    exercise_label = ctk.CTkLabel(
        break_window,
        text="",
        font=("Arial", 16),
        wraplength=550,
        justify="center"
    )
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

    ctk.CTkButton(
        btn_frame, text="🔄 Следующее", width=150, height=40,
        font=("Arial", 14), command=next_exercise
    ).grid(row=0, column=0, padx=10)

    ctk.CTkButton(
        btn_frame, text="✅ Закончить перерыв", width=180, height=40,
        font=("Arial", 14), command=end_break
    ).grid(row=0, column=1, padx=10)


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
    global is_running, elapsed, start_time
    is_running = False
    elapsed = 0
    start_time = None
    timer_label.configure(text="00:00:00", text_color="#4CAF50")
    status_label.configure(text="Готов к работе", text_color="white")
    progress.set(0)
    start_btn.configure(state="normal")
    pause_btn.configure(state="disabled")
    reset_btn.configure(state="normal")


# ── Кнопки ──
btn_frame = ctk.CTkFrame(app, fg_color="transparent")
btn_frame.pack(pady=20)

start_btn = ctk.CTkButton(btn_frame, text="▶ Старт", width=120, height=40, font=("Arial", 16), command=start)
start_btn.grid(row=0, column=0, padx=10)

pause_btn = ctk.CTkButton(btn_frame, text="⏸ Пауза", width=120, height=40, font=("Arial", 16), command=pause, state="disabled")
pause_btn.grid(row=0, column=1, padx=10)

reset_btn = ctk.CTkButton(btn_frame, text="⟲ Сброс", width=120, height=40, font=("Arial", 16), command=reset)
reset_btn.grid(row=0, column=2, padx=10)

# ── Кнопка "Разминка" (открыть окно с упражнениями вручную) ──
break_btn = ctk.CTkButton(
    app, text="🧘 Разминка", width=200, height=40,
    font=("Arial", 16), fg_color="#FF9800", hover_color="#F57C00",
    command=show_break_window
)
break_btn.pack(pady=10)

# ── Подпись ──
footer = ctk.CTkLabel(app, text="Модуль 8 · Прототип 2", font=("Arial", 11), text_color="#888")
footer.pack(side="bottom", pady=10)


# ── Запуск ──
if __name__ == "__main__":
    app.mainloop()