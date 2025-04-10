from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import requests  # 用于发送 HTTP 请求

# ALAPI 的历史上的今天 API 地址
HISTORY_TODAY_API_URL = "https://v1.alapi.cn/api/today"

@register("alapi_history_today", "YourName", "调用 ALAPI 的历史上的今天 API", "1.0.0")
class HistoryTodayPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
    
    @filter.command("today")
    async def history_today(self, event: AstrMessageEvent):
        '''调用 ALAPI 的历史上的今天 API，返回历史上的今天发生的大事'''
        try:
            # 发送 HTTP GET 请求到 ALAPI 的历史上的今天 API
            # 在这里加入你的 API 密钥
            response = requests.get(HISTORY_TODAY_API_URL, params={"token": "vnurbnwb72uu6vrlyfblc261apn5wv"})
            response.raise_for_status()  # 检查请求是否成功
            
            # 解析返回的 JSON 数据
            data = response.json()
            if data.get("code") == 200:
                events = data.get("data", [])
                if events:
                    # 格式化历史事件
                    formatted_events = []
                    for event_data in events:
                        title = event_data.get("title", "无标题")
                        content = event_data.get("content", "无内容")
                        formatted_events.append(f"【{title}】\n{content}\n")
                    
                    # 回复用户
                    yield event.plain_result(f"【历史上的今天】\n{''.join(formatted_events)}")
                else:
                    yield event.plain_result("今天没有历史上的大事记录。")
            else:
                yield event.plain_result(f"API 返回错误：{data.get('msg', '未知错误')}")        
        except Exception as e:
            logger.error(f"调用历史上的今天 API 失败: {e}")
            yield event.plain_result("抱歉，调用 API 时出错了，请稍后再试！")
    
    async def terminate(self):
        '''插件终止时的清理工作'''
        logger.info("HistoryTodayPlugin 已停止运行")
