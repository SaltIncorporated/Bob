from fbchat.models import Message
from datetime import datetime, timedelta
import os
from time import sleep
import bob
import uuid
import dateutil.parser


events = {}


def parse_time(time):
    d = {'w': 0, 'd': 0, 'h': 0, 'm': 0, 's': 0}
    i, j = 0, 0
    while len(time) != i:
        if time[i] == '-':
            i += 1
        while time[i].isdecimal():
            i += 1
        d[time[i]] = int(time[j:i])
        i += 1
        j = i
    return timedelta(weeks=d['w'], days=d['d'], hours=d['h'], minutes=d['m'], seconds=d['s'])


class Event():
    
    def __init__(self, date, body):
        self.body = body
        self.date = date
        self.uids = []
        self.resetReminder()

    def add_user(self, uid):
        if uid not in self.uids:
            self.uids.append(uid)
            return True
        return False

    def remove_user(self, uid):
        if uid in self.user_ids:
            self.uids.remove(uid)
            return True
        return False

    def resetReminder(self):
        now = datetime.now()
        delta = self.date - now
        if delta.days >= 7:
            delta.days = delta.days // 7 * 7
            delta.hours = self.date.hours
            delta.minutes = self.date.minutes
            delta.seconds = 0
            delta.microseconds = 0
        elif delta.days >= 1:
            delta = timedelta(days = 1)
        elif delta.seconds > 12 * 3600:
            delta = timedelta(hours = 12)
        elif delta.seconds > 3600:
            delta = timedelta(hours = 1)
        else:
            delta = timedelta(hours = 0)
        self.due = self.date - delta

    def is_reminder_due(self):
        return datetime.now() >= self.due

    def has_begun(self):
        return datetime.now() >= self.date

    def tolist(self):
        return [self.date.isoformat(), self.body, self.uids]

    def fromlist(list):
        e = Event(dateutil.parser.parse(list[0]), list[1])
        e.uids = list[2]
        return e


@bob.command('event')
def event(group, msg):
    usage_text = 'Usage:\event <list|info|join|leave> <event index...>\nevent add <datedelta> <hour:minute> <title...>'
    body = msg.text
    dirty_event = None

    if body == None:
        group.send(Message(text=usage_text))
        return

    if ' ' in body:
        cmd, body = body.split(' ', 1)
        if cmd == 'add':
            time, h_and_m, body = body.split(' ', 2)
            hour, minute = h_and_m.split(':', 1)
            now  = datetime.now()
            date = datetime(year=now.year, month=now.month, day=now.day+parse_time(time).days, hour=int(hour), minute=int(minute))
            dirty_event = Event(date, body)
            id = len(events[group])
            while id in events[group]:
                id += 1
            events[group][id] = dirty_event
            msg = Message(text='Added event \'%s\'' % body)
        elif cmd == 'info':
            i = int(body)
            e = events[group][i]
            msg = '%s (ID: %d)\nWhen: %s\nParticipants: %s' % (e.body, i, str(e.time), ', '.join([g.get_name(u) for u in e.uids]))
            msg = Message(text=msg)
        elif cmd == 'join':
            i = int(body)
            e = events[group][i]
            msg = ('Joined event \'%s\'' % e.body) if e.add_user(author_id) else ('Already joined \'%s\'' % e.body)
            dirty_event = e
            msg = Message(text=msg)
        elif cmd == 'leave':
            i = int(body)
            e = events[group][i]
            msg = ('Left event \'%s\'' % e.body) if e.remove_user(author_id) else ('Already left or not joined \'%s\'' % e.body)
            dirty_event = e
            msg = Message(text=msg)
        else:
            msg = Message(text=usage_text)
    else:
        if body == 'list':
            if len(events[group]) == 0:
                msg = Message(text='No events')
            else:
                l = ['%d: %s @ %s (%d participants)' % (i, e.body, str(e.date), len(e.uids)) for i,e in events[group].items()]
                msg = Message(text='\n'.join(l))
        else:
            msg = Message(text=usage_text)

    if dirty_event != None:
        group.store(str(id), dirty_event.tolist())
    if msg != None:
        group.send(msg)


@bob.cron(1)
def cron(group):
    if group in events:
        dellist = []
        for i,e in events[group].items():
            if e.is_reminder_due():
                if e.has_begun():
                    msg = 'Event \'%s\' has started' % e.body
                else:
                    msg = 'Upcoming event: %s\n\nWhen: %s' % (e.body, str(e.time))
                group.send(Message(text=msg))
                dellist.append(i)
                group.delete(str(i))
        for i in dellist:
            del events[group][i]


@bob.loadgroup
def loadgroup(group):
    events[group] = { int(id): Event.fromlist(group.load(id)) for id in group.liststore() }


@bob.newgroup
def newgroup(group):
    events[group] = {}
