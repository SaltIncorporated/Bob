from fbchat.models import Message
import bob


tells = {}


class Tell():

    def __init__(self, author, recipient, body):
        self.author    = author
        self.recipient = recipient
        self.body      = body

    def __str__(self):
        return '%s: %s (from: %s)' % (self.recipient, self.body, self.author);

    def tolist(self):
        return [self.author, self.recipient, self.body]

    def fromlist(d):
        return Tell(*d)


@bob.message
def onMessage(group, message):
    if group in tells:
        a = message.author
        t = tells[group]
        if a in t:
            for m in t[a]:
                group.send(Message(text=str(m)))
            del t[a]
            group.store(str(a), [])


@bob.command('tell')
def tell(group, msg):
    body = msg.text
    if ' ' not in body:
        group.send(Message(text='Usage: !tell <user> <message...>'))
    else:
        reply_to, body = body.split(' ', 1)
        author = group.get_name(msg.author)
        try:
            recipient_id = group.get_id(reply_to)
        except KeyError:
            group.send(Message(text='User \'{}\' not found in this group'.format(reply_to)))

        t = tells[group]
        if recipient_id not in t:
            l = []
            t[recipient_id] = l
        else:
            l = t[recipient_id]
        tell = (Tell(author, reply_to, body))
        l.append(tell)
        group.store(str(recipient_id), [tl.tolist() for tl in l])
        


@bob.loadgroup
def loadgroup(group):
    t = {}
    tells[group] = t
    for id in group.liststore():
        t[int(id)] = [Tell.fromlist(t) for t in group.load(id)]

@bob.newgroup
def newgroup(group):
    tells[group] = {}
