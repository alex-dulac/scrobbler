"""Private loopback backend owned by the Flutter desktop process."""
import asyncio
import fcntl
import json
import os
import socket
import sys
from contextlib import contextmanager

import uvicorn

from core.desktop_storage import state_directory


@contextmanager
def managed_instance_lock():
    directory = state_directory()
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / "backend.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise RuntimeError("A managed scrobbler backend is already running") from error
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


class DesktopServer(uvicorn.Server):
    async def startup(self, sockets=None):
        await super().startup(sockets=sockets)
        if self.started:
            print(json.dumps({"event": "ready", "host": "127.0.0.1",
                              "port": sockets[0].getsockname()[1], "pid": os.getpid()}), flush=True)


async def serve():
    server = DesktopServer(uvicorn.Config("server:app", log_level="info", timeout_graceful_shutdown=10))
    loop = asyncio.get_running_loop()

    def parent_input():
        if not os.read(sys.stdin.fileno(), 4096):
            loop.remove_reader(sys.stdin.fileno())
            server.should_exit = True

    loop.add_reader(sys.stdin.fileno(), parent_input)
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
            listener.bind(("127.0.0.1", 0))
            await server.serve(sockets=[listener])
    finally:
        loop.remove_reader(sys.stdin.fileno())


def main():
    if not os.environ.get("APP_TOKEN"):
        raise SystemExit("APP_TOKEN must be provided by the desktop parent")
    os.environ["SCROBBLER_MANAGED"] = "1"
    with managed_instance_lock():
        asyncio.run(serve())


if __name__ == "__main__":
    main()
