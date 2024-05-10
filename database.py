import os
import logging
import psycopg2

from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

class database:
    
    pg_host     = os.environ.get("PGHOST")
    pg_port     = os.environ.get("PGPORT")
    pg_password = os.environ.get("PGPASSWORD")
    pg_user     = os.environ.get("PGUSER")

    if not pg_host or not pg_port or not pg_password or not pg_user:
        logging.error("One of the following env variable is not set : PGHOST, PGPORT, PGPASSWORD PGUSER")
    
    def __init__(self, db_name="iward", table_name="users"):
        self.table_name = table_name
        self.db_name    = db_name
        try:
            logging.debug("Trying to connect to {}:{}".format(self.pg_host, self.pg_port))
            conn = psycopg2.connect(dbname=db_name,
                                host=self.pg_host,
                                user=self.pg_user,
                                password=self.pg_password,
                                port=self.pg_port)
            logging.debug("Connected to {}:{}".format(self.pg_host, self.pg_port))

        except psycopg2.OperationalError as err:
            if 'does not exist' in str(err):
                logging.debug("Database '{}' not found, creating it".format(db_name))
                conn = psycopg2.connect(host=self.pg_host,
                                user=self.pg_user,
                                password=self.pg_password,
                                port=self.pg_port)
                conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
                cursor = conn.cursor()
                cursor.execute(sql.SQL("CREATE DATABASE {}".format(str(db_name))))
                conn.close()
                logging.debug("Database '{}' created".format(db_name))
                conn = psycopg2.connect(dbname=db_name,
                                host=self.pg_host,
                                user=self.pg_user,
                                password=self.pg_password,
                                port=self.pg_port)
                logging.debug("Connected to {}:{}".format(self.pg_host, self.pg_port))
            elif 'Connection refused' in str(err):
                logging.error("Unable to connect to {}:{}".format(self.pg_host, self.pg_port))
                exit(1)
            else:
                logging.error("Unable to connect to {}:{} because {}".format(self.pg_host, self.pg_port, err))
                exit(1)
        
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        cursor.execute(sql.SQL("""CREATE TABLE IF NOT EXISTS users (
                                    email varchar(100) NOT NULL,
                                    password varchar(100) NOT NULL,
                                    token varchar(100),
                                    balance integer,
                                    today_balance integer,
                                    validated_steps integer,
                                    banned_cheater varchar(100),
                                    id varchar(100),
                                    username varchar(100),
                                    unique_device_id varchar(100),
                                    ad_id varchar(100),
                                    adjust_id varchar(100),
                                    amplitude_id varchar(100),
                                    device_id varchar(100),
                                    device_manufacturer varchar(100),
                                    device_model varchar(100),
                                    device_product varchar(100),
                                    device_system_version varchar(100),
                                    next_validation varchar(100),
                                    validated_today boolean,
                                    PRIMARY KEY (email))"""))
        conn.close()
        logging.debug("Table {} ready to be used".format(self.table_name))

    def create(self, email, password):
        user_data = self.get(email)
        if user_data:
            logging.debug("User {} already exist in the database".format(email))
            if not user_data["adjust_id"] or not user_data["ad_id"] or not user_data["unique_device_id"] or not user_data["amplitude_id"]:
                logging.debug("User {} already exist in the database but is not configured".format(email))
                return True
            else:
                logging.debug("User {} already exist in the database and is well configured".format(email))
                return False
        try:
            conn = psycopg2.connect(dbname=self.db_name,
                        host=self.pg_host,
                        user=self.pg_user,
                        password=self.pg_password,
                        port=self.pg_port)
            cursor = conn.cursor()

            columns = ", ".join([
                "email",
                "password"
            ])
            placeholders = ", ".join(["%s" for _ in columns.split(",")])
            insert_query = f"INSERT INTO users ({columns}) VALUES ({placeholders});"

            cursor.execute(insert_query, (email, password))
            conn.commit()

            logging.debug("User with email '{}' created successfully !".format(email))

        except psycopg2.OperationalError as err:
            print("Error connecting to PostgreSQL server:", err)
            raise
        except psycopg2.Error as err:
            print("Error creating user entry:", err)
            conn.rollback()
        finally:
            if conn:
                conn.close()
        return True

    def update(self, email, update_data):
        try:
            conn = psycopg2.connect(dbname=self.db_name,
                                    host=self.pg_host,
                                    user=self.pg_user,
                                    password=self.pg_password,
                                    port=self.pg_port)
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()
            if len(update_data.keys()) == 1:
                update_query = f"UPDATE users SET {list(update_data.keys())[0]} = %s WHERE email = %s;"
            else:
                update_columns = ", ".join(update_data.keys())
                update_values = ",".join(["%s" for _ in update_data.values()])
                update_query = f"UPDATE users SET ({update_columns}) = ({update_values}) WHERE email = %s;"
            cursor.execute(update_query, (*update_data.values(), email))
        except psycopg2.OperationalError as err:
            logging.error("Error connecting to PostgreSQL server:", err)
            raise
        except psycopg2.Error as err:
            logging.error("Error updating user data:", err)
            conn.rollback()
        finally:
            if conn:
                conn.close()
        logging.debug("Database updated")

    def delete(self, email):
        try:
            conn = psycopg2.connect(dbname=self.db_name,
                                    host=self.pg_host,
                                    user=self.pg_user,
                                    password=self.pg_password,
                                    port=self.pg_port)
            cursor = conn.cursor()

            delete_query = f"DELETE FROM users WHERE email = %s;"

            cursor.execute(delete_query, (email,))
            conn.commit()

            logging.debug(f"User with email '{email}' deleted.")

        except psycopg2.OperationalError as err:
            print("Error connecting to PostgreSQL server:", err)
            raise
        except psycopg2.Error as err:
            print("Error deleting user entry:", err)
            conn.rollback()
        finally:
            if conn:
                conn.close()

    def get(self, email):
        try:
            conn = psycopg2.connect(dbname=self.db_name,
                                    host=self.pg_host,
                                    user=self.pg_user,
                                    password=self.pg_password,
                                    port=self.pg_port)
            cursor = conn.cursor()
            select_query = f"SELECT * FROM users WHERE email = %s;"
            cursor.execute(select_query, (email,))
            user_data = cursor.fetchone()
            conn.close()

            if user_data:
                return dict(zip([col.name for col in cursor.description], user_data))
            else:
                return None

        except psycopg2.OperationalError as err:
            print("Error connecting to PostgreSQL server:", err)
            raise
        except psycopg2.Error as err:
            print("Error retrieving user entry:", err)
        finally:
            if conn:
                conn.close()

    def get_all_emails(self):
        try:
            conn = psycopg2.connect(dbname=self.db_name,
                                    host=self.pg_host,
                                    user=self.pg_user,
                                    password=self.pg_password,
                                    port=self.pg_port)
            cursor = conn.cursor()
            select_query = f"SELECT email FROM users;"
            cursor.execute(select_query)
            emails = cursor.fetchall()

        except psycopg2.OperationalError as err:
            print("Error connecting to PostgreSQL server:", err)
            raise
        except psycopg2.Error as err:
            print("Error retrieving user entry:", err)
        finally:
            if conn:
                conn.close()
        
        if emails:
            logging.debug("Emails found : {}".format(emails))
            return emails
        else:
            return []
