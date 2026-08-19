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
    _insert_one = AsyncIOMotorCollection.insert_one

    async def _stamped_insert_one(self, doc, *args, **kwargs):
        return await _insert_one(self, _stamp_doc(doc, self.name), *args, **kwargs)

    AsyncIOMotorCollection.insert_one = _stamped_insert_one

    # Only patch insert_many / bulk_write if the collection class actually has
    # them (e.g. test fakes may implement only insert_one). Guard with getattr
    # so the patch never blows up on a minimal stub collection.
    _insert_many = getattr(AsyncIOMotorCollection, 'insert_many', None)
    if _insert_many is not None:
        async def _stamped_insert_many(self, docs, *args, **kwargs):
            stamped = [_stamp_doc(d, self.name) for d in docs]
            return await _insert_many(self, stamped, *args, **kwargs)
        AsyncIOMotorCollection.insert_many = _stamped_insert_many

    _bulk_write = getattr(AsyncIOMotorCollection, 'bulk_write', None)
    if _bulk_write is not None:
        async def _stamped_bulk_write(self, requests, *args, **kwargs):
            # Stamp documents inside insert/replace bulk operations so TTL indexes
            # also apply to bulk writes (previously only insert_one was patched).
            for op in requests:
                try:
                    if hasattr(op, 'document') and isinstance(op.document, dict):
                        _stamp_doc(op.document, self.name)
                    elif hasattr(op, 'replacement') and isinstance(op.replacement, dict):
                        _stamp_doc(op.replacement, self.name)
                except Exception:
                    pass
            return await _bulk_write(self, requests, *args, **kwargs)
        AsyncIOMotorCollection.bulk_write = _stamped_bulk_write
