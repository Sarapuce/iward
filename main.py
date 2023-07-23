import random
import logging
import requests

from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)
# logging.basicConfig(filename='app.log', format='%(asctime)s - %(message)s', level=logging.INFO)

def decode(cipher):
    clear = ""
    for c in cipher:
        clear += chr(c ^ 0x41)
    return clear

validate_steps_url = decode(b')5512{nn# "*$/%o13.%o6$6 3%o\'3n 1(n7poqn7 -(% 5$\x1e25$12')
step_progress_url  = decode(b')5512{nn# "*$/%o13.%o6$6 3%o\'3n 1(n7poqn25$1\x1e13.&3$22')
get_profile_url    = decode(b')5512{nn# "*$/%o13.%o6$6 3%o\'3n 1(n7poqn"425.,$3n&$5\x1e13.\'(-$')

logging.debug("Decoded strings : ")
logging.debug("validate_steps_url = {}".format(validate_steps_url))
logging.debug("step_progress_url = {}".format(step_progress_url))
logging.debug("get_profile_url = {}".format(get_profile_url))

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

    r = requests.post(validate_steps_url, headers=headers, json=payload)
    logging.debug("Validate steps call ended with status code {}".format(r.status_code))
    return r.json()
    
def get_validated_steps(auth_token):
    logging.debug("Get steps number with auth_token = {}".format(auth_token))
    headers = {
        "Authorization" : auth_token
    }

    r = requests.get(step_progress_url, headers=headers)
    logging.debug("Get steps call ended with status code {}".format(r.status_code))
    return r.json()["valid_step"]

def get_profile(auth_token):
    logging.debug("Get profile with auth_token = {}".format(auth_token))
    headers = {
        "Authorization" : auth_token
    }

    r = requests.get(get_profile_url, headers=headers)
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

infos = {}
tokens = get_auth_tokens()
for token in tokens:
    profile = get_profile(token)
    infos[profile["username"]] = profile
print(infos)
