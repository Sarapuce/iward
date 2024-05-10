import os
import time
import user
import random
import logging

from threading import Thread
from datetime import datetime, date
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)
logging.basicConfig(filename='app.log', format='%(asctime)s - %(message)s', level=logging.INFO)

# Uncomment to use tor
# session.proxies = {'http':'socks5://127.0.0.1:9050', 'https':'socks5://127.0.0.1:9050'}
# logging.debug("IP in use : {}".format(session.get("http://httpbin.org/ip").json()["origin"]))

PASSWORD = os.getenv("PASSWORD")
if not PASSWORD:
    with open(".password", "r") as f:
        PASSWORD = f.read().strip('\n')

def watcher():
    today = -1
    while True:
        now = datetime.now()
        if today != now.day:
            today = now.day
            new_day()
        for username in infos:
            if infos[username].get("next_validation"):
                next_validation = [int(i) for i in infos[username]["next_validation"].split(":")]
                if (next_validation[0] == now.hour and next_validation[1] <= now.minute) or next_validation[0] < now.hour:
                    infos[username]["next_validation"] = False
                    # validate_steps(infos[username]["auth_token"])

        time.sleep(2)

def scheduler():
    for username in infos:
        if random.randint(0, 10) == 5:
            infos[username]["next_validation"] = False
        else:
            next_validation = random.randint(1080, 1380)
            infos[username]["next_validation"] = "{}:{}".format(str(next_validation // 60).zfill(2), str(next_validation % 60).zfill(2))

def new_day():
    scheduler()
    for username in infos:
        infos[username]["today_balance"]   = 0
        infos[username]["validated_steps"] = 0

def init():
    emails = user.get_all_users()
    logging.debug("Mails found in database : {}".format(emails))
    for email in emails:
        users[email] = user.user(email)

def update_total_wards():
    global total_wards
    global total_euros
    
    total_wards = 0
    for username in infos:
        total_wards += infos[username]["balance"]

    total_euros = "{:.2f}".format(total_wards * conversion_rate)

@app.route("/", methods=["GET"])
def main():
    if request.cookies.get("auth") != PASSWORD:
        return render_template("get_cookie.html")
    
    global error
    logging.debug("users : {}".format(users))
    for email in users:
        users[email].get_profile() 
    render = render_template("index.html", users=users, error=error, total_wards=total_wards, total_euros=total_euros)
    error = ""
    return render

@app.route("/debug", methods=["GET"])
def debug():
    return "This is a debug page :)"

@app.route("/validate_step", methods=["POST"])
def validate_step():
    if request.cookies.get('auth') != PASSWORD:
        return redirect(url_for("main"))
    
    email = request.form.get("email")
    if not email:
        return print_error("Email not found in the POST request")
    users[email].validate_steps()
    users[email].update_profile()
    return redirect(url_for("main"))

@app.route("/refresh", methods=["POST"])
def refresh():
    if request.cookies.get('auth') != PASSWORD:
        return redirect(url_for("main"))
    
    print(request.form)
    email = request.form.get("email")
    if not email:
        return print_error("Email not found in the POST request")
    users[email].update_profile()
    return redirect(url_for("main"))

@app.route("/refresh_all", methods=["POST"])
def refresh_all():
    if request.cookies.get('auth') != PASSWORD:
        return redirect(url_for("main"))
    
    for email in users:
        users[email].update_profile()
    return redirect(url_for("main"))

@app.route("/validate_all", methods=["POST"])
def validate_all():
    if request.cookies.get('auth') != PASSWORD:
        return redirect(url_for("main"))
    
    for email in users:
        users[email].validate_steps()
        users[email].update_profile()
    return redirect(url_for("main"))

@app.route("/add_account", methods=["POST"])
def add_account():
    if request.cookies.get('auth') != PASSWORD:
        return redirect(url_for("main"))
    
    # Form verification
    email = request.form.get("email")
    password = request.form.get("password")
    if not email or not password:
        return print_error("Email or password not found in the POST request")
    if email in users:
        return print_error("User already in the list")
    
    # User connection
    #TODO determine what failed during the connection
    users[email] = user.user(email, password)
    if not users[email].connect():
        users[email].delete()
        users.pop(email)
        return print_error("Can't generate token with email and password provided")
    users[email].update_profile()
    return redirect(url_for("main"))

@app.route("/logout", methods=["POST"])
def logout():
    if request.cookies.get('auth') != PASSWORD:
        return redirect(url_for("main"))
    
    email = request.form.get("email")
    if not email:
        return print_error("Email not found in the POST request")
    users[email].delete()
    users.pop(email)
    return redirect(url_for("main"))

@app.route("/auth", methods=["POST"])
def auth():
    password = request.form.get("password")
    resp = redirect(url_for("main"))
    resp.set_cookie("auth", password)
    return resp

@app.route("/logs", methods=["GET"])
def get_logs():
    if request.cookies.get('auth') != PASSWORD:
        return redirect(url_for("main"))
    
    with open("app.log", "r") as f:
        logs = f.read().split('\n')
    
    return render_template("logs.html", logs=logs)


def print_error(error_msg):
    global error

    error = error_msg
    return redirect(url_for("main"))

users           = {}
infos           = init()
error           = ""
information     = ""
conversion_rate = 0.0066666666
total_wards     = 0
total_euros     = ""
# update_total_wards()

# t = Thread(target=watcher)
# t.start()
