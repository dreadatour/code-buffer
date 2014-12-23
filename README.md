## LostCode.ru

Онлайн "буфер обмена" для кода.

Just for fun (проект выходного дня).


### Установка

1. Клонируем репозиторий:

        git clone git@github.com:dreadatour/lostcode.git
        cd lostcode

2. Создаём virtualenv:

        mkvirtualenv lostcode

3. Ставим зависимости:

        pip install -r requirements.txt

4. Запускаем:

        python lostcode.py

5. Открываем в браузере: [http://127.0.0.1:5000/](http://127.0.0.1:5000/)
6. ...
7. Profit!


### Удаление старых файлов

Для удаления всех файлов старше 30 дней добавляем в крон (например, раз в сутки, ночью) следующую команду:

    find /path/to/lostcode/snippets/ -type f -mtime +30 -exec rm {} \;

### Добавление кода:

![Edit code](https://raw.githubusercontent.com/dreadatour/lostcode/master/screenshots/edit.png)


### Просмотр кода:

![View code](https://raw.githubusercontent.com/dreadatour/lostcode/master/screenshots/view.png)
