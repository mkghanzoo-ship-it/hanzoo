"""Permission management system for bot owner and trusted admins."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger("PermissionManager")

# Global state for permissions
_permissions_state = {
    "owner_id": None,
    "trusted_admins": [],
    "config_path": None,
}


def initialize_permissions(config_path: Path) -> None:
    """Initialize the permission system with a config path."""
    _permissions_state["config_path"] = config_path
    load_trusted_admins()


def load_trusted_admins() -> None:
    """Load trusted admins and owner from config file."""
    config_path = _permissions_state["config_path"]
    
    if not config_path.exists():
        logger.warning("Trusted admins file not found. Creating with defaults.")
        _permissions_state["owner_id"] = None
        _permissions_state["trusted_admins"] = []
        save_trusted_admins()
        return
    
    try:
        with config_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        
        _permissions_state["owner_id"] = data.get("owner_id")
        _permissions_state["trusted_admins"] = data.get("trusted_admins", [])
        logger.info(f"Loaded permissions: owner={_permissions_state['owner_id']}, trusted={len(_permissions_state['trusted_admins'])} admins")
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse trusted_admins.json: {e}. Using defaults.")
        _permissions_state["owner_id"] = None
        _permissions_state["trusted_admins"] = []
        save_trusted_admins()
    except Exception as e:
        logger.error(f"Unexpected error loading permissions: {e}")
        _permissions_state["owner_id"] = None
        _permissions_state["trusted_admins"] = []


def save_trusted_admins() -> None:
    """Save trusted admins and owner to config file."""
    config_path = _permissions_state["config_path"]
    
    try:
        data = {
            "owner_id": _permissions_state["owner_id"],
            "trusted_admins": _permissions_state["trusted_admins"],
        }
        
        with config_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        
        logger.info("Permissions saved to disk.")
    except Exception as e:
        logger.error(f"Failed to save permissions: {e}")


def set_owner(owner_id: int) -> None:
    """Set the owner ID (call once during setup)."""
    _permissions_state["owner_id"] = owner_id
    save_trusted_admins()
    logger.info(f"[OWNER] Owner set to {owner_id}")


def is_owner(user_id: int) -> bool:
    """Check if user is the owner."""
    owner = _permissions_state["owner_id"]
    if owner is None:
        return False
    return user_id == owner


def is_trusted_admin(user_id: int) -> bool:
    """Check if user is a trusted admin or owner."""
    # Owner has all permissions
    if is_owner(user_id):
        return True
    
    return user_id in _permissions_state["trusted_admins"]


def is_valid_user_id(user_id: str) -> bool:
    """Validate that a user ID is a valid Discord ID (18-19 digits)."""
    try:
        uid = int(user_id)
        return 10**17 <= uid < 10**19  # Discord IDs are typically 18-19 digits
    except (ValueError, TypeError):
        return False


def add_trusted_admin(user_id: int) -> tuple[bool, str]:
    """
    Add a user to trusted admins.
    Returns (success, message).
    """
    if not is_valid_user_id(str(user_id)):
        return False, f"❌ Invalid user ID: {user_id}"
    
    if is_owner(user_id):
        return False, "❌ Cannot add owner as trusted admin (owner has all permissions by default)."
    
    if user_id in _permissions_state["trusted_admins"]:
        return False, f"⚠️ User {user_id} is already a trusted admin."
    
    _permissions_state["trusted_admins"].append(user_id)
    save_trusted_admins()
    logger.info(f"[OWNER] Added trusted admin: {user_id}")
    return True, f"✅ User {user_id} added as trusted admin."


def remove_trusted_admin(user_id: int) -> tuple[bool, str]:
    """
    Remove a user from trusted admins.
    Returns (success, message).
    """
    if not is_valid_user_id(str(user_id)):
        return False, f"❌ Invalid user ID: {user_id}"
    
    if is_owner(user_id):
        return False, "❌ Cannot remove owner from permissions."
    
    if user_id not in _permissions_state["trusted_admins"]:
        return False, f"⚠️ User {user_id} is not in trusted admins."
    
    _permissions_state["trusted_admins"].remove(user_id)
    save_trusted_admins()
    logger.info(f"[OWNER] Removed trusted admin: {user_id}")
    return True, f"✅ User {user_id} removed from trusted admins."


def get_trusted_admins_list() -> list[int]:
    """Get the list of all trusted admins."""
    return _permissions_state["trusted_admins"].copy()


def get_owner_id() -> Optional[int]:
    """Get the owner ID."""
    return _permissions_state["owner_id"]
