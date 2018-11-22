#!.venv/bin/python3

from filelock import FileLock, Timeout
lock = FileLock("lock")
try:
    lock.acquire(timeout=10)
except Timeout:
    exit(0)


from fbchat import Client
from fbchat.models import User, Message, ThreadType
from ast import literal_eval
from threading import Thread
from datetime import datetime, timedelta
import os
from time import sleep


class Tell():

    def __init__(self, author, recipient, body):
        self.author = author
        self.recipient = recipient
        self.body   = body

    def __str__(self):
        return '%s: %s (from: %s)' % (self.recipient, self.body, self.author);

    def serialize(self):
        return [self.author, self.recipient, self.body]

    def deserialize(d):
        return Tell(*literal_eval(d))


class Reminder():

    def __init__(self, time, body):
        self.time = time
        self.body = body

    def __str__(self):
        return self.body

    def __repr__(self):
        return self.body + ' @ ' + str(self.time)

    def serialize(self):
        return [self.time.isoformat(), self.body]

    def deserialize(d):
        return Reminder(datetime.fromisoformat(d[0]), d[1])

class Group():

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
        self.names_to_id = {self.names[k]: k for k in u}
        self.tells = {k: [] for k in self.users}
        dir = 'groups/%d/' % id
        if not os.path.isdir(dir):
            os.makedirs(dir + 'tells')
        for k in self.users:
            path = '%s/tells/%d' % (dir, k)
            try:
                with open(path, 'r') as f:
                    tells = literal_eval(f.read())
                    for t in tells:
                        self.tells[k].append(Tell.deserialize(t))
            except FileNotFoundError:
                with open(path, 'w') as f:
                    f.write('[]')
        self.reminders = []
        try:
            with open('groups/%d/reminders' % self.id, 'r') as f:
                r = literal_eval(f.read())
                for i in r:
                    self.reminders.append(Reminder.deserialize(i))
        except FileNotFoundError:
            with open('groups/%d/reminders' % self.id, 'w') as f:
                f.write('[]')

    def add_tell(self, author_id, recipient, message):
        recipient_id = self.names_to_id[recipient]
        t = Tell(self.names[author_id], recipient, message)
        self.tells[recipient_id].append(t)
        with open('groups/%d/tells/%d' % (self.id, recipient_id), 'w') as f:
            f.write(str([t.serialize() for t in self.tells[recipient_id]])) 
    
    def get_tells(self, user_id):
        t = self.tells[user_id]
        self.tells[user_id] = []
        with open('groups/%d/tells/%d' % (self.id, user_id), 'w') as f:
            f.write('[]')
        return t

    def add_reminder(self, time, body, now):
        d = {'w': 0, 'd': 0, 'h': 0, 'm': 0, 's': 0}
        i, j = 0, 0
        while len(time) != i:
            while time[i].isdecimal():
                i += 1
            d[time[i]] = int(time[j:i])
            i += 1
            j = i
        time = now + timedelta(weeks=d['w'], days=d['d'], hours=d['h'], minutes=d['m'], seconds=d['s'])
        self.reminders.append(Reminder(time, body))
        with open('groups/%d/reminders' % self.id, 'w') as f:
            f.write(str([r.serialize() for r in self.reminders]))

    def get_reminders(self):
        now = datetime.now()
        rem = []
        for r in self.reminders:
            if r.time < now:
                rem.append(r)
                self.reminders.remove(r)
        with open('groups/%d/reminders' % self.id, 'w') as f:
            f.write(str([r.serialize() for r in self.reminders]))
        return rem


class Bob(Client):
    """
    Bob da bot is kawaii :3
    """

    """ Special """
    def __init__(self, user, password):
        super().__init__(user, password)
        self.groups = {}
        self.reminderd = Thread(target=self.send_reminders, daemon=True)
        self.reminderd.start()

    """ Daemons """
    def send_reminders(self):
        while True:
            for i in self.groups:
                g = self.groups[i]
                for r in g.get_reminders():
                    self.send(Message(text=str(r)), thread_id=g.id, thread_type=ThreadType.GROUP)
            sleep(1)

    """ General """
    def get_tells(self, author_id, thread_id):
        if thread_id not in self.groups:
            return []
        return [Message(text=str(t)) for t in self.groups[thread_id].get_tells(author_id)]

    def get_group(self, thread_id):
        if thread_id not in self.groups:
            self.groups[thread_id] = Group(self, thread_id)
        return self.groups[thread_id]

    def parse_command(self, author_id, thread_id, text):
        if text[0] != '!':
            return None
        t = text.split(' ', 1)
        if len(t) == 2:
            cmd, body = t
        else:
            cmd, body = t[0], None
        cmd = cmd[1:]

        if cmd == 'tell':
            reply_to, body = body.split(' ', 1)
            try:
                self.get_group(thread_id).add_tell(author_id, reply_to, body)
            except KeyError:
                return Message(text='User \'{}\' not found in this group'.format(reply_to))

        elif cmd == 'stout':
            return Message(text='Stout %s!' % body)

        elif cmd == 'ketter':
            return Message(text='https://youtu.be/lXhU9zacjzw')

        elif cmd == 'help':
            a = ['tell <name> <message...>',
                 'stout <name>',
                 'ketter',
                 'help',
                 'debug <users|reminders>']
            return Message(text='\n'.join(a))

        elif cmd == 'remind':
            now = datetime.now()
            time, body = body.split(' ', 1)
            self.get_group(thread_id).add_reminder(time, body, now)

        elif cmd == 'debug':
            if body == 'users':
                groups = self.fetchGroupInfo(thread_id)
                names = []
                for id in groups:
                    users = groups[id].participants
                for id, user in self.fetchUserInfo(*users).items():
                    names.append(user.first_name.lower())
                return Message(text=', '.join(names))

            elif body == 'reminders':
                s = '\n'.join([repr(r) for r in self.get_group(thread_id).reminders])
                return Message(text=s if s != '' else 'No reminders')

            else:
                return Message(text='Usage: !debug users')

        else:
            return Message(text='Heil Bob')

        return None

    def onMessage(self, message_object, author_id, thread_id, thread_type, **kwargs):
        author_id = int(author_id)
        thread_id = int(thread_id)

        for tell in self.get_tells(author_id, thread_id):
            self.send(tell, thread_id=thread_id, thread_type=thread_type)

        cmd = message_object.text
        reply = self.parse_command(author_id, thread_id, cmd)
        if reply:
            self.send(reply, thread_id=thread_id, thread_type=thread_type)



client = Bob('***REMOVED***', '***REMOVED***')
try:
    client.listen()
except KeyboardInterrupt:
    client.logout()
