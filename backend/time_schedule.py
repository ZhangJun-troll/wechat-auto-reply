"""时段调度 - 根据时间返回不同轮询间隔"""
from datetime import datetime
from config import cfg


def get_current_interval() -> float:
    schedule = cfg.config.get("time_schedule", [])
    now = datetime.now()
    now_min = now.hour * 60 + now.minute

    for slot in schedule:
        start_h, start_m = map(int, slot["start"].split(":"))
        end_h, end_m = map(int, slot["end"].split(":"))
        s, e = start_h * 60 + start_m, end_h * 60 + end_m
        hit = (s <= now_min <= e) if s <= e else (now_min >= s or now_min <= e)
        if hit:
            return slot["interval"]

    return cfg.config["auto_pilot"]["poll_interval"]


def get_slot_info() -> dict:
    schedule = cfg.config.get("time_schedule", [])
    now = datetime.now()
    now_min = now.hour * 60 + now.minute

    for slot in schedule:
        start_h, start_m = map(int, slot["start"].split(":"))
        end_h, end_m = map(int, slot["end"].split(":"))
        s, e = start_h * 60 + start_m, end_h * 60 + end_m
        hit = (s <= now_min <= e) if s <= e else (now_min >= s or now_min <= e)
        if hit:
            return {"name": slot.get("name", ""), "interval": slot["interval"],
                    "start": slot["start"], "end": slot["end"]}

    return {"name": "默认", "interval": cfg.config["auto_pilot"]["poll_interval"],
            "start": "00:00", "end": "23:59"}
