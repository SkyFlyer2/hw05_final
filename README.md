{% if False %}

# Описание проекта

Учебный проект "Социальная сеть Yatube"
Автор: SkyFlyer, telegram: @skyflyer1

Проект реализован на django 2.2.16, версия python 3.8.10.

![Главная страница проекта(__screenshots/main.png?raw=true "Title")

### Основные возможности

* Пользователи могут создавать сообщения
* Загрузка картинок
* Редактирование своих записей
* Удаление записей
* Подписки на авторов

{% endif %}

# {{ project_name|title }}

# Начало работы

Клонируйте репозиторий к себе на компьютер и перейдите в каталог проекта:

    $ git clone git@github.com/USERNAME/{{ project_name }}.git
    $ cd {{ project_name }}
    
Установите виртуальное окружение.

	$ {{ project_name }} python -m venv venv

Активируйте виртуальное окружение.

В виртуальном окружении установите зависимости:     

    $ pip install -r requirements.txt
   
Теперь можно запустить сервер разработки:   

    $ python manage.py runserver