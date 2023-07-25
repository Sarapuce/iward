import time
import random
import logging
import imaplib
import requests

from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)
# logging.basicConfig(filename='app.log', format='%(asctime)s - %(message)s', level=logging.INFO)

session = requests.session()
session.proxies = {'http':'socks5://127.0.0.1:9050', 'https':'socks5://127.0.0.1:9050'}
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
base_url                = decode(b')5512{nn666o6$6 3%o 11n2(&/(/\x1e6(5)\x1e$, (-')
sender_name             = decode(b'\x16$6 3%')

logging.debug("Decoded strings : ")
logging.debug("validate_steps_url = {}".format(validate_steps_url))
logging.debug("step_progress_url = {}".format(step_progress_url))
logging.debug("get_profile_url = {}".format(get_profile_url))
logging.debug("get_profile_url = {}".format(signin_with_email_url))
logging.debug("get_profile_url = {}".format(base_url))

def validate_steps(auth_token):
    logging.debug("Validate steps with auth_token = {}".format(auth_token))
    if get_validated_steps(auth_token) > 10000:
        logging.debug("Aborting, this profile already validated its steps")
        return
    
    random_step = random.randint(0, 200)
    random_device = random.randint(0, 1000)
    payload = {
        "amount" : 20000 + random_step,
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
        "Accept-Encoding": "gzip, deflate"
    }

    r = session.post(validate_steps_url, headers=headers, json=payload)
    logging.debug("Validate steps call ended with status code {}".format(r.status_code))
    if r.status_code != 200:
        logging.debug("Message from server : {}".format(r.text))
    return r.json()
    
def get_validated_steps(auth_token):
    logging.debug("Get steps number with auth_token = {}".format(auth_token))
    headers = {
        "Authorization" : auth_token
    }

    r = session.get(step_progress_url, headers=headers)
    logging.debug("Get steps call ended with status code {}".format(r.status_code))
    logging.debug("Answer from server : {}".format(r.text))
    return r.json()["valid_step"]

def get_profile(auth_token):
    logging.debug("Get profile with auth_token = {}".format(auth_token))
    headers = {
        "Authorization" : auth_token
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
    infos[username] = json

def get_auth_tokens():
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
        infos[profile["username"]] = profile
    return infos

def get_weward_link(email, password):
    imap_server = imaplib.IMAP4_SSL(host="imap.gmx.com")
    imap_server.login(email, password)
    imap_server.select()

    _, message_numbers_raw = imap_server.search(None, 'FROM', sender_name)
    logging.debug("Message send by {} : {}".format(sender_name, message_numbers_raw))
    for message_number in message_numbers_raw[0].split():
        _, msg  = imap_server.fetch(message_number, '(RFC822)')
        content = msg[0][1].decode()
        start   = content.index(base_url)
        end     = content.index("\"}\r\nX-Mailgun-Template")
    
    imap_server.close()
    imap_server.logout()
    return content[start:end]

def delete_all_mail(email, password):
    imap_server = imaplib.IMAP4_SSL(host="imap.gmx.com")
    imap_server.login(email, password)
    imap_server.select()
    
    typ, data = imap_server.search(None, 'ALL')
    for num in data[0].split():
        imap_server.store(num, '+FLAGS', '\\Deleted')
    imap_server.expunge()
    imap_server.close()
    imap_server.logout()

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
    delete_all_mail(email, password)
    
    payload = {
        "email": email   
        }
    r = session.post(signin_with_email_url, json=payload)

    c = 0
    while not check_if_mail(email, password):
        logging.debug("Checking for new messages." + "." * c)
        time.sleep(3)
        c += 1
        if c > 10:
            logging.debug("No new message during 30 secondes")
            return False

    time.sleep(1)
    return get_weward_link(email, password)

@app.route("/", methods=["GET"])
def main():
    return render_template("index.html", infos=infos)

@app.route("/debug", methods=["GET"])
def debug():
    return "This is a debug page :)"

@app.route("/validate_step", methods=["POST"])
def validate_step():
    username = request.form.get("username")
    validate_steps(infos[username]["auth_token"])
    update_profile(username)
    return redirect(url_for("main"))

@app.route("/refresh", methods=["POST"])
def refresh():
    username = request.form.get("username")
    update_profile(username)
    return redirect(url_for("main"))

infos = init()
