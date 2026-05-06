"""
时间格式化工具类
提供时间格式化和解析方法
"""
from copy import deepcopy
from datetime import date, datetime
from typing import Any, Optional, List, Union

try:
    from dateutil.parser import parse
    HAS_DATEUTIL = True
except ImportError:
    HAS_DATEUTIL = False


class TimeFormatUtil:
    """
    时间格式化工具类
    """

    @classmethod
    def format_time(cls, time_info: Union[str, datetime], fmt: str = '%Y-%m-%d %H:%M:%S') -> str:
        """
        格式化时间字符串或datetime对象为指定格式

        Args:
            time_info: 时间字符串或datetime对象
            fmt: 格式化格式，默认为'%Y-%m-%d %H:%M:%S'

        Returns:
            str: 格式化后的时间字符串
        """
        if isinstance(time_info, datetime):
            format_date = time_info.strftime(fmt)
        else:
            try:
                if HAS_DATEUTIL:
                    dt = parse(time_info)
                    format_date = dt.strftime(fmt)
                else:
                    # 如果没有 dateutil，尝试直接解析常见格式
                    dt = datetime.fromisoformat(time_info.replace('Z', '+00:00'))
                    format_date = dt.strftime(fmt)
            except Exception:
                format_date = time_info

        return format_date

    @classmethod
    def parse_date(cls, time_str: str) -> Union[date, str]:
        """
        解析时间字符串提取日期部分

        Args:
            time_str: 时间字符串

        Returns:
            Union[date, str]: 日期部分或原始字符串
        """
        try:
            if HAS_DATEUTIL:
                dt = parse(time_str)
                return dt.date()
            else:
                dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                return dt.date()
        except Exception:
            return time_str

    @classmethod
    def format_time_dict(cls, time_dict: dict, fmt: str = '%Y-%m-%d %H:%M:%S') -> dict:
        """
        格式化时间字典

        Args:
            time_dict: 时间字典
            fmt: 格式化格式，默认为'%Y-%m-%d %H:%M:%S'

        Returns:
            dict: 格式化后的时间字典
        """
        copy_time_dict = deepcopy(time_dict)
        for k, v in copy_time_dict.items():
            if isinstance(v, (str, datetime)):
                copy_time_dict[k] = cls.format_time(v, fmt)
            elif isinstance(v, dict):
                copy_time_dict[k] = cls.format_time_dict(v, fmt)
            elif isinstance(v, list):
                copy_time_dict[k] = cls.format_time_list(v, fmt)
            else:
                copy_time_dict[k] = v

        return copy_time_dict

    @classmethod
    def format_time_list(cls, time_list: List[Any], fmt: str = '%Y-%m-%d %H:%M:%S') -> List[Any]:
        """
        格式化时间列表

        Args:
            time_list: 时间列表
            fmt: 格式化格式，默认为'%Y-%m-%d %H:%M:%S'

        Returns:
            List[Any]: 格式化后的时间列表
        """
        format_time_list = []
        for item in time_list:
            if isinstance(item, (str, datetime)):
                format_item = cls.format_time(item, fmt)
            elif isinstance(item, dict):
                format_item = cls.format_time_dict(item, fmt)
            elif isinstance(item, list):
                format_item = cls.format_time_list(item, fmt)
            else:
                format_item = item

            format_time_list.append(format_item)

        return format_time_list