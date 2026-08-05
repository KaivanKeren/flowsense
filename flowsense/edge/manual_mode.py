import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional
import time

logger = logging.getLogger(__name__)

class OverrideState(Enum):
    MANUAL_ALL_RED = "MANUAL_ALL_RED"
    MANUAL_FLASH = "MANUAL_FLASH"
    MANUAL_GREEN_PHASE = "MANUAL_GREEN_PHASE"
    AUTO = "AUTO"

class ManualOverrideController:
    """Manages manual overrides for traffic signals."""

    def __init__(self, timeout_seconds: int = 3600):
        self.state = OverrideState.AUTO
        self.active_phase: Optional[int] = None
        self.lock_owner: Optional[str] = None
        self.lock_expiry: float = 0
        self.timeout_seconds = timeout_seconds
        self.audit_log: List[Dict] = []

    def lock(self, user: str) -> bool:
        """Lock the controller for manual override."""
        now = time.time()
        if self.lock_owner and self.lock_owner != user and now < self.lock_expiry:
            logger.warning(f"Lock denied for {user}: locked by {self.lock_owner}")
            return False
        
        self.lock_owner = user
        self.lock_expiry = now + self.timeout_seconds
        self._log_audit(user, "LOCK", {"timeout": self.timeout_seconds})
        return True

    def unlock(self, user: str) -> bool:
        """Unlock the controller, reverting to AUTO."""
        if self.lock_owner != user and self.lock_owner is not None:
             logger.warning(f"Unlock denied for {user}: locked by {self.lock_owner}")
             return False
             
        self.lock_owner = None
        self.lock_expiry = 0
        self.state = OverrideState.AUTO
        self.active_phase = None
        self._log_audit(user, "UNLOCK", {})
        return True

    def set_override(self, user: str, state: OverrideState, phase: Optional[int] = None) -> bool:
        """Set a manual override state."""
        if self.lock_owner != user:
            logger.warning(f"Override denied for {user}: not lock owner")
            return False
            
        if time.time() > self.lock_expiry:
            logger.warning(f"Override denied for {user}: lock expired")
            self.unlock(user)
            return False

        if state == OverrideState.MANUAL_GREEN_PHASE and phase is None:
            logger.error("Phase must be specified for MANUAL_GREEN_PHASE")
            return False

        self.state = state
        self.active_phase = phase if state == OverrideState.MANUAL_GREEN_PHASE else None
        
        self._log_audit(user, "SET_OVERRIDE", {"state": state.value, "phase": phase})
        # Reset timeout on activity
        self.lock_expiry = time.time() + self.timeout_seconds
        return True
        
    def _log_audit(self, user: str, action: str, details: Dict):
        """Record an audit log entry."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user": user,
            "action": action,
            "details": details
        }
        self.audit_log.append(entry)
        logger.info(f"AUDIT: {entry}")

    def get_status(self) -> Dict:
        """Get the current controller status."""
        now = time.time()
        is_locked = self.lock_owner is not None and now < self.lock_expiry
        
        if not is_locked and self.state != OverrideState.AUTO:
             # Lock expired while in override, auto-revert
             self.state = OverrideState.AUTO
             self.active_phase = None
             self.lock_owner = None
             
        return {
            "state": self.state.value,
            "active_phase": self.active_phase,
            "is_locked": is_locked,
            "lock_owner": self.lock_owner,
            "time_remaining": max(0, int(self.lock_expiry - now)) if is_locked else 0
        }
