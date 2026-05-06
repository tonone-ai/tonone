# FIXTURE FILE — intentionally vulnerable for Warden scan tests.
# DO NOT deploy or import this file in production code.

import hashlib
import random
import subprocess


def get_user(user_input):
    # SQL injection: string formatting in query
    query = "SELECT * FROM users WHERE name = '%s'" % user_input
    return query


def run_command(cmd):
    # command injection: shell=True with user input
    subprocess.run(cmd, shell=True)


def hash_password(password):
    # weak hashing: MD5 for passwords
    return hashlib.md5(password.encode()).hexdigest()


def generate_token():
    # insecure random: random module not cryptographically secure
    return str(random.randint(100000, 999999))


SECRET_KEY = "hardcoded-secret-key-abc123"  # hardcoded secret
