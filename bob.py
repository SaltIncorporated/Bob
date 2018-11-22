#!.venv/bin/python3

from filelock import FileLock, Timeout
lock = FileLock("lock")
try:
    lock.acquire(timeout=10)
except Timeout:
    exit(0)


from fbchat import Client
from fbchat.models import *

class Tell():
    def __init__(self, author, body):
        self.author = author
        self.body   = body

    def __str__(self):
        return '{} (from: {})'.format(self.body, self.author)


class Bob(Client):

    def __init__(self, user, password):
        super().__init__(user, password)
        self.tells = {}

    def send_tells(self, author_id):
        if author_id not in self.tells:
            return []
        for id, user in self.fetchUserInfo(author_id).items():
            author = user.first_name.lower()
        tells = [Message(text='{}: {}'.format(author, str(t))) for t in self.tells[author_id]]
        self.tells[author_id] = []
        return tells

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

            groups = self.fetchGroupInfo(thread_id)
            for id in groups:
                users = groups[id].participants
            reply_id, author = None, None

            for id, user in self.fetchUserInfo(*users).items():
                name = user.first_name.lower()
                if name == reply_to:
                    reply_id = id
                if id == author_id:
                    author = name

            if not reply_id:
                return Message(text='User \'{}\' not found in this group'.format(reply_to))

            if reply_id not in self.tells:
                self.tells[reply_id] = []
            self.tells[reply_id].append(Tell(author, body))

        elif cmd == 'stout':
            return Message(text='Stout %s!' % body)

        elif cmd == 'ketter':
            return Message(text='https://youtu.be/lXhU9zacjzw')

        elif cmd == 'help':
            a = ['tell <name> <message...>',
                 'stout <name>',
                 'ketter',
                 'help',
                 'debug users']
            return Message(text='\n'.join(a))

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
            return Message(text='Heil Bob')

        return None

    def onMessage(self, message_object, author_id, thread_id, thread_type, **kwargs):
        for tell in self.send_tells(author_id):
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
