"""TTL retention helpers.

MongoDB TTL indexes ONLY expire documents whose indexed field is a real BSON
Date. Several call sites store dates as ISO *strings*, which makes a TTL index
silently never fire. ``_stamp_doc`` attaches a true ``datetime`` ``createdAt``
to inserts of retention-managed collections; ``_install_createdAt_stamp`` wires
it into motor at the class level (motor hands out a fresh collection object per
``db.X`` access, so an instance-level wrap would not persist).
"""
import datetime as _dt

_TTL_COLLECTIONS = {'request_logs', 'audit_logs', 'video_jobs',
                    'deploy_jobs', 'credit_transactions'}


def _stamp_doc(doc, coll_name):
    if (coll_name in _TTL_COLLECTIONS and isinstance(doc, dict)
            and 'createdAt' not in doc):
        doc['createdAt'] = _dt.datetime.now(_dt.timezone.utc)
    return doc


def _install_createdAt_stamp():
    from motor.motor_asyncio import AsyncIOMotorCollection
    _orig = AsyncIOMotorCollection.insert_one

    async def _stamped_insert(self, doc, *args, **kwargs):
        return await _orig(self, _stamp_doc(doc, self.name), *args, **kwargs)

    AsyncIOMotorCollection.insert_one = _stamped_insert
