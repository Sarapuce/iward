import time
import uuid
import hashlib
import logging
import imaplib
import requests

##########
# Config #
##########

logging.basicConfig(level=logging.DEBUG)

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

user_agent = "okhttp/4.11.0"

####################
# Hidden functions #
####################

def generate_headers(user_headers, auth_token=""):
  headers = {
    "Content-Type": "application/json",
    "Accept-Encoding": "gzip, deflate",
    "Host": host,
    "User-Agent": user_agent,
    "Ww_app_version": "7.6.5",
    "Ww_os": "android",
    "Ww_os_version": "29",
    "Ww_build_version": "242174",
    "Ww_codepush_version": "base",
    "Ww-Unique-Device-Id": user_headers["unique_device_id"],
    "Ww_device_ts": str(int(time.time() * 1000)),
    "Ww_device_timezone": "Europe/Paris",
    "Ww_device_country": "US",
    "Ww_user_language": "en-US",
    "Ww_user_advertising_id": user_headers["ad_id"],
    "Ww_adjust_id": user_headers["adjust_id"],
    "Push_notification_enabled": "1",
    "Amplitude_device_id": user_headers["amplitude_id"],
    "Ww_track": hashlib.sha256(str(uuid.uuid4()).encode()).hexdigest()
  }
  if auth_token:
      headers["Authorization"] = auth_token
  return headers

def delete_all_mail(email, password):
  imap_server = imaplib.IMAP4_SSL(host="imap.gmx.com")
  try:
      imap_server.login(email, password)
  except:
      logging.debug("Can't connect to mail server")
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
        content = content[start:]
        end     = content.index("]")
        content = content[:end]
        content = content.replace('=\r\n', '')

    imap_server.close()
    imap_server.logout()
    
    try:
        return content
    except UnboundLocalError:
        logging.error("No mail found")
        return ""

def get_google_token(weward_token):
    payload = {
        "token": weward_token,
        "returnSecureToken": True
    }

    r = requests.post("https://www.googleapis.com/identitytoolkit/v3/relyingparty/verifyCustomToken?key=AIzaSyBpVnvwRMvz9lP9A2cVBKIIutli4ZuCmm4", json=payload)
    return r.json()["idToken"]

def get_auth_token(google_token, email, user_headers):
    payload = {
        "id_token" : google_token,
    }

    r = requests.post(signin_id_token, json=payload, headers=user_headers)
    if r.status_code != 200:
        logging.debug("Message from server : {}".format(r.text))
    return r.json()["token"]

##################
# Main functions #
##################

def get_login_token(email, password, user_headers):
  if not delete_all_mail(email, password):
    logging.debug("Can't connect to mail server")
    return ""
    
  payload = {
    "email": email   
  }
  logging.debug("Sending connection mail")

  headers = generate_headers(user_headers)

  r = requests.post(signin_with_email_url, json=payload, headers=headers)
  logging.debug("Answer from server : {} : {}".format(r.status_code, r.text))
  weward_link = get_weward_link(email, password)
  if not weward_link:
      return False
  weward_token = weward_link.split('=3D')[1].split('&')[0]
  logging.debug("WeWard token : {}".format(weward_token))
  google_token = get_google_token(weward_token)
  logging.debug("Google token : {}".format(google_token))
  return get_auth_token(google_token, email, headers)

def get_user_info(user_headers, auth_token):
    headers = generate_headers(user_headers, auth_token)
    r = requests.get(get_profile_url, headers=headers)
    logging.debug("Answer from server : {}".format(r.status_code))
    return r.json()
