from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from backend import api


class FakeDB:
    def __init__(self, document):
        self.document = document
        self.deleted = False
        self.committed = False

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def scalar(self, *args):
        return self.document

    def delete(self, *args):
        self.deleted = True

    def commit(self):
        self.committed = True


def test_system_document_delete_cannot_reach_mutation(monkeypatch):
    db = FakeDB(SimpleNamespace(is_system=True))
    monkeypatch.setattr(api, "DB", lambda: db)
    with pytest.raises(HTTPException) as error:
        api.delete_document("system")
    assert error.value.status_code == 403
    assert not db.deleted and not db.committed


def test_ordinary_document_delete_commits(monkeypatch):
    db = FakeDB(SimpleNamespace(is_system=False))
    monkeypatch.setattr(api, "DB", lambda: db)
    assert api.delete_document("ordinary") == {"deleted": "ordinary"}
    assert db.deleted and db.committed
