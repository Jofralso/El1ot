"""
Security Subsystem

Manages users, targets, permissions, and audit logging.
All YAML-backed configuration files live in the security/ directory.

Before any system interaction, ELIOT checks:
1. User is authenticated
2. User has required permissions
3. Target is whitelisted
4. Action is logged to audit trail
"""

import os
import time
import uuid
import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class User:
    id: str = ""
    name: str = ""
    role: str = "unknown"
    permissions: List[str] = field(default_factory=list)
    face_embeddings: List[List[float]] = field(default_factory=list)
    voice_embedding: Optional[List[float]] = None
    active: bool = True
    created_at: float = field(default_factory=time.time)


@dataclass
class Target:
    id: str = ""
    name: str = ""
    address: str = ""
    description: str = ""
    approved: bool = False
    approved_by: str = ""
    approved_at: float = 0.0
    tags: List[str] = field(default_factory=list)


@dataclass
class AuditEntry:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    user_id: str = ""
    action: str = ""
    target: str = ""
    tool: str = ""
    result: str = ""
    details: Dict[str, Any] = field(default_factory=dict)


class SecurityManager:
    """Manages users, targets, permissions, and audit trail."""

    def __init__(self, security_dir: str = "security"):
        self._security_dir = security_dir
        self._users: Dict[str, User] = {}
        self._targets: Dict[str, Target] = {}
        self._audit_log: List[AuditEntry] = []
        self._permissions: Dict[str, List[str]] = {}
        os.makedirs(security_dir, exist_ok=True)

    def load(self):
        """Load all security configs from YAML files."""
        self._load_users()
        self._load_targets()
        self._load_permissions()
        logger.info(
            f"Security loaded: {len(self._users)} users, "
            f"{len(self._targets)} targets, "
            f"{sum(len(v) for v in self._permissions.values())} permission rules"
        )

    def save(self):
        """Persist all security configs to YAML files."""
        self._save_users()
        self._save_targets()
        self._save_permissions()

    # ── Users ────────────────────────────────────────────────

    def _load_users(self):
        path = os.path.join(self._security_dir, "users.yaml")
        if not os.path.exists(path):
            self._create_default_users()
            return
        try:
            import yaml
            with open(path) as f:
                data = yaml.safe_load(f) or {}
            for uid, ud in data.get("users", {}).items():
                self._users[uid] = User(id=uid, **ud)
        except Exception as e:
            logger.error(f"Failed to load users: {e}")
            self._create_default_users()

    def _create_default_users(self):
        owner_id = str(uuid.uuid4())
        self._users[owner_id] = User(
            id=owner_id,
            name="Owner",
            role="owner",
            permissions=["admin", "read", "write", "execute", "network", "voice", "vision"],
        )
        self._save_users()

    def _save_users(self):
        import yaml
        path = os.path.join(self._security_dir, "users.yaml")
        data = {"users": {}}
        for uid, user in self._users.items():
            data["users"][uid] = {
                "name": user.name,
                "role": user.role,
                "permissions": user.permissions,
                "active": user.active,
            }
        with open(path, "w") as f:
            yaml.dump(data, f, default_flow_style=False)

    def authenticate_user(self, user_id: str) -> Optional[User]:
        user = self._users.get(user_id)
        if user and user.active:
            return user
        return None

    def add_user(self, user: User):
        self._users[user.id] = user
        self._save_users()

    def remove_user(self, user_id: str):
        self._users.pop(user_id, None)
        self._save_users()

    def get_users(self) -> List[User]:
        return list(self._users.values())

    # ── Targets ──────────────────────────────────────────────

    def _load_targets(self):
        path = os.path.join(self._security_dir, "targets.yaml")
        if not os.path.exists(path):
            self._save_targets()
            return
        try:
            import yaml
            with open(path) as f:
                data = yaml.safe_load(f) or {}
            for tid, td in data.get("targets", {}).items():
                self._targets[tid] = Target(id=tid, **td)
        except Exception as e:
            logger.error(f"Failed to load targets: {e}")

    def _save_targets(self):
        import yaml
        path = os.path.join(self._security_dir, "targets.yaml")
        data = {"targets": {}}
        for tid, target in self._targets.items():
            data["targets"][tid] = {
                "name": target.name,
                "address": target.address,
                "description": target.description,
                "approved": target.approved,
                "tags": target.tags,
            }
        with open(path, "w") as f:
            yaml.dump(data, f, default_flow_style=False)

    def approve_target(self, target: Target):
        target.approved = True
        target.approved_at = time.time()
        self._targets[target.id] = target
        self._save_targets()

    def remove_target(self, target_id: str):
        self._targets.pop(target_id, None)
        self._save_targets()

    def get_approved_targets(self) -> List[Target]:
        return [t for t in self._targets.values() if t.approved]

    def is_target_approved(self, address: str) -> bool:
        return any(
            t.approved and t.address == address
            for t in self._targets.values()
        )

    def get_targets(self) -> List[Target]:
        return list(self._targets.values())

    # ── Permissions ──────────────────────────────────────────

    def _load_permissions(self):
        path = os.path.join(self._security_dir, "permissions.yaml")
        if not os.path.exists(path):
            self._create_default_permissions()
            return
        try:
            import yaml
            with open(path) as f:
                data = yaml.safe_load(f) or {}
            self._permissions = data.get("roles", {})
        except Exception as e:
            logger.error(f"Failed to load permissions: {e}")
            self._create_default_permissions()

    def _create_default_permissions(self):
        self._permissions = {
            "owner": ["admin", "read", "write", "execute", "network", "voice", "vision", "plan", "analyze", "research", "code", "document", "knowledge_search"],
            "approved": ["read", "voice", "knowledge_search"],
            "unknown": [],
        }
        self._save_permissions()

    def _save_permissions(self):
        import yaml
        path = os.path.join(self._security_dir, "permissions.yaml")
        with open(path, "w") as f:
            yaml.dump({"roles": self._permissions}, f, default_flow_style=False)

    def check_permission(self, role: str, permission: str) -> bool:
        role_perms = self._permissions.get(role, [])
        return permission in role_perms or "admin" in role_perms

    # ── Audit ────────────────────────────────────────────────

    def log_audit(self, entry: AuditEntry):
        self._audit_log.append(entry)
        logger.info(
            f"AUDIT: user={entry.user_id} action={entry.action} "
            f"target={entry.target} tool={entry.tool} result={entry.result}"
        )

    def get_audit_log(self, limit: int = 100, user_id: Optional[str] = None) -> List[AuditEntry]:
        entries = self._audit_log
        if user_id:
            entries = [e for e in entries if e.user_id == user_id]
        return entries[-limit:]

    def authorize_action(
        self,
        user_id: str,
        action: str,
        target_address: str = "",
        tool: str = "",
    ) -> bool:
        user = self.authenticate_user(user_id)
        if not user:
            self.log_audit(AuditEntry(
                user_id=user_id,
                action=action,
                target=target_address,
                tool=tool,
                result="denied",
                details={"reason": "user_not_authenticated"},
            ))
            return False

        if not self.check_permission(user.role, action):
            self.log_audit(AuditEntry(
                user_id=user_id,
                action=action,
                target=target_address,
                tool=tool,
                result="denied",
                details={"reason": "insufficient_permissions"},
            ))
            return False

        if target_address and not self.is_target_approved(target_address):
            self.log_audit(AuditEntry(
                user_id=user_id,
                action=action,
                target=target_address,
                tool=tool,
                result="denied",
                details={"reason": "target_not_whitelisted"},
            ))
            return False

        self.log_audit(AuditEntry(
            user_id=user_id,
            action=action,
            target=target_address,
            tool=tool,
            result="allowed",
        ))
        return True


# Global security manager instance
_security_manager: Optional[SecurityManager] = None


def get_security_manager() -> SecurityManager:
    global _security_manager
    if _security_manager is None:
        from core.config import settings
        _security_manager = SecurityManager(security_dir=settings.security_dir)
        _security_manager.load()
    return _security_manager
