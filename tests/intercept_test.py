"""Test intercepts."""

from pytest import raises
from attr import attrs
from gsb import Server, Protocol, Caller, intercept


class MenuItem1(Exception):
    pass


class MenuItem2(Exception):
    pass


class MenuItem3(Exception):
    pass


class NotifyException(Exception):
    """So we know what gets notified."""
    pass


@attrs
class _TestProtocol(Protocol):
    """Override sendLine."""
    def __attrs_post_init__(self):
        self.line = None
        self.command = None

    def sendLine(self, line):
        line = line.decode()
        self.line = line
        raise NotifyException(line)


def good_command(caller):
    assert caller.text == 'good'
    assert caller.connection is p
    p.command = 'good'


def bad_command(caller):
    assert caller.text == 'bad'
    assert caller.connection is p
    p.command = 'bad'


def menu_command_1(caller):
    raise MenuItem1


def menu_command_2(caller):
    raise MenuItem2


def menu_command_3(caller):
    raise MenuItem3


s = Server()
p = _TestProtocol(s, '127.0.0.1', 1987)  # Pretend protocol.
p.connectionMade()
assert p.line is None


def test_notify():
    """This should go in server_test.py, but what the hell!"""
    text = 'Testing, testing, 1, 2, 3.'
    with raises(NotifyException):
        p.notify(text)
    assert p.line == text


def test_handle_line():
    s.command('^good$')(good_command)
    s.command('^bad$')(bad_command)
    p.lineReceived('good'.encode())
    assert p.command == 'good'
    with raises(NotifyException):
        p.lineReceived('nothing'.encode())
    p.lineReceived('bad'.encode())
    assert p.command == 'bad'


def test_menuitem():
    i = intercept.MenuItem('testing', print)
    assert i.text == 'testing'
    assert i.func == print


def test_menu():
    i1 = intercept.MenuItem('First Thing', menu_command_1)
    i2 = intercept.MenuItem('second Thing', menu_command_2)
    i3 = intercept.MenuItem('Third Thing', menu_command_3)
    m = intercept.Menu('Test Menu', [i1, i2, i3])
    assert m.title == 'Test Menu'
    c = Caller(p)
    c.text = '$'
    assert m.match(c) is i3
    c.text = 'first'
    assert m.match(c) == i1
    c.text = 'thing'  # Multiple results.
    with raises(NotifyException):
        m.match(c)
    c.match = 'nothing'
    with raises(NotifyException):
        assert m.match(c) is None
