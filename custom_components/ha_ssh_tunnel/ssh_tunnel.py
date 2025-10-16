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
                _LOGGER.info(f"try key")
                return key_class.from_private_key_file(path)
            except paramiko.ssh_exception.SSHException:
                _LOGGER.error(f"try except")
                continue
        raise Exception("Unsupported or invalid SSH key format")

    def _run(self):
        key = self.load_private_key(self.private_key)
        while self._running:
            client = None
            try:
                client = paramiko.SSHClient()
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                client.connect(
                    self.host,
                    port=self.port,
                    username=self.user,
                    pkey=key,
                    banner_timeout=30,
                    auth_timeout=30,
                    timeout=10
                )
                _LOGGER.info(f"Connected to {self.host}:{self.port}")

                transport = client.get_transport()
                # Слушаем локальный порт и прокидываем через SSH
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    sock.bind(("127.0.0.1", self.local_port))
                    sock.listen(5)
                    _LOGGER.info(f"Local port {self.local_port} listening → {self.remote_host}:{self.remote_port}")

                    while self._running and transport.is_active():
                        r, _, _ = select.select([sock], [], [], 1)
                        if sock in r:
                            client_socket, _ = sock.accept()
                            chan = transport.open_channel(
                                "direct-tcpip",
                                (self.remote_host, self.remote_port),
                                client_socket.getsockname()
                            )
                            self._forward(chan, client_socket)

            except Exception as e:
                _LOGGER.error(f"SSH tunnel error: {e}")
                time.sleep(5)
            finally:
                if client:
                    client.close()

            if not self.auto_reconnect:
                break

    def _forward(self, chan, client_socket):
        try:
            while True:
                r, _, _ = select.select([chan, client_socket], [], [])
                if client_socket in r:
                    data = client_socket.recv(1024)
                    if not data:
                        break
                    chan.send(data)
                if chan in r:
                    data = chan.recv(1024)
                    if not data:
                        break
                    client_socket.send(data)
        except Exception as e:
            _LOGGER.warning(f"Forwarding error: {e}")
        finally:
            chan.close()
            client_socket.close()

    def stop(self):
        self._running = False
        _LOGGER.info("SSH tunnel stopped.")
