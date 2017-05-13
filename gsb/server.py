"""Contains the Server base class."""

import logging
from re import search
from datetime import datetime
from twisted.internet import reactor
from attr import attrs, attrib, Factory
from .caller import Caller, DontStopException
from .factory import Factory as ServerFactory
from .command import Command

logger = logging.getLogger(__name__)


@attrs
class Server:
    """
    A game server instance.
    This class represents an instance of a game server.

    port
    The port the server should run on.
    interface
    The interface the server should listen on.
    factory
    The Twisted factory to use for dishing out connections.
    command_class
    The class for new commands.
    commands
    A list of the commands added to this server with the @Server.command
    decorator.
    connections
    A list of protocol objects that are connected.
    """

    port = attrib(default=Factory(lambda: 4000))
    interface = attrib(default=Factory(lambda: '0.0.0.0'))
    factory = attrib(default=Factory(lambda: None), repr=False)
    command_class = attrib(default=Factory(lambda: Command))
    commands = attrib(default=Factory(list), repr=False, init=False)
    connections = attrib(default=Factory(list), init=False, repr=False)
    started = attrib(default=Factory(lambda: None))

    def __attrs_post_init__(self):
        if self.factory is None:
            self.factory = ServerFactory(self)

    def is_banned(self, host):
        """Determine if host is banned. Simply returns False by default."""
        return False

    def run(self):
        """Run the server."""
        if self.started is None:
            self.started = datetime.now()
        reactor.listenTCP(
            self.port,
            self.factory,
            interface=self.interface
        )
        logger.info(
            'Now listening for connections on %s:%d.',
            self.interface,
            self.port
        )
        self.on_start(Caller(None))
        reactor.addSystemEventTrigger(
            'before',
            'shutdown',
            self.on_stop,
            Caller(None)
        )
        reactor.run()
        logger.info('Finished after %s.', datetime.now() - self.started)

    def on_start(self, caller):
        """The server has started. The passed instance of Caller does nothing,
        but ensures compatibility with the other events. Is called from
        Server.run."""
        pass

    def on_stop(self, caller):
        """The server is about to stop. The passed instance of Caller does
        nothing but maintains compatibility with the other events. Is scheduled
        when Server.run is used."""
        pass

    def on_command(self, caller):
        """A command was sent."""
        return True

    def on_error(self, caller):
        """An exception was raised by a command. In this instance caller has
        an extra exception attribute which holds the exception which was
        thrown."""
        self.notify(caller.connection, 'There was an error with your command.')

    def on_connect(self, caller):
        """A connection has been established. Send welcome message ETC."""
        pass

    def on_disconnect(self, caller):
        """A client has disconnected."""
        pass

    def handle_line(self, connection, line):
        """Handle a line of text from a connection."""
        # Let's build an instance of Caller:
        caller = Caller(connection, text=line)
        if self.on_command(caller):
            for cmd in self.commands:
                caller.match = search(cmd.regexp, line)
                if caller.match is not None and (
                    cmd.allowed is None or cmd.allowed(caller)
                ):
                    try:
                        cmd.func(caller)
                    except DontStopException:
                        continue
                    except Exception as e:
                        caller.exception = e
                        logger.exception(
                            'Command %r threw an error:',
                            cmd
                        )
                        logger.exception(e)
                        self.on_error(caller)
                    break
            else:
                caller.match = None
                self.huh(caller)

    def huh(self, caller):
        """Notify the connection that we have no idea what it's on about."""
        self.notify(caller.connection, "I don't understand that.")

    def format_text(self, text, *args, **kwargs):
        """Format text for use with notify and broadcast."""
        if args:
            text = text % args
        if kwargs:
            text = text % kwargs
        return text

    def notify(self, connection, text, *args, **kwargs):
        """Notify connection of text formatted with args and kwargs."""
        if connection is not None:
            connection.sendLine(
                self.format_text(
                    text,
                    *args,
                    **kwargs
                ).encode()
            )

    def broadcast(self, text, *args, **kwargs):
        """Notify all connections."""
        text = self.format_text(text, *args, **kwargs)
        for con in self.connections:
            self.notify(con, text)

    def command(self, *args, **kwargs):
        """Add a command to the commands list. Passes all arguments to
        command_class."""
        def inner(func):
            """Add func to self.commands."""
            cmd = self.command_class(func, *args, **kwargs)
            logger.info(
                'Adding command %r.',
                cmd
            )
            self.commands.append(cmd)
            return cmd
        return inner

    def disconnect(self, connection):
        """Disconnect a connection."""
        connection.transport.loseConnection()
