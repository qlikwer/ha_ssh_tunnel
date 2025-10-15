import threading
import time
import paramiko
import socket
import select
import logging

_LOGGER = logging.getLogger(__name__)

class SSHTunnel:
    def __init__(self, host, port, user, private_key, local_port, remote_host, remote_port, auto_reconnect=True):
        self.host = host
        self.port = port
        self.user = user
        self.private_key = private_key
        self.local_port = local_port
        self.remote_host = remote_host
        self.remote_port = remote_port
        self.auto_reconnect = auto_reconnect
        self._running = False
        self._thread = None

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def load_private_key(self, path):
        for key_class in (paramiko.Ed25519Key, paramiko.RSAKey, paramiko.ECDSAKey, paramiko.DSSKey):
            try:
                return key_class.from_private_key_file(path)
            except paramiko.ssh_exception.SSHException:
                continue
        raise Exception("Unsupported or invalid SSH key format")

    def _run(self):
        while self._running:
            try:
                key = self.load_private_key(self.private_key)
                client = paramiko.SSHClient()
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                client.connect(self.host, port=self.port, username=self.user, pkey=key)
                _LOGGER.info(f"Connected to {self.host}:{self.port}")

                transport = client.get_transport()
                transport.request_port_forward("", self.local_port)
                while self._running and transport.is_active():
                    chan = transport.accept(1)
                    if chan:
                        self._forward(chan)
                client.close()
            except Exception as e:
                _LOGGER.error(f"SSH tunnel error: {e}")
                if not self.auto_reconnect:
                    break
                time.sleep(5)

    def _forward(self, chan):
        try:
            sock = socket.socket()
            sock.connect((self.remote_host, self.remote_port))
            while True:
                r, _, _ = select.select([sock, chan], [], [])
                if sock in r:
                    data = sock.recv(1024)
                    if not data:
                        break
                    chan.send(data)
                if chan in r:
                    data = chan.recv(1024)
                    if not data:
                        break
                    sock.send(data)
        except Exception as e:
            _LOGGER.warning(f"Forwarding error: {e}")
        finally:
            chan.close()
            sock.close()

    def stop(self):
        self._running = False
        _LOGGER.info("SSH tunnel stopped.")
