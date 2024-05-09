import os
import time
import json
import user
import uuid
import random
import logging
import imaplib
import hashlib
import requests

from threading import Thread
from database import database
from datetime import datetime, date
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)
# logging.basicConfig(filename='app.log', format='%(asctime)s - %(message)s', level=logging.INFO)

session = requests.session()
# Uncomment to use tor
# session.proxies = {'http':'socks5://127.0.0.1:9050', 'https':'socks5://127.0.0.1:9050'}
# logging.debug("IP in use : {}".format(session.get("http://httpbin.org/ip").json()["origin"]))

def decode(cipher):
    clear = ""
    for c in cipher:
        clear += chr(c ^ 0x41)
    return clear

validate_steps_url      = decode(b')5512{nn# "*$/%o13.%o6$6 3%o\'3n 1(n7poqn7 -(% 5$\x1e25$12')
step_progress_url       = decode(b')5512{nn# "*$/%o13.%o6$6 3%o\'3n 1(n7poqn25$1\x1e13.&3$22')
get_profile_url         = decode(b')5512{nn# "*$/%o13.%o6$6 3%o\'3n 1(n7poqn"425.,$3n&$5\x1e13.\'(-$')
signin_with_email_url   = decode(b')5512{nn# "*$/%o13.%o6$6 3%o\'3n 1(n7poqn"425.,$3n3$04$25\x1e2(&/(/\x1e6(5)\x1e$, (-')
signin_id_token         = decode(b')5512{nn# "*$/%o13.%o6$6 3%o\'3n 1(n7poqn"425.,$3n2(&/(/\x1e6(5)\x1e(%\x1e5.*$/')
referal_url             = decode(b')5512{nn# "*$/%o13.%o6$6 3%o\'3n 1(n7poqn"425.,$3n".,1-$5$\x1e21./2.32)(1\x1e25$1')
base_url                = decode(b')5512{nn666o6$6 3%o 11n2(&/(/\x1e6(5)\x1e$, (-')
host                    = decode(b'# "*$/%o13.%o6$6 3%o\'3')
sender_name             = decode(b'\x16$6 3%')
conversion_rate         = 0.0066666666
total_wards             = 0
total_euros             = ""

with open("devices.json", "r") as f:
    devices = json.load(f)

logging.debug("Decoded strings : ")
logging.debug("validate_steps_url = {}".format(validate_steps_url))
logging.debug("step_progress_url = {}".format(step_progress_url))
logging.debug("get_profile_url = {}".format(get_profile_url))
logging.debug("signin_with_email_url = {}".format(signin_with_email_url))
logging.debug("signin_id_token = {}".format(signin_id_token))
logging.debug("referal_url = {}".format(referal_url))
logging.debug("host = {}".format(host))
logging.debug("base_url = {}".format(base_url))


PASSWORD = os.getenv("PASSWORD")
SALT1    = os.getenv("SALT1")
SALT2    = os.getenv("SALT2")
SALT3    = os.getenv("SALT3")
SALT4    = os.getenv("SALT4")

if not PASSWORD:
    with open(".password", "r") as f:
        PASSWORD = f.read().strip('\n')

if not SALT1:
    SALT1 = uuid.uuid4()

if not SALT2:
    SALT2 = uuid.uuid4()

if not SALT3:
    SALT3 = uuid.uuid4()

if not SALT4:
    SALT4 = uuid.uuid4()

def auth_token2email(auth_token):
    try:
        for username in infos:
            if infos[username]["auth_token"] == auth_token:
                return infos[username]['email']
    except:
        return str(uuid.UUID(hashlib.md5("{}{}".format(SALT4, auth_token).encode()).hexdigest()))

def create_header(seed, auth_token = False):
    
    if auth_token:
        email = auth_token2email(seed)
    else:
        email = seed

    device_id = hashlib.md5("{}{}".format(SALT1, email).encode()).hexdigest()[:16]
    ts = str(int(time.time() * 1000))
    ad_id = uuid.UUID(hashlib.md5("{}{}".format(SALT2, email).encode()).hexdigest())
    track_id = hashlib.sha256("{}{}".format(SALT3, email).encode()).hexdigest()

    return { 
        "Map": "[object Object]",
        "Ww_app_version": "7.5.4",
        "Ww_os": "android",
        "Ww_os_version": "29",
        "Ww_build_version": "242075",
        "Ww_codepush_version": "v346",
        "Ww-Unique-Device-Id": device_id,
        "Ww_device_ts": ts,
        "Ww_device_timezone": "Europe/Paris",
        "Ww_device_country": "FR",
        "Ww_user_language": "fr-FR",
        "Ww_user_advertising_id": str(ad_id),
        "Ww_track": track_id
    }


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
                    validate_steps(infos[username]["auth_token"])

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


def validate_steps(auth_token):
    logging.debug("Validate steps for {}".format(auth_token2email(auth_token)))
    if get_validated_steps(auth_token) > 10000:
        logging.debug("Aborting, this profile already validated its steps")
        return
    
    random.seed(time.time())
    random_step = random.randint(0, 2000)
    device_uptime_ms = random.randint(3870000, 10000000)
    md5_hash = hashlib.md5(auth_token.encode()).hexdigest()
    
    random.seed(sum(ord(c) for c in auth_token[:3]))
    random_device = devices[random.randint(0, len(devices))]
    payload = {
        "amount" : 19700 + random_step,
        "steps_needing_validation" : None,
        "device_id" : md5_hash[:16],
        "device_manufacturer" : random_device["manufacturer"],
        "device_model" : random_device["manufacturer"],
        "device_product" : "{}_{}".format(random_device["manufacturer"], random_device["model"].replace(" ", "_")),
        "device_system_name" : "Android",
        "device_system_version" : "{}.0".format(random.randint(7, 11)),
        "device_uptime_ms" : device_uptime_ms,
        "googlefit_steps" : 0,
        "steps_source" : "GoogleFit",
        "data_sources" : [""]
    }

    headers = {
        "Authorization": auth_token,
        "Content-Type": "application/json",
        "Accept-Encoding": "gzip, deflate",
        "Host": host,
        "User-Agent": "okhttp/4.9.1"
    }

    headers = {**headers, **create_header(auth_token, True)}

    r = session.post(validate_steps_url, headers=headers, json=payload)
    logging.debug("Validate steps call ended with status code {}".format(r.status_code))
    if r.status_code != 200:
        logging.debug("Message from server : {}".format(r.text))
    return r.json()
    
def get_validated_steps(auth_token):
    logging.debug("Get steps number for {}".format(auth_token2email(auth_token)))
    headers = {
        "Authorization": auth_token,
        "Content-Type": "application/json",
        "Accept-Encoding": "gzip, deflate",
        "Host": host,
        "User-Agent": "okhttp/4.9.1"
    }

    headers = {**headers, **create_header(auth_token, True)}

    r = session.get(step_progress_url, headers=headers)
    logging.debug("Get steps call ended with status code {}".format(r.status_code))
    logging.debug("Answer from server : {}".format(r.text))
    return r.json()["valid_step"]

def get_profile(auth_token):
    logging.debug("Get profile for {}".format(auth_token2email(auth_token)))
    headers = {
        "Authorization": auth_token,
        "Content-Type": "application/json",
        "Accept-Encoding": "gzip, deflate",
        "Host": host,
        "User-Agent": "okhttp/4.9.1"
    }

    headers = {**headers, **create_header(auth_token, True)}

    r = session.get(get_profile_url, headers=headers)
    if r.status_code == 200:
        json = r.json()
        json["auth_token"] = auth_token
        json["validated_steps"] = get_validated_steps(auth_token)
        logging.debug("Request succeed")
        return json
    else:
        logging.debug("Request failed with status code {} and said {}".format(r.status_code, r.text))
        return {}

def update_profile(username):
    json = get_profile(infos[username]["auth_token"])
    for key in json:
        infos[username][key] = json[key]
    update_total_wards()

def get_auth_tokens():
    if not os.path.isfile("./tokens.txt"):
        with open('./tokens.txt', 'w') as f:
            pass
        return []

    with open('./tokens.txt', 'r') as f:
        data = f.read()
    tokens = data.split('\n')
    tokens = [i for i in tokens if i != '']
    return tokens

def init():
    emails = user.get_all_users()
    logging.debug("Mails found in database : {}".format(emails))
    for email in emails:
        users[email] = user.user(email)

def remove_token(token):
    data_removed = ""
    with open("tokens.txt", "r") as f:
        data = f.read().split('\n')
    for line in data:
        if line != token:
            data_removed += line
            data_removed += "\n"
    while '\n\n' in data_removed:
        data_removed = data_removed.replace('\n\n', '\n')
    with open("tokens.txt", "w") as f:
        f.write(data_removed)

def referral_user(auth_token, ref_code):
    payload = {
        "sponsorship_code" : ref_code
    }

    headers = {
        "Authorization": auth_token,
        "Content-Type": "application/json",
        "Accept-Encoding": "gzip, deflate",
        "Host": host,
        "User-Agent": "okhttp/4.9.1"
    }

    headers = {**headers, **create_header(auth_token, True)}

    r = session.post(referal_url, headers=headers, json=payload)
    logging.debug("Referal attribution ended with code {}".format(r.status_code))
    if r.status_code != 200:
        logging.debug("Message from server : {}".format(r.text))
    return r.json()

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
    
    for username in infos:
        validate_steps(infos[username]["auth_token"])
        update_profile(username)
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
        users.pop(email)
        return print_error("Can't generate token with email and password provided")
    return redirect(url_for("main"))

@app.route("/logout", methods=["POST"])
def logout():
    if request.cookies.get('auth') != PASSWORD:
        return redirect(url_for("main"))
    
    username = request.form.get("username")
    if not username:
        return print_error("Username not found in the POST request")
    token = infos[username]["auth_token"]
    remove_token(token)
    infos.pop(username)
    return redirect(url_for("main"))

@app.route("/referral", methods=["POST"])
def referral():
    if request.cookies.get('auth') != PASSWORD:
        return redirect(url_for("main"))
    
    username = request.form.get("username")
    code     = request.form.get("code")
    token = infos[username]["auth_token"]
    referral_user(token, code)
    return redirect(url_for("main"))

@app.route("/auth", methods=["POST"])
def auth():
    password = request.form.get("password")
    resp = redirect(url_for("main"))
    resp.set_cookie("auth", password)
    return resp

def print_error(error_msg):
    global error

    error = error_msg
    return redirect(url_for("main"))

users       = {}
infos       = init()
error       = ""
information = ""
# update_total_wards()

# t = Thread(target=watcher)
# t.start()
