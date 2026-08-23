"""Loop-aware MongoDB access shared by Getszy backend modules.

Motor binds a client to the first asyncio event loop that uses it. A production
ASGI worker has one long-lived loop, while the regression suite uses several
short-lived loops and TestClient lifecycles. This proxy creates one client per
active loop and closes the previous one when the loop changes, preventing a
closed test loop from poisoning later application work.
"""
import asyncio
import os
from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient

mongo_url = os.environ['MONGO_URL']
db_name = os.environ.get('DB_NAME', 'getszy_db')


class _LoopAwareMongo:
    def __init__(self, url: str, database_name: str):
        self._url = url
        self._database_name = database_name
        self._client: AsyncIOMotorClient | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

    def _active_client(self) -> AsyncIOMotorClient:
        # Collection classes are inspected and monkeypatched by synchronous tests
        # before an async handler is entered. Use that thread's policy loop for
        # inspection, then replace the client once a real running loop takes over.
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                # Python 3.11+ may clear the policy loop after asyncio.run().
                # Create one only for synchronous collection inspection; an async
                # handler will replace this client on its own running loop.
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        if self._client is None or self._loop is not loop:
            if self._client is not None:
                self._client.close()
            self._client = AsyncIOMotorClient(self._url)
            self._loop = loop
        return self._client

    def database(self):
        return self._active_client()[self._database_name]

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
        self._client = None
        self._loop = None


class _DatabaseProxy:
    """Expose Motor database methods lazily on the loop currently handling a call."""
    def __init__(self, manager: _LoopAwareMongo):
        self._manager = manager

    def __getattr__(self, name: str) -> Any:
        return getattr(self._manager.database(), name)

    def __getitem__(self, name: str) -> Any:
        return self._manager.database()[name]


_manager = _LoopAwareMongo(mongo_url, db_name)
client = _manager
db = _DatabaseProxy(_manager)


def serialize_doc(doc):
    """Remove Mongo _id and ensure JSON serializable."""
    if doc is None:
        return None
    return {key: value for key, value in doc.items() if key != '_id'}
