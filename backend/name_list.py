"""名单管理"""
from config import cfg

DANGER_KEYWORDS = ["删", "格式化", "清空", "关机", "重启", "卸载", "密码", "支付", "转账", "付款"]

def is_blacklisted(name: str) -> bool:
    return any(k in name for k in cfg.config.get("blacklist", []))

def is_whitelisted(name: str) -> bool:
    return any(k in name for k in cfg.config.get("whitelist", []))

def is_dangerous(message: str) -> bool:
    return any(k in message for k in DANGER_KEYWORDS + cfg.config.get("transfer_keywords", ["转人工", "找人", "人工客服"]))

def should_auto_reply(name: str, message: str) -> str:
    """
    返回: 'skip' / 'auto' / 'notify' / 'pending'
    """
    if is_blacklisted(name):
        return "skip"
    if is_whitelisted(name):
        if is_dangerous(message):
            return "pending"  # 高危，等人工确认
        return "notify"       # 普通需求，自动回+通知
    return "auto"             # 普通，静默自动回

def needs_human_approval(name: str, message: str) -> bool:
    """白名单或高危关键词 → 需要人工确认"""
    if is_whitelisted(name):
        return True
    return is_dangerous(message)
