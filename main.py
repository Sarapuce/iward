import os
import user
import logging

from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)

# Uncomment to use tor
# session.proxies = {'http':'socks5://127.0.0.1:9050', 'https':'socks5://127.0.0.1:9050'}
# logging.debug("IP in use : {}".format(session.get("http://httpbin.org/ip").json()["origin"]))

try:
    PASSWORD = os.getenv("PASSWORD")
    if not PASSWORD:
        with open(".password", "r") as f:
            PASSWORD = f.read().strip('\n')
except:
    logging.debug("PASSWORD not set")

def update_total_wards():
    global total_wards
    global total_euros
    
    total_wards = 0
    for email in users:
        total_wards += users[email].balance

    total_euros = "{:.2f}".format(total_wards * conversion_rate)

def init():
    emails = [result[0] for result in user.get_all_users()]
    logging.debug("Mails found in database : {}".format(emails))
    for email in emails:
        users[email] = user.user(email)
    update_total_wards()

@app.route("/", methods=["GET"])
def main():
    if request.cookies.get("auth") != PASSWORD:
        return render_template("get_cookie.html")
    
    global error
    logging.debug("users : {}".format(users))
    for email in users:
        users[email].get_profile()
    update_total_wards()
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

@app.route("/check_validation", methods=["POST"])
def check_validation():
    if request.cookies.get('auth') != PASSWORD:
        return redirect(url_for("main"))
    
    result = True
    for email in users:
        result = users[email].check_validation() and result
    if result:
        return "success"
    else:
        return "fail"

@app.route("/set_timers", methods=["POST"])
def set_timers():
    if request.cookies.get('auth') != PASSWORD:
        return redirect(url_for("main"))
    
    result = True
    for email in users:
        result = users[email].set_timer() and result
    if result:
        return "success"
    else:
        return "fail"

@app.route("/reset_new_day", methods=["POST"])
def reset_new_day():
    if request.cookies.get('auth') != PASSWORD:
        return redirect(url_for("main"))
    
    result = True
    for email in users:
        result = users[email].reset_new_day() and result
    if result:
        return "success"
    else:
        return "fail"

def print_error(error_msg):
    global error

    error = error_msg
    return redirect(url_for("main"))

users           = {}
infos           = init()
error           = ""
conversion_rate = 0.0066666666
total_wards     = 0
total_euros     = ""
