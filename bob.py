#!.venv/bin/python3


from fbchat import Client
from fbchat.models import User, Message, ThreadType
from ast import literal_eval
from threading import Thread, Lock
from datetime import datetime, timedelta
import os
from time import sleep
import dateutil.parser
from inspect import getdoc
from importlib import import_module
import sys
import traceback




"""
Global
"""

groupsdir  = 'groups/'
current_cmd_lock = Lock()
current_cmd = None

if not os.path.isdir(groupsdir):
    os.makedirs(groupsdir)


groups     = {}
commands   = {}
cronjobs   = []
suspended_cronjobs = []
callbacks  = {
    'newgroup' : [],
    'loadgroup': [],
    'message'  : [],
}



"""
Classes
"""

class Group():

    valid_types = [int, list, dict, str, float]

    def __init__(self, client, id):
        self.id = id
        self.client = client
        groups = client.fetchGroupInfo(id)
        u = {}
        for k in groups[str(id)].participants:
            vs = client.fetchUserInfo(k)
            for v in vs:
                u[int(k)] = vs[v]
                break
        self.users = u
        self.names = {k: u[k].first_name.lower() for k in u}
        self.ids = {self.names[k]: k for k in u}
        self.tells = {k: [] for k in self.users}
        self.dir = groupsdir + str(id) + '/'
        if not os.path.isdir(self.dir):
            os.makedirs(self.dir)

    def _getdir(self, name):
        d = self.dir + '/' + current_cmd.name + '/'
        if not os.path.isdir(d):
            os.makedirs(d)
        return d
    
    def load(self, name):
        with open(self._getdir(current_cmd.name) + name, 'r') as f:
            return literal_eval(f.read())

    def store(self, name, obj):
        t = type(obj)
        if t not in self.valid_types:
            raise TypeError("Can't store object of type '%s'" % str(t))
        with open(self._getdir(current_cmd.name) + name, 'w') as f:
            f.write(str(obj))

    def delete(self, name):
        os.remove(self._getdir(current_cmd.name) + name)

    def liststore(self):
        return os.listdir(self._getdir(current_cmd.name))

    def get_name(self, uid):
        return self.names[uid]

    def get_id(self, name):
        return self.ids[name]

    def send(self, message):
        self.client.send(message, thread_id=str(self.id), thread_type=ThreadType.GROUP)


class Command():

    def __init__(self, cmd):
        self.name = sys.modules[cmd.__module__].__name__
        self._cmd = cmd
        self.doc  = getdoc(cmd)

    def __call__(self, *args, **kwargs):
        global current_cmd
        with current_cmd_lock:
            current_cmd = self
            self._cmd(*args, **kwargs)
            current_cmd = None

    def __str__(self):
        return self.name + ':' + self._cmd.__name__


class Bob(Client):
    """
    Bob da bot is kawaii :3
    """

    def __init__(self, user, password):
        for m in os.listdir('modules'):
            if m[-3:] == '.py':
                print('Importing %s...' % m[:-3])
                import_module('modules.' + m[:-3])
        super().__init__(user, password)
        self.crond = Thread(target=self.cron, daemon=True)
        self.crond.start()


    def cron(self):
        while True:
            for c in cronjobs:
                try:
                    for g in groups:
                        c(groups[g])
                except Exception as e:
                    print("'%s' crashed! %s: %s" % (c, str(e), e))
                    print(traceback.format_exc())
                    print("Suspending '%s' 30 seconds to prevent excessive log spam" % c)
                    suspended_cronjobs.append([c, 0])
                    cronjobs.remove(c)
            for s in suspended_cronjobs:
                s[1] += 1
                if s[1] >= 30:
                    print("Unsuspending '%s'" % str(s[0]))
                    cronjobs.append(s[0])
                    suspended_cronjobs.remove(s)
            sleep(1)


    def get_group(self, thread_id):
        if thread_id not in groups:
            self.wave(thread_id=thread_id, thread_type=ThreadType.GROUP)
            g = Group(self, thread_id)
            groups[thread_id] = g
            for c in callbacks['loadgroup']:
                c(g)
        return groups[thread_id]


    def parse_command(self, author_id, thread_id, msg):
        text = msg.text
        if text[0] != '!':
            return None
        t = text.split(' ', 1)
        if len(t) == 2:
            cmd, body = t
        else:
            cmd, body = t[0], None
        cmd = cmd[1:]

        if cmd == 'help':
            if body == None:
                msg = '\n'.join([c.name for c in commands])
            else:
                msg = getdoc(commands.get(body, "Command '%s' does not exist" % body))
            return Message(text=msg)
        elif cmd == 'debug':
            if body == 'users':
                groups = self.fetchGroupInfo(thread_id)
                names = []
                for id in groups:
                    users = groups[id].participants
                for id, user in self.fetchUserInfo(*users).items():
                    names.append(user.first_name.lower())
                return Message(text=', '.join(names))
            else:
                return Message(text='Usage: !debug users')
        else:
            if cmd not in commands:
                return Message(text="No command named '%s'" % cmd)
            msg.text = body
            commands[cmd](self.get_group(thread_id), msg)

        return None

    def onMessage(self, message_object, author_id, thread_id, thread_type, **kwargs):
        author_id  = int(author_id)
        thread_id  = int(thread_id)
        message_object.author = int(message_object.author)

        g = self.get_group(thread_id)
        for c in callbacks['message']:
            c(g, message_object)

        if message_object.text != None:
            reply = self.parse_command(author_id, thread_id, message_object)
            if reply:
                self.send(reply, thread_id=thread_id, thread_type=thread_type)



"""
Decorators
"""

def command(name):
    if name in commands:
        raise KeyError("Command '%s' has already been registered" % name)
    def d(f):
        commands[name] = Command(f)
    return d

def cron(time):
    def d(f):
        cronjobs.append(Command(f))
    return d

def loadgroup(f):
    callbacks['loadgroup'].append(Command(f))

def newgroup(f):
    callbacks['newgroup'].append(Command(f))

def message(f):
    callbacks['message'].append(Command(f))
