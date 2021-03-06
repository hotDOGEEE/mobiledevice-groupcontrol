# coding: utf-8
# codeskyblue 2020/06/03
#

__all__ = ['SafeStreamSocket', 'PlistSocket']

import logging
import os
import socket
import ssl
import struct
import plistlib
import threading

from typing import Union, Any
from .exceptions import *
from ._proto import PROGRAM_NAME

logger = logging.getLogger(PROGRAM_NAME)

_n = [0]
_nlock = threading.Lock()

def get_uniq_id() -> int:
    with _nlock:
        _n[0] += 1
        return _n[0]


class SafeStreamSocket:
    def __init__(self, addr: Union[str, tuple, socket.socket,
                                   Any]):
        """
        Args:
            addr: can be /var/run/usbmuxd or (localhost, 27015)
        """
        self._id = get_uniq_id()
        self._sock = None
        if isinstance(addr, socket.socket):
            self._sock = addr
            return
        if isinstance(addr, SafeStreamSocket):  # copy self
            self._sock = addr._sock
            return

        if isinstance(addr, str):
            if ':' in addr:
                host, port = addr.split(":", 1)
                addr = (host, int(port))
                family = socket.AF_INET
            elif os.path.exists(addr):
                family = socket.AF_UNIX
            else:
                raise MuxError("socket unix:{} unable to connect".format(addr))
        else:
            family = socket.AF_INET
        self._sock = socket.socket(family, socket.SOCK_STREAM)
        self._sock.connect(addr)
        

    @property
    def id(self) -> int:
        return self._id

    def get_socket(self) -> socket.socket:
        return self._sock

    def recv(self, bufsize: int = 4096) -> bytes:
        return self._sock.recv(bufsize)

    def recvall(self, size: int) -> bytearray:
        buf = bytearray()
        while len(buf) < size:
            chunk = self._sock.recv(size - len(buf))
            if not chunk:
                raise MuxError("socket connection broken")
            buf.extend(chunk)
        return buf

    def sendall(self, data: Union[bytes, bytearray]) -> int:
        return self._sock.sendall(data)

    def switch_to_ssl(self, pemfile):
        """ wrap socket to SSLSocket """
        # logger.debug("Switch to ssl")
        assert os.path.isfile(pemfile)
        self._dup_sock = self._sock.dup()
        
        context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
        context.load_cert_chain(pemfile, keyfile=pemfile)
        context.check_hostname = False
        ssock = context.wrap_socket(self._sock, server_hostname="iphone.localhost")
        
        self._sock = ssock

    def close(self):
        logger.debug("Socket %d closed", self._id)
        self._sock.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
    
    #def __del__(self):
    #    self.close()


class PlistSocket(SafeStreamSocket):
    def __init__(self, addr: str, tag: int = 0):
        super().__init__(addr)
        if isinstance(addr, PlistSocket):
            self._tag = addr._tag
            self._first = addr._first
        else:
            self._tag = tag
            self._first = True
        self.prepare()

    def prepare(self):
        pass

    def is_secure(self):
        return isinstance(self._sock, ssl.SSLSocket)

    def send_packet(self, payload: dict, message_type: int = 8):
        """
        Args:
            payload: required

            # The following args only used in the first request
            message_type: 8 (Plist)
            tag: int
        """
        #if self.is_secure():
        #    logger.debug(secure_text + " send: %s", payload)
        #else:
        logger.debug("SEND(%d): %s", self.id, payload)

        body_data = plistlib.dumps(payload)
        if self._first:  # first package
            length = 16 + len(body_data)
            header = struct.pack(
                "IIII", length, 1, message_type,
                self._tag)  # version: 1, request: 8(?), tag: 1(?)
        else:
            header = struct.pack(">I", len(body_data))
        self.sendall(header + body_data)

    def recv_packet(self, header_size=None) -> dict:
        if self._first or header_size == 16:  # first receive
            header = self.recvall(16)
            (length, version, resp, tag) = struct.unpack("IIII", header)
            length -= 16  # minus header length
            self._first = False
        else:
            header = self.recvall(4)
            (length, ) = struct.unpack(">I", header)

        body_data = self.recvall(length)
        payload = plistlib.loads(body_data)
        if 'PairRecordData' in payload:
            logger.debug("Recv pair record data ...")
        else:
            # if self.is_secure():
            #    logger.debug(secure_text + " recv" + Color.END + ": %s",
            #                 payload)
            # else:
            logger.debug("RECV(%d): %s", self.id, payload)
        return payload

    def send_recv_packet(self, payload: dict) -> dict:
        self.send_packet(payload)
        return self.recv_packet()
