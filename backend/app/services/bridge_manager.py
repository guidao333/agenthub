"""桥接会话管理 - 会话生命周期"""

import logging
import time
from sqlalchemy.orm import Session

from ..models import BridgeSession
from ..utils.helpers import now_timestamp

logger = logging.getLogger("agenthub.bridge")


def clean_expired_sessions(db: Session):
    """清理过期会话（30 分钟无活动）"""
    now_ms = int(time.time() * 1000)
    expired = (db.query(BridgeSession)
               .filter(BridgeSession.status == "active")
               .filter(now_ms - BridgeSession.last_activity > 30 * 60 * 1000)
               .all())

    for session in expired:
        session.status = "expired"
        session.updated_at = now_timestamp()
        logger.info(f"Bridge session expired: {session.id} (inactive for 30min)")

    if expired:
        db.commit()

    return len(expired)
