from fbchat.models import Message, ThreadType
from datetime import datetime, timedelta
import dateutil.parser
import bob


reminders = {}


def parse_time(time):
    d = {'w': 0, 'd': 0, 'h': 0, 'm': 0, 's': 0}
    i, j = 0, 0
    while len(time) != i:
        if time[i] == '-':
            i += 1
        while time[i].isdecimal():
            i += 1
        d[time[i]] += int(time[j:i])
        i += 1
        j = i
    return timedelta(weeks=d['w'], days=d['d'], hours=d['h'], minutes=d['m'], seconds=d['s'])


class Reminder():

    def __init__(self, id, date, body):
        self.id   = id
        self.date = date
        self.body = body

    def __str__(self):
        return self.body

    def __repr__(self):
        return self.body + ' @ ' + str(self.date)

    def tolist(self):
        return [self.date.isoformat(), self.body]

    def fromlist(d):
        return Reminder(dateutil.parser.parse(d[0]), d[1])


@bob.command('remind')
def remind(group, msg):
    rl = reminders[group]
    time, body = msg.text.split(' ', 1)
    r = Reminder(len(rl), datetime.now() + parse_time(time), body)
    rl.append(r)
    group.store(str(r.id), r.tolist())


@bob.cron(1)
def cron(group):
    if group in reminders:
        now = datetime.now()
        rl = reminders[group]
        for r in rl:
            if r.date < now:
                group.send(Message(text=str(r)))
                rl.remove(r)


@bob.loadgroup
def loadgroup(group):
    reminders[group] = []
    for id in group.liststore():
        group.load(id)


@bob.newgroup
def newgroup(group):
    reminders[group] = []
