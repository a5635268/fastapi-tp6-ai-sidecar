"""
命名风格转换工具类
提供驼峰命名和下划线命名之间的转换方法
"""
import re
from typing import Any, List, Dict, Union


class CamelCaseUtil:
    """
    下划线形式(snake_case)转小驼峰形式(camelCase)工具类
    """

    @classmethod
    def snake_to_camel(cls, snake_str: str) -> str:
        """
        下划线形式字符串转换为小驼峰形式字符串

        Args:
            snake_str: 下划线形式字符串

        Returns:
            str: 小驼峰形式字符串
        """
        if not snake_str:
            return snake_str
        words = snake_str.split('_')
        return words[0] + ''.join(word.capitalize() for word in words[1:] if word)

    @classmethod
    def transform_result(cls, result: Any) -> Any:
        """
        将字典中的下划线键名批量转换为小驼峰形式

        Args:
            result: 输入数据（dict、list 或其他）

        Returns:
            Any: 转换后的结果
        """
        if isinstance(result, dict):
            return {cls.snake_to_camel(k): cls.transform_result(v) for k, v in result.items()}
        elif isinstance(result, list):
            return [cls.transform_result(item) for item in result]
        else:
            return result


class SnakeCaseUtil:
    """
    小驼峰形式(camelCase)转下划线形式(snake_case)工具类
    """

    @classmethod
    def camel_to_snake(cls, camel_str: str) -> str:
        """
        小驼峰形式字符串转换为下划线形式字符串

        Args:
            camel_str: 小驼峰形式字符串

        Returns:
            str: 下划线形式字符串
        """
        if not camel_str:
            return camel_str
        words = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', camel_str)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', words).lower()

    @classmethod
    def transform_result(cls, result: Any) -> Any:
        """
        将字典中的小驼峰键名批量转换为下划线形式

        Args:
            result: 输入数据（dict、list 或其他）

        Returns:
            Any: 转换后的结果
        """
        if isinstance(result, dict):
            return {cls.camel_to_snake(k): cls.transform_result(v) for k, v in result.items()}
        elif isinstance(result, list):
            return [cls.transform_result(item) for item in result]
        else:
            return result