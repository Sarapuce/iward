import uuid
import utils
import random
import hashlib
import logging

from database import database
from datetime import datetime
class user:

  db = database("defaultdb")
  logging.basicConfig(level=logging.DEBUG)

  def __init__(self, email, password=""):
    self.email = email
    if password:
      self.password = password
      if self.db.create(email, password):
        self.user_headers = {
          "unique_device_id": hashlib.md5("{}{}".format(uuid.uuid4(), password).encode()).hexdigest()[:16],
          "ad_id":            str(uuid.uuid4()),
          "adjust_id":        hashlib.md5("{}{}".format(uuid.uuid4(), password).encode()).hexdigest(),
          "amplitude_id":     str(uuid.uuid4()) + 'R'
        }
        device = utils.get_random_device()
        self.device_id             = hashlib.md5("{}{}".format(uuid.uuid4(), password).encode()).hexdigest()[:16]
        self.device_manufacturer   = device["manufacturer"]
        self.device_model          = device["model"]
        self.device_product        = "{}_{}".format(self.device_manufacturer, self.device_model.replace(" ", "_"))
        self.device_system_version = "{}.0".format(random.randint(10, 14))
        self.db.update(email, {
          "unique_device_id":      self.user_headers["unique_device_id"],
          "ad_id":                 self.user_headers["ad_id"],
          "adjust_id":             self.user_headers["adjust_id"],
          "amplitude_id":          self.user_headers["amplitude_id"],
          "device_id":             self.device_id,
          "device_manufacturer":   self.device_manufacturer,
          "device_model":          self.device_model,
          "device_product":        self.device_product,
          "device_system_version": self.device_system_version
          })
      else:
        self.get_profile()
    else:
      self.get_profile()

  def connect(self):
    weward_token = utils.get_login_token(self.email, self.password, self.user_headers)
    logging.debug("WeWard token for {} : {}".format(self.email, weward_token))
    if not weward_token:
        return False
    self.token = weward_token
    self.db.update(self.email, {"token" : weward_token})
    return True
  
  def update_profile(self):
    user_data         = self.db.get(self.email)
    auth_token        = user_data["token"]
    server_data       = utils.get_user_info(self.user_headers, self.token)
    server_data_steps = utils.get_step_progress(self.user_headers, self.token)

    self.balance         = server_data["balance"]
    self.today_balance   = server_data["today_balance"]
    self.validated_steps = server_data_steps["valid_step"]
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

  def get_profile(self):
    user_data = self.db.get(self.email)

    self.password              = user_data["password"]
    self.token                 = user_data["token"]
    self.balance               = user_data["balance"]
    self.today_balance         = user_data["today_balance"]
    self.validated_steps       = user_data["validated_steps"]
    self.banned_cheater        = user_data["banned_cheater"]
    self.id                    = user_data["id"]
    self.username              = user_data["username"]
    self.user_headers = {
          "unique_device_id": user_data["unique_device_id"],
          "ad_id":            user_data["ad_id"] ,
          "adjust_id":        user_data["adjust_id"],
          "amplitude_id":     user_data["amplitude_id"]
        }
    self.device_id             = user_data["device_id"]
    self.device_manufacturer   = user_data["device_manufacturer"]
    self.device_model          = user_data["device_model"]
    self.device_product        = user_data["device_product"]
    self.device_system_version = user_data["device_system_version"]
    self.validated_today       = user_data["validated_today"]
    self.next_validation       = user_data["next_validation"]

  def validate_steps(self, step_number=0):
    logging.debug("Validating steps for {}".format(self.email))
    self.update_profile()
    if self.validated_steps > 10000:
      logging.debug("Aborting, this profile already validated its steps")
      return False
    
    if not step_number:
      step_number = random.randint(0, 2000)
    device_uptime_ms = random.randint(3870000, 10000000)
    payload = {
      "amount" : 19700 + step_number,
      "steps_needing_validation" : None,
      "device_id" : self.device_id,
      "device_manufacturer" : self.device_manufacturer,
      "device_model" : self.device_model,
      "device_product" : self.device_product,
      "device_system_name" : "Android",
      "device_system_version" : self.device_system_version,
      "device_uptime_ms" : device_uptime_ms,
      "steps_source" : "GoogleFit"
    }
    return utils.validate_steps(payload, self.user_headers, self.token)

  def delete(self):
    logging.debug("Deleting user {}".format(self.email))
    self.db.delete(self.email)

  def check_validation(self):
    if self.validated_today:
      return True
    
    now = datetime.now()
    next_validation = [int(i) for i in self.next_validation.split(":")]
    if (next_validation[0] == now.hour and next_validation[1] <= now.minute) or next_validation[0] < now.hour:
      self.validated_today = True
      self.db.update(self.email, {"validated_today": self.validated_today})
      return self.validate_steps()
      
  def set_timer(self):
    self.validated_today = False
    if random.randint(0, 10) == 5:
      self.validated_today = True
    
    validation_raw       = random.randint(1080, 1380)
    self.next_validation = "{}:{}".format(str(validation_raw // 60).zfill(2), str(validation_raw % 60).zfill(2))
    self.db.update(self.email, {"next_validation": self.next_validation, "validated_today": self.validated_today})
    return True

  def reset_new_day(self):
    self.validate_steps = 0
    self.today_balance  = 0
    self.db.update(self.email, {"validate_steps": self.validate_steps, "today_balance": self.today_balance})

def get_all_users():
  return user.db.get_all_emails()
