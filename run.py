#!.venv/bin/python3


from bob import Bob
from filelock import FileLock
from os import sys, path
from login import email, password

lock = FileLock("lock")
try:
    lock.acquire(timeout=10)
except Timeout:
    exit(0)
sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))
client = Bob(email, password)
try:
    client.listen()
except KeyboardInterrupt:
    client.logout()
