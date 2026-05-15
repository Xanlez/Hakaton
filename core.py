from gigachat import GigaChat

# Укажите ключ авторизации, полученный в личном кабинете, в интерфейсе проекта GigaChat API
with GigaChat(credentials="MDE5ZDJhNTktMzg2YS03ZDM0LThmMTUtMWIyNTM5ZDNjNzA0OjQwYjhmNjFhLWJiM2EtNGU4Ni04MzE1LTJmOWU3MjNhMTZlYQ==") as giga:
    response = giga.chat("Какие факторы влияют на стоимость страховки на дом?")
    print(response.choices[0].message.content)