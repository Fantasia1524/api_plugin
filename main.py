import json
import re
from datetime import date, datetime, timedelta
from pathlib import Path

import aiohttp
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import random
from astrbot import logger
from astrbot.api.event import filter
from astrbot.api.star import Context, Star, register
from astrbot.core.platform import AstrMessageEvent
import astrbot.core.message.components as Comp

# 修改为 Windows 系统自带的字体路径
FONT_PATH = Path(r"C:\Windows\Fonts\simhei.ttf")  # 黑体字体路径
BACKGROUND_PATH = Path("data/plugins/astrbot_plugin_history_day/resource/background.png")  # 背景图片路径

TEMP_DIR = Path("data/plugins_data/astrbot_plugin_history_day")
TEMP_DIR.mkdir(parents=True, exist_ok=True)


@register("astrbot_plugin_history_day", "YourName", "查看历史上的某天发生的大事", "1.0.0")
class HistoryPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.month = date.today().strftime("%m")
        self.day = date.today().strftime("%d")

    @filter.regex(r'^历史上的.*')
    async def on_regex(self, event: AstrMessageEvent):
        """/历史上的{今天、昨天、明天、3月12日、3月12号、3.12}"""
        date_str: str = event.get_message_str().lstrip("历史上的").strip()
        today: date = datetime.now().date()
        if date_str in {"今天", "昨天", "明天"}:
            date_map = {
                "今天": today,
                "昨天": today - timedelta(days=1),
                "明天": today + timedelta(days=1),
            }
            self.month = f"{date_map[date_str].month:02d}"  # 保持两位数格式
            self.day = f"{date_map[date_str].day:02d}"  # 保持两位数格式
        else:
            patterns = [
                r"^(?P<month>\d{1,2})月(?P<day>\d{1,2})[日号]$",  # %m月%d日 或 %m月%d号
                r"^(?P<month>\d{1,2})\.(?P<day>\d{1,2})$",  # %m.%d
            ]
            for pattern in patterns:
                if match := re.match(pattern, date_str):
                    month = int(match.group("month"))
                    day = int(match.group("day"))
                    self.month = f"{month:02d}"  # 保持两位数格式
                    self.day = f"{day:02d}"  # 保持两位数格式
                    try:
                        datetime(year=today.year, month=month, day=day)  # 验证日期是否有效
                    except ValueError:
                        yield event.plain_result("输入的日期无效，请检查格式。")
                        return
                    break
            else:
                yield event.plain_result("输入的日期格式不支持，请使用“今天”、“昨天”、“明天”或“3月12日”等格式。")
                return

        image_name = f"{self.month}月{self.day}日.png"
        image_path = TEMP_DIR / image_name
        if image_path.exists():
            yield event.image_result(str(image_path))
            return

        try:
            text = await self.get_events_on_history(self.month)
            if not text:
                yield event.plain_result("获取历史数据失败，请稍后再试。")
                return

            data = self.html_to_json_func(text)
            today_ = f"{self.month}{self.day}"
            f_today = f"{self.month.lstrip('0') or '0'}月{self.day.lstrip('0') or '0'}日"
            reply = f"【历史上的今天-{f_today}】\n"
            if today_ in data.get(self.month, {}):
                events = data[self.month][today_]
                for event_data in events:
                    str_year = event_data.get("year", "")
                    str_title = event_data.get("title", "")
                    reply += f"{str_year} {str_title}\n"
            else:
                reply += "今天没有历史上的大事记录。"

            image_bytes = self.text_to_image_bytes(reply)
            image = Image.open(BytesIO(image_bytes))
            image.save(image_path)

            chain = [Comp.Image.fromBytes(image_bytes)]
            yield event.chain_result(chain)
        except Exception as e:
            logger.error(f"处理历史上的今天请求时出错: {e}")
            yield event.plain_result("抱歉，处理请求时出错了，请稍后再试！")

    @staticmethod
    async def get_events_on_history(month: str) -> str:
        try:
            async with aiohttp.ClientSession() as client:
                url = f"https://baike.baidu.com/cms/home/eventsOnHistory/{month}.json"
                async with client.get(url) as response:
                    response.encoding = "utf-8"
                    return await response.text()
        except Exception as e:
            logger.error(f"获取历史数据失败: {e}")
            return ""

    @staticmethod
    def html_to_json_func(text: str) -> dict:
        """处理返回的HTML内容，转换为JSON格式"""
        text = text.replace("</a>", "").replace("\n", "")

        while True:
            address_head = text.find("<a target=")
            address_end = text.find(">", address_head)
            if address_head == -1 or address_end == -1:
                break
            text_middle = text[address_head:address_end + 1]
            text = text.replace(text_middle, "")

        address_head = 0
        while True:
            address_head = text.find('"desc":', address_head)
            address_end = text.find('"cover":', address_head)
            if address_head == -1 or address_end == -1:
                break
            text_middle = text[address_head + 8:address_end - 2]
            address_head = address_end
            text = text.replace(text_middle, "")

        address_head = 0
        while True:
            address_head = text.find('"title":', address_head)
            address_end = text.find('"festival"', address_head)
            if address_head == -1 or address_end == -1:
                break
            text_middle = text[address_head + 9:address_end - 2]
            if '"' in text_middle:
                text_middle = text_middle.replace('"', " ")
                text = text[:address_head + 
