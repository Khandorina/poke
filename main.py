import os
import pickle
import random
import tempfile
import time
import smtplib
import uuid
from datetime import datetime
from urllib.parse import urlencode
from requests import post
import redis
import requests
from flask import Flask, render_template, request, jsonify, redirect, session, url_for
import ast
import psycopg2
import bbcode
from ftplib import FTP
from flask_session import Session
import argon2

CLIENTID=os.getenv('CLIENTID', '')
CLIENTSECRET=os.getenv('CLIENTSECRET', '')
SMTPLOGIN=os.getenv('SMTPLOGIN', '')
SMTPPASS=os.getenv('SMTPPASS', '')
FTPLOGIN=os.getenv('FTPLOGIN', '')
FTPPASS=os.getenv('FTPPASS', '')
DBUSER=os.getenv('DBUSER', '')
DBPASS=os.getenv('DBPASS', '')
dbhost = "host.docker.internal" # подключение по адресу хоста из докера, порт везде стандартный
PGHOST=os.getenv('PGHOST', dbhost)
RDHOST=os.getenv('RDHOST', dbhost)

cacheserver = redis.Redis(RDHOST, 6379, 0)

html_escape_table = {
    "&": "&amp;",
    '"': "&quot;",
    "'": "&apos;",
    ">": "&gt;",
    "<": "&lt;",
}


def html_escape(text):
    return "".join(html_escape_table.get(c, c) for c in text)


app = Flask(__name__)
SESSION_TYPE = 'redis'
SESSION_REDIS = cacheserver
app.config.from_object(__name__)
sess = Session(app)


def yandex_sendmail(email_text, dest=SMTPLOGIN):
    if SMTPLOGIN != '' and SMTPPASS != '':
        # Заменить на email = 1 password = 2 для встроенных логина и пароля от почты
        email = SMTPLOGIN
        password = SMTPPASS

        server = smtplib.SMTP('smtp.yandex.ru', 587)
        server.ehlo()
        server.starttls()
        server.login(email, password)

        dest_email = dest
        subject = "Pokemon test"
        message = 'From: %s\nTo: %s\nSubject: %s\n\n%s' % (email, dest_email, subject, email_text)

        server.set_debuglevel(1)  # Необязательно; так будут отображаться данные с сервера в консоли
        server.sendmail(email, dest_email, message.encode("UTF-8"))
        server.quit()


def fetch_pokemon_data(limit=5, offset=0, search="", getrandom=0):
    results = []
    if getrandom == 1:
        data = requests.get(f"https://pokeapi.co/api/v2/pokemon?limit=100000&offset=0").json()
        results.append(random.choice(data['results']))
    elif len(search) > 1:
        rediskey = "s" + str(search)
        if cacheserver.exists(rediskey):
            results = pickle.loads(cacheserver.get(rediskey))
            print("load results from cache")
        else:
            data = requests.get(f"https://pokeapi.co/api/v2/pokemon?limit=100000&offset=0").json()
            results = data['results']
            results = [pokemon for pokemon in results if pokemon['name'].startswith(search)]
            cacheserver.set(rediskey, pickle.dumps(results))
            print("saved results to cache")
    else:
        rediskey = str(offset) + "x" + str(limit)
        if cacheserver.exists(rediskey):
            results = pickle.loads(cacheserver.get(rediskey))
            print("load results from cache")
        else:
            url = f"https://pokeapi.co/api/v2/pokemon?limit={limit}&offset={offset}"
            response = requests.get(url)
            data = response.json()
            results = data['results']
            cacheserver.set(rediskey, pickle.dumps(results))  # сохраняем в кеш
            print("saved results to cache")

    pokemon_list = []
    for result in results:
        pokemon_url = result['url']
        pokemon_response = requests.get(pokemon_url)
        pokemon_data = pokemon_response.json()
        stats = [(stat['stat']['name'], stat['base_stat']) for stat in pokemon_data['stats']]
        forms_url = pokemon_data['forms'][0]['url']
        forms_response = requests.get(forms_url)
        forms_data = forms_response.json()
        image_url = forms_data['sprites']['front_default']
        pokemon_list.append({
            'name': result['name'],
            'stats': stats,
            'image_url': image_url
        })
    return pokemon_list


@app.route('/', methods=['GET'])
def list_pokemons():
    search = request.args.get('search', '')
    page = int(request.args.get('page', 1))
    limit = 5
    offset = (page - 1) * limit
    pokemon_list = fetch_pokemon_data(limit, offset, search)
    api = request.args.get('api', default=0, type=int)
    if api == 1:
        return pokemon_list
    else:
        username = ""
        if 'username' in session:
            username = session['username']
        return render_template('pokemons.html', pokemon_list=pokemon_list, page=page, username=username)


@app.route('/ftpsave', methods=['GET', 'POST'])
def ftp_save():
    selected_pokemon_name = str(request.args.get("selected_pokemon_name"))
    selected_pokemon = fetch_pokemon_data(search=selected_pokemon_name)[0]
    selected_pokemon_stats = {
        stat: base_stat
        for stat, base_stat in selected_pokemon['stats']
    }
    saved = False

    if request.method == 'POST':
        # Создаем временную директорию для работы с временным локальным файлом
        with tempfile.TemporaryDirectory() as tmpdir:
            selected_stats = request.form.getlist('stat')
            # Сохраняем покемона в локальный файл чтобы потом загрузить на сервер
            filename = uuid.uuid4().hex + ".txt"
            filepath = os.path.join(tmpdir, filename)
            textpoke = ""
            textpoke = textpoke + "#" + selected_pokemon_name + "\n"
            for stat, base_stat in selected_pokemon['stats']:
                if str(stat) in selected_stats:
                    textpoke = textpoke + "*" + str(stat) + ": " + str(base_stat) + "\n"
            text_file = open(filepath, "w+")
            text_file.write(textpoke)
            text_file.close()
            if FTPLOGIN != '' and FTPPASS != '':
                # Подключаемся к локальному фтп серверу
                ftp = FTP(dbhost)
                ftp.login(user=FTPLOGIN, passwd=FTPPASS)  # вынести логин и пароль в контейнер докера
                dirname = datetime.today().strftime('%Y%m%d')
                # Проверяем наличие папки yyyymmdd, если не нашли - создаем
                filelist = []
                ftp.retrlines('LIST', filelist.append)
                exists = False
                for f in filelist:
                    if f.split()[-1] == dirname and f.upper().startswith('D'):
                        exists = True
                if exists is False:
                    ftp.mkd(dirname)
                # Входим в нашу папку yyyymmdd
                ftp.cwd(dirname)
                # Загружаем наш файл на сервер
                with open(filepath, 'rb') as file:
                    ftp.storbinary('STOR ' + filename, file)
                # Удаляем временный файл
                # os.remove(filepath)
                saved = True

    return render_template(
        'save.html',
        pokemon_name=selected_pokemon_name,
        pokemon_stats=selected_pokemon_stats,
        saved=saved
    )


@app.route('/comment', methods=['GET', 'POST'])
def list_comments():
    if request.method == 'POST':
        pokemon_name = request.form.get("pokemon_name")
        rating = request.form.get("rating")
        comment = html_escape(str(request.form.get("editor1")))

        if DBUSER != '' and DBPASS != '':
            try:
                conn = psycopg2.connect(host=PGHOST, database="pokemons", user="postgres", password="412244")
                cursor = conn.cursor()
                query = f'INSERT INTO public.pokemon_comments(pokemon_name, rating, comment)' \
                        f' VALUES (%s,%s,%s)'
                cursor.execute(query,
                               (pokemon_name, rating, comment))  # Экранирование автоматическое у параметризированного запр
                conn.commit()
            except (Exception, psycopg2.Error) as error:
                print("Ошибка подключения к PostgreSQL", error)
            finally:
                if conn:
                    cursor.close()
                    conn.close()

    selected_pokemon_name = str(request.args.get("selected_pokemon_name"))
    pokemon_comments = []
    if DBUSER != '' and DBPASS != '':
        try:
            conn = psycopg2.connect(host=PGHOST, database="pokemons", user=DBUSER, password=DBPASS)
            cursor = conn.cursor()
            query = "SELECT * FROM public.pokemon_comments WHERE pokemon_name = %s"
            cursor.execute(query, (selected_pokemon_name,))

            pokemon_comments_bb = cursor.fetchall()
            for comment_bb in pokemon_comments_bb:
                pokemon_comments.append([comment_bb[2], bbcode.render_html(comment_bb[3])])
            conn.commit()
        except (Exception, psycopg2.Error) as error:
            print("Ошибка подключения к PostgreSQL", error)
        finally:
            if conn:
                cursor.close()
                conn.close()
    return render_template(
        'comment.html',
        pokemon_name=selected_pokemon_name,
        pokemon_comments=pokemon_comments
    )


@app.route('/battle', methods=['POST', 'GET'])
def pokemon_battle():
    battlefinished = 0;
    if request.method == 'POST':
        quickbattle = int(request.form.get('quickbattle'))
        rounds = int(request.form.get('rounds')) + 1
        selected_pokemon = ast.literal_eval(request.form.get('selected_pokemon'))
        target_pokemon = ast.literal_eval(request.form.get('target_pokemon'))
        selected_pokemon_hp = request.form.get('selected_pokemon_hp')
        target_pokemon_hp = request.form.get('target_pokemon_hp')
        selected_pokemon_stats = {
            stat: base_stat
            for stat, base_stat in selected_pokemon['stats']
        }
        target_pokemon_stats = {
            stat: base_stat
            for stat, base_stat in target_pokemon['stats']
        }
        if quickbattle == 1:
            while min(float(selected_pokemon_hp), float(target_pokemon_hp)) > 0.01:
                if random.choice([0, 1]) == 0:
                    damage = 15 * target_pokemon_stats['attack'] / selected_pokemon_stats['defense']
                    selected_pokemon_hp = float(selected_pokemon_hp) - damage
                else:
                    damage = 15 * selected_pokemon_stats['attack'] / target_pokemon_stats['defense']
                    target_pokemon_hp = float(selected_pokemon_hp) - damage
            winner = 0
            if float(selected_pokemon_hp) < float(target_pokemon_hp):
                message = "Битва окончена! Победитель: " + target_pokemon['name']
                winner = 1
            else:
                message = "Битва окончена! Победитель: " + selected_pokemon['name']
            battlefinished = 1
            if DBUSER != '' and DBPASS != '':
                try:
                    conn = psycopg2.connect(host=PGHOST, database="pokemons", user=DBUSER, password=DBPASS)
                    cursor = conn.cursor()
                    if 'username' in session:
                        query = f'INSERT INTO public.battle_history(date, pokemon1, pokemon2, winner, rounds, username)' \
                                f' VALUES {tuple([time.time(), selected_pokemon["name"], target_pokemon["name"], winner, rounds, session["username"]])}'
                    else:
                        query = f'INSERT INTO public.battle_history(date, pokemon1, pokemon2, winner, rounds)' \
                                f' VALUES {tuple([time.time(), selected_pokemon["name"], target_pokemon["name"], winner, rounds])}'
                    cursor.execute(query)
                    conn.commit()
                except (Exception, psycopg2.Error) as error:
                    print("Ошибка подключения к PostgreSQL", error)
                finally:
                    if conn:
                        cursor.close()
                        conn.close()
            yandex_sendmail(message)
        else:
            if random.choice([0, 1]) == 0:
                damage = 15 * target_pokemon_stats['attack'] / selected_pokemon_stats['defense']
                selected_pokemon_hp = float(selected_pokemon_hp) - damage
                message = target_pokemon['name'] + " атакует " + selected_pokemon['name'] + " нанося " + str(
                    damage) + " урона!"
            else:
                damage = 15 * selected_pokemon_stats['attack'] / target_pokemon_stats['defense']
                target_pokemon_hp = float(selected_pokemon_hp) - damage
                message = selected_pokemon['name'] + " атакует " + target_pokemon['name'] + " нанося " + str(
                    damage) + " урона!"
            if min(float(selected_pokemon_hp), float(target_pokemon_hp)) <= 0.01:
                winner = 0
                if float(selected_pokemon_hp) < float(target_pokemon_hp):
                    message = "Битва окончена! Победитель: " + target_pokemon['name']
                    winner = 1
                else:
                    message = "Битва окончена! Победитель: " + selected_pokemon['name']
                battlefinished = 1
                if DBUSER != '' and DBPASS != '':
                    try:
                        conn = psycopg2.connect(host=PGHOST, database="pokemons", user=DBUSER, password=DBPASS)
                        cursor = conn.cursor()
                        if 'username' in session:
                            query = f'INSERT INTO public.battle_history(date, pokemon1, pokemon2, winner, rounds, username)' \
                                    f' VALUES {tuple([time.time(), selected_pokemon["name"], target_pokemon["name"], winner, rounds, session["username"]])}'
                        else:
                            query = f'INSERT INTO public.battle_history(date, pokemon1, pokemon2, winner, rounds)' \
                                    f' VALUES {tuple([time.time(), selected_pokemon["name"], target_pokemon["name"], winner, rounds])}'
                        cursor.execute(query)
                        conn.commit()
                    except (Exception, psycopg2.Error) as error:
                        print("Ошибка подключения к PostgreSQL", error)
                    finally:
                        if conn:
                            cursor.close()
                            conn.close()

    else:
        rounds = 0
        target_pokemon = fetch_pokemon_data(getrandom=1)[0]
        selected_pokemon = fetch_pokemon_data(getrandom=1)[0]
        new = request.args.get("new")
        if new is None:
            selected_pokemon_name = str(request.args.get("selected_pokemon_name"))
            selected_pokemon = fetch_pokemon_data(search=selected_pokemon_name)[0]
        selected_pokemon_stats = {
            stat: base_stat
            for stat, base_stat in selected_pokemon['stats']
        }
        target_pokemon_stats = {
            stat: base_stat
            for stat, base_stat in target_pokemon['stats']
        }
        selected_pokemon_hp = selected_pokemon_stats['hp']
        target_pokemon_hp = target_pokemon_stats['hp']
        message = "В битве столкнулись " + selected_pokemon['name'] + " и " + target_pokemon['name'];

    print(target_pokemon)
    print(selected_pokemon)
    return render_template(
        'battle.html',
        selected_pokemon=selected_pokemon,
        selected_pokemon_hp=selected_pokemon_hp,
        target_pokemon=target_pokemon,
        target_pokemon_hp=target_pokemon_hp,
        message=message,
        battlefinished=battlefinished,
        rounds=rounds
    )


@app.route('/verification_code')
def verification_code():
    if 'username' in session or CLIENTID == '' or CLIENTSECRET == '':
        return redirect(url_for('list_pokemons'))
    else:
        if request.args.get('code', False):
            # После того как пользователь авторизуется на странице яндекса его перекинет обратно с кодом авторизации
            # Мы должны получить из этого кода токен авторизации для нашего приложения
            data = {
                'grant_type': 'authorization_code',
                'code': request.args.get('code'),
                'client_id': CLIENTID,
                'client_secret': CLIENTSECRET
            }
            data = urlencode(data)
            oauthjson = post('https://oauth.yandex.ru/' + "token", data).json()
            userinfo = requests.get('https://login.yandex.ru/info',
                                    headers={'Authorization': 'OAuth ' + oauthjson['access_token']}).json()

            if DBUSER != '' and DBPASS != '':
                try:
                    conn = psycopg2.connect(host=PGHOST, database="pokemons", user=DBUSER, password=DBPASS)
                    cursor = conn.cursor()
                    query = f'INSERT INTO public.pokemon_users(email)' \
                            f' VALUES (\'{userinfo["default_email"]}\')' \
                            f' ON CONFLICT (email) DO NOTHING;'
                    cursor.execute(query)
                    conn.commit()
                    session['username'] = userinfo['default_email']
                except (Exception, psycopg2.Error) as error:
                    print("Ошибка подключения к PostgreSQL", error)
                finally:
                    if conn:
                        cursor.close()
                        conn.close()
            return redirect(url_for('list_pokemons'))
        else:
            # Если скрипт был вызван без указания параметра "code",
            # то пользователь перенаправляется на страницу запроса доступа
            return redirect('https://oauth.yandex.ru/' + "authorize?response_type=code&client_id={}".format(CLIENTID))


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('list_pokemons'))


@app.route('/register', methods=['POST', 'GET'])
def register():
    if request.method == 'POST' and DBUSER != '' and DBPASS != '':
        login = request.form.get('login')

        try:
            conn = psycopg2.connect(host=PGHOST, database="pokemons", user=DBUSER, password=DBPASS)
            cursor = conn.cursor()
            query = "SELECT COUNT(*) FROM public.pokemon_users WHERE email = %s"
            cursor.execute(query, (login,))

            user_exists = cursor.fetchone()[0]
            print(user_exists)
            conn.commit()
        except (Exception, psycopg2.Error) as error:
            print("Ошибка подключения к PostgreSQL", error)
        finally:
            if conn:
                cursor.close()
                conn.close()
        if user_exists == 1:
            return render_template('register.html', error="Пользователь с таким именем существует")
        password = request.form.get('password')
        password = argon2.hash_password(str.encode(password)).decode()
        print(password)
        try:
            conn = psycopg2.connect(host=PGHOST, database="pokemons", user=DBUSER, password=DBPASS)
            cursor = conn.cursor()
            query = f'INSERT INTO public.pokemon_users(email,password)' \
                    f' VALUES {tuple([login, password])}'
            cursor.execute(query)
            conn.commit()
            session['username'] = login
        except (Exception, psycopg2.Error) as error:
            print("Ошибка подключения к PostgreSQL", error)
        finally:
            if conn:
                cursor.close()
                conn.close()

        return redirect(url_for('list_pokemons'))
    else:
        return render_template('register.html')


@app.route('/login', methods=['POST', 'GET'])
def login():
    if request.method == 'POST' and DBUSER != '' and DBPASS != '':
        lostpasscode = request.form.get('lostpasscode', '')
        if lostpasscode == '':
            username = request.form.get('login', '')
            password = request.form.get('password', '')
            if username == '' or password == '':
                return render_template('login.html', error="Неверный логин или пароль")

            #Берем пароль пользователя и сверяем с полученным
            user_password = ""
            try:
                conn = psycopg2.connect(host=PGHOST, database="pokemons", user=DBUSER, password=DBPASS)
                cursor = conn.cursor()
                query = "SELECT password FROM public.pokemon_users WHERE email = %s"
                cursor.execute(query, (username,))
                if cursor.rowcount < 1:
                    return render_template('login.html', error="Неверный логин или пароль")

                user_password = cursor.fetchone()[0]
                print(user_password)
                conn.commit()
            except (Exception, psycopg2.Error) as error:
                print("Ошибка подключения к PostgreSQL", error)
            finally:
                if conn:
                    cursor.close()
                    conn.close()
            try:
                argon2.verify_password(str.encode(user_password), str.encode(password))
            except argon2.exceptions.Argon2Error as err:
                return render_template('login.html', error="Неверный логин или пароль")
            #Если пароль верный то создаем код, сохраняем его в базе и отправляем на почту пользователя
            #Код
            secretcode = random.randint(100000, 999999)
            #Сохраняем в базе
            try:
                conn = psycopg2.connect(host=PGHOST, database="pokemons", user=DBUSER, password=DBPASS)
                cursor = conn.cursor()
                query = f'UPDATE public.pokemon_users' \
                        f' SET lostpasscode = \'{secretcode}\'' \
                        f' WHERE email = \'{username}\';'
                cursor.execute(query)
                conn.commit()
            except (Exception, psycopg2.Error) as error:
                print("Ошибка подключения к PostgreSQL", error)
            finally:
                if conn:
                    cursor.close()
                    conn.close()
            #Отправляем письмо, проверив что почта есть в базе
            user_email = ""
            try:
                conn = psycopg2.connect(host=PGHOST, database="pokemons", user=DBUSER, password=DBPASS)
                cursor = conn.cursor()
                query = "SELECT email FROM public.pokemon_users WHERE email = %s"
                cursor.execute(query, (username,))
                if cursor.rowcount > 0:
                    user_email = cursor.fetchone()[0]
                conn.commit()
            except (Exception, psycopg2.Error) as error:
                print("Ошибка подключения к PostgreSQL", error)
            finally:
                if conn:
                    cursor.close()
                    conn.close()

            if user_email != "":
                yandex_sendmail("Тест 2fa, код " + str(secretcode), user_email)

            return render_template('login2fa.html', username=username, password=password)
        else:
            username = request.form.get('login', '')
            password = request.form.get('password', '')
            if username == '' or password == '':
                return render_template('login.html', error="Неверный логин или пароль")

            #Берем пароль пользователя, там где код и почта равны присланым и сверяем с полученным
            user_password = ""
            try:
                conn = psycopg2.connect(host=PGHOST, database="pokemons", user=DBUSER, password=DBPASS)
                cursor = conn.cursor()
                query = "SELECT password FROM public.pokemon_users WHERE email = %s AND lostpasscode = %s"
                cursor.execute(query, (username,lostpasscode,))
                if cursor.rowcount < 1:
                    return render_template('login2fa.html',username=username,password=password, error="Неверный код 2fa")

                user_password = cursor.fetchone()[0]
                print(user_password)
                conn.commit()
            except (Exception, psycopg2.Error) as error:
                print("Ошибка подключения к PostgreSQL", error)
            finally:
                if conn:
                    cursor.close()
                    conn.close()
            try:
                argon2.verify_password(str.encode(user_password), str.encode(password))
            except argon2.exceptions.Argon2Error as err:
                return render_template('login.html', error="Неверный логин или пароль")
            session['username']=username
            return redirect(url_for('list_pokemons'))
    else:
        return render_template('login.html')


@app.route('/lostpass', methods=['POST', 'GET'])
def lostpass():
    if request.method == 'POST' and DBUSER != '' and DBPASS != '':
        username = request.form.get('login', "")
        if username == "":
            return render_template('lostpass.html')
        lostpasscode = request.form.get('lostpasscode', "")
        if lostpasscode == "":
            user_email=""
            try:
                conn = psycopg2.connect(host=PGHOST, database="pokemons", user=DBUSER, password=DBPASS)
                cursor = conn.cursor()
                query = "SELECT email FROM public.pokemon_users WHERE email = %s"
                cursor.execute(query, (username,))
                if cursor.rowcount > 0:
                    user_email = cursor.fetchone()[0]
                conn.commit()
            except (Exception, psycopg2.Error) as error:
                print("Ошибка подключения к PostgreSQL", error)
            finally:
                if conn:
                    cursor.close()
                    conn.close()

            secretcode = random.randint(100000, 999999)

            try:
                conn = psycopg2.connect(host=PGHOST, database="pokemons", user=DBUSER, password=DBPASS)
                cursor = conn.cursor()
                query = f'UPDATE public.pokemon_users' \
                        f' SET lostpasscode = \'{secretcode}\'' \
                        f' WHERE email = \'{username}\';'
                cursor.execute(query)
                conn.commit()
            except (Exception, psycopg2.Error) as error:
                print("Ошибка подключения к PostgreSQL", error)
            finally:
                if conn:
                    cursor.close()
                    conn.close()

            if user_email != "":
                yandex_sendmail("Тест восстановления пароля, код " + str(secretcode), user_email)
            return render_template('changepass.html', username = username)
        else:
            password = request.form.get('password', "")
            if password == "":
                return render_template('changepass.html', username = username, error ="Поле пароля не должно быть пустым")

            password = argon2.hash_password(str.encode(password)).decode()

            try:
                conn = psycopg2.connect(host=PGHOST, database="pokemons", user=DBUSER, password=DBPASS)
                cursor = conn.cursor()
                query = "SELECT email FROM public.pokemon_users WHERE email = %s AND lostpasscode = %s"
                cursor.execute(query, (username,lostpasscode,))
                if cursor.rowcount < 1:
                    return render_template('changepass.html', username = username, error ="Неверный код восстановления пароля")
                conn.commit()
            except (Exception, psycopg2.Error) as error:
                print("Ошибка подключения к PostgreSQL", error)
            finally:
                if conn:
                    cursor.close()
                    conn.close()
            try:
                conn = psycopg2.connect(host=PGHOST, database="pokemons", user=DBUSER, password=DBPASS)
                cursor = conn.cursor()
                query = f'UPDATE public.pokemon_users SET password = \'{password}\' WHERE email = \'{username}\' AND lostpasscode = \'{lostpasscode}\';'
                print(query)
                cursor.execute(query)
                conn.commit()
            except (Exception, psycopg2.Error) as error:
                print("Ошибка подключения к PostgreSQL", error)
            finally:
                if conn:
                    cursor.close()
                    conn.close()
            return render_template('changepass.html', username = username, error="Пароль успешно изменен")
    else:
        return render_template('lostpass.html')


if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0')
