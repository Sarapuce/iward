import requests
import random
from flask import Flask, render_template

app = Flask(__name__)

def validate_steps(auth_token):
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

    r = requests.post("https://backend.prod.weward.fr/api/v1.0/validate_steps", headers=headers, json=payload)
    print(r.text, r.status_code)
    return r.text, r.status_code
    

def get_profile(auth_token):
    headers = {
        "Authorization" : auth_token
    }

    r_profile = requests.get("https://backend.prod.weward.fr/api/v1.0/customer/get_profile", headers=headers)
    print(r_profile.text, r_profile.status_code)
    if r_profile.status_code == 200:
        json = r_profile.json()
        json["Auth_token"] = auth_token[:4] + '*' * 39

    r_step = requests.get("https://backend.prod.weward.fr/api/v1.0/step_progress", headers=headers)
    steps = r_step.json()["valid_step"]
    json["validated_steps"] = steps

    print(json)
    return json

def get_auth_tokens():
    with open('./tokens.txt', 'r') as f:
        data = f.read()
    tokens = data.split('\n')
    tokens = [i for i in tokens if i != '']
    return tokens

@app.route('/')
def main():
    return render_template('index.html', infos=infos)

@app.route('/debug')
def debug():
    return 'This is a debug page :)'

infos = []
tokens = get_auth_tokens()
for token in tokens:
    # validate_steps(token)
    infos.append(get_profile(token))
