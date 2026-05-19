"""计费服务 - 余额管理、冻结、扣款"""

import json
import logging
from sqlalchemy.orm import Session

from ..config import (
    DEVELOPER_CUT_RATE, PLATFORM_CUT_RATE,
    SELF_KEY_DEVELOPER_CUT, SELF_KEY_PLATFORM_CUT,
    NEW_USER_BONUS, FREE_TRIAL_PER_CAP,
)
from ..models import User, Capability, CallLog, Invoice
from ..utils.errors import ErrorCode, AppException
from ..utils.helpers import now_timestamp, parse_json_field, serialize_json

logger = logging.getLogger("agenthub.billing")


def pre_check_balance(user: User, capability: Capability, db: Session) -> bool:
    """
    余额预检：检查用户是否有足够余额

    Returns:
        True: 余额足够
        Raises AppException: 余额不足
    """
    # 免费能力
    if capability.price <= 0:
        return True

    # 检查是否有免费试用额度
    quota_used = parse_json_field(user.free_quota_used, {})
    today = now_timestamp()[:10]  # YYYY-MM-DD
    cap_key = f"{capability.id}_{today}"
    used_count = quota_used.get(cap_key, 0)
    if used_count < FREE_TRIAL_PER_CAP:
        return True

    # 检查余额
    available = user.balance - user.frozen_balance
    if available < capability.price:
        raise AppException(ErrorCode.BILL_INSUFFICIENT_BALANCE,
                           detail=f"需要 ¥{capability.price}，可用余额 ¥{available}")

    return True


def freeze_amount(user: User, amount: float, db: Session):
    """冻结金额"""
    user.balance -= amount
    user.frozen_balance += amount
    db.commit()


def unfreeze_amount(user: User, amount: float, db: Session):
    """解冻金额"""
    user.balance += amount
    user.frozen_balance -= amount
    db.commit()


def charge(user: User, amount: float, db: Session):
    """实际扣款"""
    user.frozen_balance -= amount
    db.commit()


def record_trial_usage(user: User, capability_id: int, db: Session):
    """记录免费试用"""
    quota_used = parse_json_field(user.free_quota_used, {})
    today = now_timestamp()[:10]
    cap_key = f"{capability_id}_{today}"
    quota_used[cap_key] = quota_used.get(cap_key, 0) + 1
    user.free_quota_used = serialize_json(quota_used)
    db.commit()


def distribute_revenue(call_log: CallLog, capability: Capability, db: Session):
    """
    分配开发者收益

    - 平台 LLM 模式: 开发者 70%, 平台 30%
    - 自备 Key 模式: 开发者 85%, 平台 15%
    """
    if capability.llm_mode == "self_key":
        dev_cut = SELF_KEY_DEVELOPER_CUT
    else:
        dev_cut = DEVELOPER_CUT_RATE

    revenue = call_log.charged * dev_cut

    # 给开发者加收益
    developer = db.query(User).filter(User.id == capability.developer_id).first()
    if developer:
        developer.earnings += revenue
        logger.info(f"Revenue distributed: Cap#{capability.id} → Dev#{developer.id}: ¥{revenue}")

    db.commit()
