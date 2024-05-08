import uuid
import utils
import hashlib
import logging

from database import database

class user:

  db = database()
  logging.basicConfig(level=logging.DEBUG)

  def __init__(self, email, password):
    self.email = email
    self.password = password
    if self.db.create(email, password):
      self.user_headers = {
        "unique_device_id": hashlib.md5("{}{}".format(uuid.uuid4(), password).encode()).hexdigest()[:16],
        "ad_id":            str(uuid.uuid4()),
        "adjust_id":        hashlib.md5("{}{}".format(uuid.uuid4(), password).encode()).hexdigest(),
        "amplitude_id":     str(uuid.uuid4()) + 'R'
      }
      self.db.update(email, {
        "unique_device_id" : self.user_headers["unique_device_id"],
        "ad_id" : self.user_headers["ad_id"],
        "adjust_id" : self.user_headers["adjust_id"],
        "amplitude_id" : self.user_headers["amplitude_id"],
        })
    else:
      user_data = self.db.get(self.email)
      self.user_headers = {
        "unique_device_id": user_data["unique_device_id"],
        "ad_id":            user_data["ad_id"],
        "adjust_id":        user_data["adjust_id"],
        "amplitude_id":     user_data["amplitude_id"]
      }

  def connect(self):
    weward_token = utils.get_login_token(self.email, self.password, self.user_headers)
    logging.debug("WeWard token for {} : {}".format(self.email, weward_token))
    if not weward_token:
        return False
    self.token = weward_token
    self.db.update(self.email, {"token" : weward_token})
    return True
  
  def update_profile(self):
    user_data   = self.db.get(self.email)
    auth_token  = user_data["token"]
    server_data = utils.get_user_info(self.user_headers, self.token)

    self.balance         = server_data["balance"]
    self.today_balance   = server_data["today_balance"]
    self.validated_steps = server_data["validated_steps"]
    self.banned_cheater  = server_data["banned_cheater"]
    self.id              = server_data["id"]
    self.username        = server_data["username"]

    self.db.update(self.email, {
      "balance": self.balance,
      "today_balance": self.today_balance,
      "validated_steps": self.validated_steps,
      "banned_cheater": self.banned_cheater,
      "id": self.id,
      "username": self.username
    })

