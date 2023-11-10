import os
import random
import tempfile
import time
import smtplib
import uuid
from datetime import datetime

import requests
from flask import Flask, render_template, request
import ast
import psycopg2
import bbcode
from ftplib import FTP

html_escape_table = {
    "&": "&amp;",
    '"': "&quot;",
    "'": "&apos;",
    ">": "&gt;",
    "<": "&lt;",
}
def html_escape(text):
    return "".join(html_escape_table.get(c,c) for c in text)

app = Flask(__name__)

def yandex_sendmail(email_text):
    email = "ekaterina.handorina@yandex.ru"
    password = ""
    server = smtplib.SMTP('smtp.yandex.ru', 587)
    server.ehlo()
    server.starttls()
    server.login(email, password)

    dest_email = "ekaterina.handorina@yandex.ru"
    subject = "Pokemon test"
    message = 'From: %s\nTo: %s\nSubject: %s\n\n%s' % (email, dest_email, subject, email_text)

    server.set_debuglevel(1)  # Необязательно; так будут отображаться данные с сервера в консоли
    server.sendmail(email, dest_email, message.encode("UTF-8"))
    server.quit()
    print(2)

def fetch_pokemon_data(limit=5, offset=0, search="", getrandom=0):
    results = []
    if getrandom == 1:
        data = requests.get(f"https://pokeapi.co/api/v2/pokemon?limit=100000&offset=0").json()
        results.append(random.choice(data['results']))
    elif len(search) > 1:
        data = requests.get(f"https://pokeapi.co/api/v2/pokemon?limit=100000&offset=0").json()
        results = data['results']
        results = [pokemon for pokemon in results if pokemon['name'].startswith(search)]
    else:
        url = f"https://pokeapi.co/api/v2/pokemon?limit={limit}&offset={offset}"
        response = requests.get(url)
        data = response.json()
        results = data['results']

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
    return render_template('pokemons.html', pokemon_list=pokemon_list, page=page)


@app.route('/ftpsave', methods=['GET','POST'])
def ftp_save():
    selected_pokemon_name = str(request.args.get("selected_pokemon_name"))
    selected_pokemon = fetch_pokemon_data(search=selected_pokemon_name)[0]
    selected_pokemon_stats = {
        stat: base_stat
        for stat, base_stat in selected_pokemon['stats']
    }
    saved = False

    if request.method == 'POST':
        #Создаем временную директорию для работы с временным локальным файлом
        with tempfile.TemporaryDirectory() as tmpdir:
            selected_stats = request.form.getlist('stat')
            print(selected_stats)
            #Сохраняем покемона в локальный файл чтобы потом загрузить на сервер
            filename = uuid.uuid4().hex + ".txt"
            filepath = os.path.join(tmpdir, filename)
            textpoke = ""
            textpoke = textpoke + "#" + selected_pokemon_name + "\n"
            for stat, base_stat in selected_pokemon['stats']:
                if str(stat) in selected_stats:
                    textpoke = textpoke + "*" +  str(stat) + ": " + str(base_stat) + "\n"
            text_file = open(filepath, "w+")
            n = text_file.write(textpoke)
            text_file.close()
            #Подключаемся к локальному фтп серверу
            ftp = FTP('localhost')
            ftp.login(user='poke', passwd='412244')
            dirname = datetime.today().strftime('%Y%m%d')
            #Проверяем наличие папки yyyymmdd, если не нашли - создаем
            filelist = []
            ftp.retrlines('LIST', filelist.append)
            exists = False
            for f in filelist:
                if f.split()[-1] == dirname and f.upper().startswith('D'):
                    exists = True
            if exists is False:
                ftp.mkd(dirname)
            #Входим в нашу папку yyyymmdd
            ftp.cwd(dirname)
            #Загружаем наш файл на сервер
            with open(filepath, 'rb') as file:
                ftp.storbinary('STOR ' + filename, file)
            #Удаляем временный файл
            #os.remove(filepath)
            saved = True

    return render_template(
        'save.html',
        pokemon_name=selected_pokemon_name,
        pokemon_stats=selected_pokemon_stats,
        saved=saved
    )


@app.route('/comment', methods=['GET','POST'])
def list_comments():
    if request.method == 'POST':
        pokemon_name = request.form.get("pokemon_name")
        rating = request.form.get("rating")
        comment = html_escape(str(request.form.get("editor1")))

        try:
            conn = psycopg2.connect(host="localhost", database="pokemons", user="postgres", password="412244")
            cursor = conn.cursor()
            query = f'INSERT INTO public.pokemon_comments(pokemon_name, rating, comment)' \
                    f' VALUES (%s,%s,%s)'
            cursor.execute(query,(pokemon_name, rating, comment)) #Экранирование автоматическое у параметризированного запр
            conn.commit()
        except (Exception, psycopg2.Error) as error:
            print("Ошибка подключения к PostgreSQL", error)
        finally:
            if conn:
                cursor.close()
                conn.close()

    selected_pokemon_name = str(request.args.get("selected_pokemon_name"))
    pokemon_comments = []
    try:
        conn = psycopg2.connect(host="localhost", database="pokemons", user="postgres", password="412244")
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
            print(1)
            try:
                conn = psycopg2.connect(host="localhost", database="pokemons", user="postgres", password="412244")
                cursor = conn.cursor()
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
            print(2)

            yandex_sendmail(message)
            #message = "Сообщение отправлено"
            print(3)
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
                try:
                    conn = psycopg2.connect(host="localhost", database="pokemons", user="postgres", password="412244")
                    cursor = conn.cursor()
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


if __name__ == '__main__':
    app.run()
