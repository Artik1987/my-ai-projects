import random

secret = random.randint(1,100)
attempts = 0
print("Я загадал число от 1 до 100.Попробуй угадать!")

while True:
    guess = int(input("Твоё число: "))
    attempts = attempts + 1

    if guess < secret:
        print("Больше ⬆️")
    elif guess > secret:
        print("Меньше ⬇️")
    else:
        print(f"🎉 Угадал! Число было {secret}")
        print(f"Ты потратил попыток: {attempts}")
        break

if attempts < 5:
    print("Ты мега мозг 🏆")
elif attempts < 10:
    print("Молодец так держать 👍")
else:
    print("Дружище включай голову 😅")        