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

    def __init__(self, date, body):
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
    i = len(rl)
    while i in rl:
        i += 1
    rl[i] = Reminder(datetime.now() + parse_time(time), body)
    group.store(str(i), rl[i].tolist())


@bob.cron(1)
def cron(group):
    if group in reminders:
        now = datetime.now()
        rl = reminders[group]
        to_del = []
        for i,r in rl.items():
            if r.date < now:
                group.send(Message(text=str(r)))
                to_del.append(i)
                group.delete(str(i))
        for i in to_del:
            del rl[i]


@bob.loadgroup
def loadgroup(group):
    reminders[group] = { int(i): Reminder.fromlist(group.load(i)) for i in group.liststore() }


@bob.newgroup
def newgroup(group):
    reminders[group] = []
