"""Provides the Protocol class which is a subclass of
twisted.protocols.basic.LineReceiver until I figure out how the Telnet protocol
works."""

import logging
import sys
from twisted.protocols.basic import LineReceiver
from attr import attrs, attrib, Factory
from .caller import Caller


@attrs
class Protocol(LineReceiver):
    """
    Server protocol

    Instances of this class represent a connection to the server.

    server
    An instance of gsb.Server.
    host
    The IP address of the host which this connection represents.
    port
    The port number this connection is connected on.
    """

    server = attrib()
    host = attrib()
    port = attrib()
    _parser = attrib()
    encode_args = attrib(
        default=Factory(
            lambda: (sys.getdefaultencoding(), 'replace')
        )
    )
    decode_args = attrib(
        default=Factory(
            lambda: (sys.getdefaultencoding(), 'ignore')
        )
    )

    @property
    def parser(self):
        """Get the current parser."""
        return self._parser

    @parser.setter
    def parser(self, value):
        """Set self._parser."""
        old_parser = self._parser
        if old_parser is not None:
            old_parser.on_detach(self, value)
        if value is None:
            value = self.server.default_parser
            self.logger.warning(
                'Attempting to set parser to None. Falling back on %r.',
                self.server.default_parser
            )
        self._parser = value
        value.on_attach(self, old_parser)

    def lineReceived(self, line):
        """Handle a line from a client."""
        line = line.decode(*self.decode_args)
        self.parser.handle_line(self, line)

    def connectionMade(self):
        """Call self.server.on_connect."""
        self.logger = logging.getLogger(
            '%s:%d' % (
                self.host,
                self.port
            )
        )
        self.server.connections.append(self)
        self.server.on_connect(Caller(self))
        if self.parser is not None:
            self.parser.on_attach(self, None)

    def connectionLost(self, reason):
        """Call self.server.on_disconnect."""
        if self in self.server.connections:
            self.server.connections.remove(self)
        self.logger.info(
            'Disconnected: %s',
            reason.getErrorMessage()
        )
        self.server.on_disconnect(Caller(self))

    def notify(self, *args, **kwargs):
        """Notify this connection of something."""
        self.server.notify(self, *args, **kwargs)
