name = input("Как тебя зовут? ")
age = int(input("Сколько тебе лет? "))

if name == "Артём":
    print("Привет, создатель! 👑")
else:
    print(f"Привет, {name}!")      # ← f и {name}

# Возраст — отдельным блоком
if age < 18:
    print("Ты ещё молодой 👶")
elif age < 60:
    print("Взрослый человек 💪")
else:
    print("Мудрый возраст 🧠")