from fbchat.models import Message
import bob


@bob.command('stout')
def stout(group, msg):
    """
    >:(
    """
    group.send(Message(text='Stout ' + msg.text + '!'))


@bob.command('ketter')
def ketter(group, msg):
    """
    Fucking HERETICS
    """
    group.send(Message(text='https://youtu.be/lXhU9zacjzw'))
