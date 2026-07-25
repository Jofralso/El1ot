"""
Tests for the Security subsystem.
"""

import os
import tempfile
import pytest
from security import SecurityManager, User, Target, AuditEntry


@pytest.fixture
def security_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def sm(security_dir):
    manager = SecurityManager(security_dir=security_dir)
    manager.load()
    return manager


class TestUsers:
    def test_default_owner_created(self, sm):
        users = sm.get_users()
        assert len(users) >= 1
        owner = [u for u in users if u.role == "owner"]
        assert len(owner) == 1

    def test_authenticate_valid_user(self, sm):
        users = sm.get_users()
        owner = [u for u in users if u.role == "owner"][0]
        result = sm.authenticate_user(owner.id)
        assert result is not None
        assert result.name == "Owner"

    def test_authenticate_invalid_user(self, sm):
        result = sm.authenticate_user("nonexistent-id")
        assert result is None

    def test_add_and_remove_user(self, sm):
        user = User(id="test-user", name="Test", role="approved", permissions=["read"])
        sm.add_user(user)
        assert len(sm.get_users()) == 2
        sm.remove_user("test-user")
        assert len(sm.get_users()) == 1


class TestTargets:
    def test_approve_target(self, sm):
        target = Target(id="t1", name="Localhost", address="127.0.0.1", approved=False)
        sm.approve_target(target)
        assert sm.is_target_approved("127.0.0.1")

    def test_unapproved_target(self, sm):
        assert not sm.is_target_approved("192.168.1.1")

    def test_remove_target(self, sm):
        target = Target(id="t1", name="Localhost", address="127.0.0.1")
        sm.approve_target(target)
        sm.remove_target("t1")
        assert not sm.is_target_approved("127.0.0.1")


class TestPermissions:
    def test_owner_has_admin(self, sm):
        assert sm.check_permission("owner", "admin")
        assert sm.check_permission("owner", "read")
        assert sm.check_permission("owner", "execute")

    def test_approved_limited(self, sm):
        assert sm.check_permission("approved", "read")
        assert not sm.check_permission("approved", "execute")
        assert not sm.check_permission("approved", "admin")

    def test_unknown_no_permissions(self, sm):
        assert not sm.check_permission("unknown", "read")


class TestAudit:
    def test_authorize_action(self, sm):
        users = sm.get_users()
        owner = [u for u in users if u.role == "owner"][0]
        target = Target(id="t1", name="Localhost", address="127.0.0.1")
        sm.approve_target(target)
        result = sm.authorize_action(owner.id, "read", "127.0.0.1")
        assert result is True

    def test_deny_unknown_user(self, sm):
        result = sm.authorize_action("nonexistent", "read")
        assert result is False

    def test_audit_log_recorded(self, sm):
        users = sm.get_users()
        owner = [u for u in users if u.role == "owner"][0]
        sm.authorize_action(owner.id, "read")
        log = sm.get_audit_log()
        assert len(log) >= 1
