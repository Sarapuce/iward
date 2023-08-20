import os
import time
import random
import logging
import imaplib
import requests

from threading import Thread
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

logging.debug("Decoded strings : ")
logging.debug("validate_steps_url = {}".format(validate_steps_url))
logging.debug("step_progress_url = {}".format(step_progress_url))
logging.debug("get_profile_url = {}".format(get_profile_url))
logging.debug("get_profile_url = {}".format(signin_with_email_url))
logging.debug("get_profile_url = {}".format(signin_id_token))
logging.debug("get_profile_url = {}".format(referal_url))
logging.debug("get_profile_url = {}".format(host))
logging.debug("get_profile_url = {}".format(base_url))


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
            scheduler()
        for username in infos:
            if infos.get("next_validation"):
                next_validation = infos["next_validation"].split(":")
                if (next_validation[0] == now.hour and next_validation[1] <= now.minute) or next_validation[0] < now.hour:
                    infos["next_validation"] = False
                    validate_steps(infos[username]["auth_token"])

        time.sleep(2)

def scheduler():
    print("Scheduling..")
    for username in infos:
        if random.randint(0, 10) == 5:
            infos[username]["next_validation"] = False
        else:
            next_validation = random.randint(1080, 1380)
            infos[username]["next_validation"] = "{}:{}".format(str(next_validation // 60).zfill(2), str(next_validation % 60).zfill(2))

def validate_steps(auth_token):
    logging.debug("Validate steps with auth_token = {}".format(auth_token))
    if get_validated_steps(auth_token) > 10000:
        logging.debug("Aborting, this profile already validated its steps")
        return
    
    random_step = random.randint(0, 2000)
    random_device = random.randint(0, 1000)
    payload = {
        "amount" : 19700 + random_step,
        "steps_needing_validation" : None,
        "device_id" : str(random_device),
        "device_manufacturer" : "Google",
        "device_model" : "Android SDK built for x86",
        "device_product" : "sdk_gphone_x86",
        "device_system_name" : "Android",
        "device_system_version" : "10",
        "device_uptime_ms" : "3878841",
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

    r = session.post(validate_steps_url, headers=headers, json=payload)
    logging.debug("Validate steps call ended with status code {}".format(r.status_code))
    if r.status_code != 200:
        logging.debug("Message from server : {}".format(r.text))
    return r.json()
    
def get_validated_steps(auth_token):
    logging.debug("Get steps number with auth_token = {}".format(auth_token))
    headers = {
        "Authorization": auth_token,
        "Content-Type": "application/json",
        "Accept-Encoding": "gzip, deflate",
        "Host": host,
        "User-Agent": "okhttp/4.9.1"
    }

    r = session.get(step_progress_url, headers=headers)
    logging.debug("Get steps call ended with status code {}".format(r.status_code))
    logging.debug("Answer from server : {}".format(r.text))
    return r.json()["valid_step"]

def get_profile(auth_token):
    logging.debug("Get profile with auth_token = {}".format(auth_token))
    headers = {
        "Authorization": auth_token,
        "Content-Type": "application/json",
        "Accept-Encoding": "gzip, deflate",
        "Host": host,
        "User-Agent": "okhttp/4.9.1"
    }

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
    print(infos[username])

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
    infos = {}
    tokens = get_auth_tokens()
    for token in tokens:
        profile = get_profile(token)
        profile["next_validation"] = False
        if profile != {}:
            infos[profile["username"]] = profile

    return infos

def get_weward_link(email, password):
    imap_server = imaplib.IMAP4_SSL(host="imap.gmx.com")
    imap_server.login(email, password)
    imap_server.select()

    c = 0
    _, message_numbers_raw = imap_server.search(None, 'FROM', sender_name)
    while not message_numbers_raw[0].split() and c < 10:
        time.sleep(3)
        _, message_numbers_raw = imap_server.search(None, 'FROM', sender_name)
        logging.debug("Waiting for message." + "." * c)
        c += 1

    for message_number in message_numbers_raw[0].split():
        _, msg  = imap_server.fetch(message_number, '(RFC822)')
        content = msg[0][1].decode()
        start   = content.index(base_url)
        end     = content.index("\"}\r\nX-Mailgun-Template")
    
    imap_server.close()
    imap_server.logout()
    return content[start:end]

def delete_all_mail(email, password):
    logging.debug("Deleting all mails")
    
    imap_server = imaplib.IMAP4_SSL(host="imap.gmx.com")
    try:
        imap_server.login(email, password)
    except:
        return False
    imap_server.select()
    
    typ, data = imap_server.search(None, 'ALL')
    for num in data[0].split():
        imap_server.store(num, '+FLAGS', '\\Deleted')
    imap_server.expunge()
    imap_server.close()
    imap_server.logout()
    logging.debug("All mails deleted")
    return True

def check_if_mail(email, password):
    imap_server = imaplib.IMAP4_SSL(host="imap.gmx.com")
    imap_server.login(email, password)
    imap_server.select()

    _, message_numbers_raw = imap_server.search(None, 'FROM', sender_name)

    if message_numbers_raw[0]:
        logging.debug("Found corresponding messages : {}".format(message_numbers_raw))
        return True
    else:
        return False

def get_login_link(email, password):
    if not delete_all_mail(email, password):
        return False

    headers = {
        "Content-Type": "application/json",
        "Accept-Encoding": "gzip, deflate",
        "Host": host,
        "User-Agent": "okhttp/4.9.1"
    }
    
    payload = {
        "email": email   
        }
    logging.debug("Sending connection mail")
    r = session.post(signin_with_email_url, json=payload, headers=headers)
    return get_weward_link(email, password)

def get_google_jwt(weward_token):
    payload = {
        "token": weward_token,
        "returnSecureToken": True
    }

    r = requests.post("https://www.googleapis.com/identitytoolkit/v3/relyingparty/verifyCustomToken?key=AIzaSyBpVnvwRMvz9lP9A2cVBKIIutli4ZuCmm4", json=payload)
    return r.json()["idToken"]

def get_auth_token(google_token):
    payload = {
        "id_token" : google_token,
    }

    headers = {
        "Content-Type": "application/json",
        "Accept-Encoding": "gzip, deflate",
        "Host": host,
        "User-Agent": "okhttp/4.9.1"
    }

    r = session.post(signin_id_token, json=payload, headers=headers)
    if r.status_code != 200:
        logging.debug("Message from server : {}".format(r.text))
    return r.json()["token"]

def get_auth_token_from_mail(email, password):
    weward_link  = get_login_link(email, password)
    logging.debug("WeWard link : {}".format(weward_link))
    if not weward_link:
        return False
    weward_token = weward_link.split('=')[1].split('&')[0]
    logging.debug("WeWard token : {}".format(weward_token))
    google_token = get_google_jwt(weward_token)
    logging.debug("Google token : {}".format(google_token))
    return get_auth_token(google_token)

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

def referral_user(token, ref_code):
    payload = {
        "sponsorship_code" : ref_code
    }

    headers = {
        "Authorization": token,
        "Content-Type": "application/json",
        "Accept-Encoding": "gzip, deflate",
        "Host": host,
        "User-Agent": "okhttp/4.9.1"
    }

    r = session.post(referal_url, headers=headers, json=payload)
    logging.debug("Referal attribution ended with code {}".format(r.status_code))
    if r.status_code != 200:
        logging.debug("Message from server : {}".format(r.text))
    return r.json()

@app.route("/", methods=["GET"])
def main():
    if request.cookies.get('auth') != PASSWORD:
        return render_template("get_cookie.html")
    
    global error
    
    render = render_template("index.html", infos=infos, error=error)
    error = ''
    return render

@app.route("/debug", methods=["GET"])
def debug():
    return "This is a debug page :)"

@app.route("/validate_step", methods=["POST"])
def validate_step():
    if request.cookies.get('auth') != PASSWORD:
        return redirect(url_for("main"))
    
    username = request.form.get("username")
    if not username:
        return print_error("Username not found in the POST request")
    validate_steps(infos[username]["auth_token"])
    update_profile(username)
    return redirect(url_for("main"))

@app.route("/refresh", methods=["POST"])
def refresh():
    if request.cookies.get('auth') != PASSWORD:
        return redirect(url_for("main"))
    
    username = request.form.get("username")
    if not username:
        return print_error("Username not found in the POST request")
    update_profile(username)
    return redirect(url_for("main"))

@app.route("/add_account", methods=["POST"])
def add_account():
    if request.cookies.get('auth') != PASSWORD:
        return redirect(url_for("main"))
    
    email = request.form.get("email")
    password = request.form.get("password")
    if not email or not password:
        return print_error("email or password not found in the POST request")
    auth_token = get_auth_token_from_mail(email, password)
    if not auth_token:
        return print_error("Can't generate token with email and password provided")
    with open("tokens.txt", "a") as f:
        f.write(auth_token + "\n")
    profile = get_profile(auth_token)
    infos[profile["username"]] = profile
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

infos = init()
error = ""
information = ""


t = Thread(target=watcher)
t.start()
