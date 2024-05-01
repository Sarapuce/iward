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
    
    def __init__(self, db_name="iward", table_name="users"):
        self.table_name = table_name
        self.db_name    = db_name
        try:
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
        
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        cursor.execute(sql.SQL("""CREATE TABLE IF NOT EXISTS users (
                                    email varchar(100) NOT NULL,
                                    password varchar(100) NOT NULL,
                                    token varchar(100),
                                    balance integer,
                                    today_balance integer,
                                    validated_steps integer,
                                    PRIMARY KEY (email))"""))
        conn.close()
        logging.debug("Table {} ready to be used".format(self.table_name))

    def create(self, email, password, token="", balance=0, today_balance=0, validated_steps=0):
        try:
            conn = psycopg2.connect(dbname=self.db_name,
                        host=self.pg_host,
                        user=self.pg_user,
                        password=self.pg_password,
                        port=self.pg_port)
            cursor = conn.cursor()

            columns = ", ".join([
                "email",
                "password",
                "token",
                "balance",
                "today_balance",
                "validated_steps"
            ])
            placeholders = ", ".join(["%s" for _ in columns.split(",")])
            insert_query = f"INSERT INTO users ({columns}) VALUES ({placeholders});"

            cursor.execute(insert_query, (email, password, token, balance, today_balance, validated_steps))
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

    def update(self, email, update_data):
        try:
            conn = psycopg2.connect(dbname=self.db_name,
                                    host=self.pg_host,
                                    user=self.pg_user,
                                    password=self.pg_password,
                                    port=self.pg_port)
            cursor = conn.cursor()
            update_columns = ", ".join(update_data.keys())
            update_values = ",".join(["%s" for _ in update_data.values()])
            update_query = f"UPDATE users SET {update_columns} = ({update_values}) WHERE email = %s;"
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
