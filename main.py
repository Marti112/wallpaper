import json
import random
import re
import socket
import time
from threading import Thread
from urllib.parse import quote
from urllib.request import urlopen

import requests
import telebot
from bs4 import BeautifulSoup
from gevent.pywsgi import WSGIServer
from requests import Session
from telebot import types
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup

TELEGRAM_TOKEN = "1047067706:AAFvpf-GpABTx0OiLfQejpne8lBdCih6-Jk"
bot = telebot.TeleBot(TELEGRAM_TOKEN)
RESULT_NUMBER = 5
# V_SERVER_IP = "172.17.207.112"
V_SERVER_IP = ""


from flask import Flask, request, jsonify

app = Flask(__name__)


@app.route("/", methods=["GET"])
def index():
    return "Hello", 200


@app.route("/online", methods=["POST"])
def ping():
    if request.method == 'POST':
        ip = request.json['ip']
        if ip not in ONLINE.values():
            ONLINE[len(ONLINE)] = ip
        return jsonify({"status": "OK"}), 200


def start_server(app_, port):
    srv = WSGIServer(('0.0.0.0', port), app_, log=None)
    # srv = WSGIServer(('172.17.207.112', port), app_, log=None)
    srv.serve_forever()


def change(image, server_ip):
    url = f'http://{server_ip}:5678/image'
    if not server_ip:
        return
    print(server_ip)
    # files = {'media': open('3.jpg', 'rb')}
    image_file = image[0]
    files = {'media': image_file}
    try:
        res = requests.post(url, files=files)
    except Exception as e:
        raise
        return f"Error {e}"
    else:
        return res.json()["status"]


def send_with_rerun(func, *args, **kwargs):
    for i in range(5):
        try:
            # bot.send_message(*args, **kwargs)
            func(*args, **kwargs)
        except Exception as e:
            print(e)
            time.sleep(1)
        else:
            break


def get_image_urls(word):
    # text = quote(f"{word} full hd")
    text = quote(f"{word}")
    y_search = f"https://yandex.ru/images/search/?text={text}"

    session = Session()
    response = session.get(y_search)
    soup = BeautifulSoup(response.content, features="html.parser")
    parsed = soup.find_all("div", {"class": "serp-item"})
    iter_num = (len(parsed) - 1) & RESULT_NUMBER
    result = []
    for i in range(iter_num):
        result.append(json.loads(parsed[random.randint(0, len(parsed) - 1)]['data-bem'])["serp-item"]["preview"][0]["url"])
    session.close()
    return result


@bot.message_handler(commands=['help', 'start'])
def send_welcome(message):
    # msg = bot.reply_to(message, """Hi there, I am Test runner bot.""")
    msg = """Hi there, I am remote wallpaper changer bot.\nAvailable commands:"""
    send_with_rerun(bot.send_message, message.chat.id, msg)
    cmds = """/categories - for getting list of all available image categories\n/add new category - for adding new category\n/menu - for manage."""
    # bot.send_message(message.chat.id, cmds)
    send_with_rerun(bot.send_message, message.chat.id, cmds)


def get_image(url, images, idx):
    try:
        images.append((urlopen(url).read(), idx))
    except Exception:
        pass


def get_images(category):
    tasks = []
    images = []

    for idx, url in enumerate(get_image_urls(category), 1):
        # task = Thread(target=send_image, args=(call.message.chat.id, urlopen(url).read(), idx))
        task = Thread(target=get_image, args=(url, images, idx))
        task.start()
        tasks.append(task)
    for task in tasks:
        task.join()
    return images


def vote(variants):
    s = ""
    all_votes = sum(list(map(int, variants.values())))
    for idx, value in variants.items():
        s = f"{s}\n{idx} {f'- {value}' if value != 0 else ''}\n{f'{ round(100 * int(value) / all_votes) }%' if all_votes else ''}"
    print(repr(s), 44444444)
    return f"Vote:{s} "


im = None


@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    global im

    variants = {}
    if not call.data.startswith("select"):
        category = call.data
        bot.answer_callback_query(call.id, f"Some variants for {category}")

        images = get_images(category)

        im = images[:]

        for image, idx in images:
            send_with_rerun(bot.send_photo, call.message.chat.id, image, caption=idx)

        keyboard = telebot.types.InlineKeyboardMarkup(row_width=5)
        for i, variant in enumerate(range(1, RESULT_NUMBER + 1), 1):
            variants[i] = 0
            keyboard.add(InlineKeyboardButton(f"Variant {variant}: 0", callback_data=f"select-{variant}"))

        send_with_rerun(bot.send_message, call.message.chat.id, vote(variants), reply_markup=keyboard)

    else:
        voted = int(call.data.split("-")[1])
        send_with_rerun(bot.answer_callback_query, call.id, f"You voted for {voted}")
        change(im[voted], V_SERVER_IP)

        j = call.message.json["reply_markup"]
        for find in re.findall(r"(\d+)(( - )?(\d+))?", call.message.json["text"]):
            if find[0] == str(voted):
                cur_val = find[-1]
                print(f"cur_v: '{cur_val}'")
                print(voted)
                variants[str(voted)] = 1 + (int(cur_val) if cur_val else 0)
            else:
                if int(find[0]) in list(range(1, RESULT_NUMBER)):
                    variants[find[0]] = (find[-1] or 0)

        kb = j["inline_keyboard"]

        for button in kb:
            b = button[0]
            if call.data == b["callback_data"]:
                text = b["text"]
                cur_val = re.match("Variant (\d+): (\d+)", text).group(2)
                b["text"] = "Variant {}: {}".format(voted, int(cur_val) + 1)

        keyboard = telebot.types.InlineKeyboardMarkup(row_width=5)
        for button in kb:
            b = button[0]
            keyboard.add(InlineKeyboardButton(b["text"], callback_data=b["callback_data"]))

        send_with_rerun(bot.edit_message_text, vote(variants), call.message.chat.id, call.message.message_id, reply_markup=InlineKeyboardMarkup(keyboard))
        send_with_rerun(bot.edit_message_reply_markup, call.message.chat.id, call.message.message_id, reply_markup=keyboard)


@bot.message_handler(commands=['search'])
def message_handler(message):
    search = message.text.split("/search ")
    if len(search) >= 2:
        category = " ".join(search[1:])
        images = get_images(category)
        for image, idx in images:
            send_with_rerun(bot.send_photo, message.chat.id, image)


@bot.message_handler(commands=['categories'])
def message_handler(message):
    markup = InlineKeyboardMarkup()
    markup.row_width = 1
    markup.add(*[InlineKeyboardButton(f"{categorie}", callback_data=f"{categorie[:30]}") for categorie, id_ in CategoryData.items()])

    bot.send_message(message.chat.id, "All categories:", reply_markup=markup)


@bot.message_handler(commands=['add'])
def url(message):
    new = message.text.split("/add ")
    if len(new) >= 2:
        new_category = " ".join(new[1:])
        CategoryData[new_category] = len(CategoryData)
        send_with_rerun(bot.send_message, message.chat.id, f"New item {new_category} added.\nCheck in /categories")
    else:
        send_with_rerun(bot.send_message, message.chat.id, "Incorrect input format.\nValid format:\n/add new category")


@bot.message_handler(commands=['clear', 'clean'])
def url(message):
    global CategoryData
    CategoryData = {}
    # bot.send_message(message.chat.id, f"Categories clean.")
    send_with_rerun(bot.send_message, message.chat.id, f"Categories clean.")


@bot.message_handler(commands=['online'])
def url(message):
    global ONLINE
    send_with_rerun(bot.send_message, message.chat.id, "\n".join(ONLINE.values()))


@bot.message_handler(commands=['menu'])
def message_handler(message):
    markup = ReplyKeyboardMarkup(True, True)
    markup.row("/categories")
    markup.row("/add", "/remove")
    markup.row("/online")
    send_with_rerun(bot.send_message, message.chat.id, "menu", reply_markup=markup)


@bot.inline_handler(lambda query: query.query == 'online')
def query_text(inline_query):
    try:
        o = []
        for idx, online in ONLINE.items():
            o.append(types.InlineQueryResultArticle(idx, online, types.InputTextMessageContent(f"Set wallpaper for {online}")))
        bot.answer_inline_query(inline_query.id, o)
    except Exception as e:
        print(e)


@bot.chosen_inline_handler(func=lambda chosen_inline_result: True)
def test_chosen(chosen_inline_result):
    global V_SERVER_IP
    print(chosen_inline_result.result_id)
    V_SERVER_IP = ONLINE.get(int(chosen_inline_result.result_id))
    print(V_SERVER_IP)


@bot.message_handler(commands=['m'])
def menu_handler(message):
    markup = InlineKeyboardMarkup(True)
    markup.row("/categories")
    markup.row("/add", "/remove")
    # markup.row("/online")
    send_with_rerun(bot.send_message, message.chat.id, "menu", reply_markup=markup)


if __name__ == '__main__':
    ONLINE = {}
    CategoryData = {"pen": 0}
    t = Thread(target=start_server, args=(app, 8765))
    t.start()
    while True:
        try:
            bot.polling(none_stop=True, timeout=7000)
        except Exception as e:
            print(e)
        time.sleep(0.1)


