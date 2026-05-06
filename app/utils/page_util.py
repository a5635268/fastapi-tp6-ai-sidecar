"""
分页工具类
适配 Tortoise ORM 的分页查询功能
"""
from typing import Any, Dict, List, Tuple
from tortoise.queryset import QuerySet

from app.core.response import PaginatedResponse


def _calculate_pages(total: int, page_size: int) -> int:
    """
    计算总页数（通用逻辑，避免重复）

    Args:
        total: 总记录数
        page_size: 每页数量

    Returns:
        int: 总页数
    """
    if page_size <= 0:
        return 0
    return (total + page_size - 1) // page_size


def _validate_page_params(page: int, page_size: int) -> Tuple[int, int]:
    """
    校验并修正分页参数（通用逻辑）

    Args:
        page: 当前页码
        page_size: 每页数量

    Returns:
        Tuple[int, int]: 修正后的 (page, page_size)
    """
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 10
    return page, page_size


class PageUtil:
    """
    分页工具类（Tortoise ORM 版本）
    """

    @classmethod
    def get_page_obj(
        cls,
        data_list: List[Any],
        page: int = 1,
        page_size: int = 10,
    ) -> Dict[str, Any]:
        """
        对列表进行切片分页

        Args:
            data_list: 数据列表
            page: 当前页码，从 1 开始
            page_size: 每页数量

        Returns:
            Dict[str, Any]: 分页结果字典
        """
        # 参数校验：使用通用逻辑
        page, page_size = _validate_page_params(page, page_size)

        total = len(data_list)
        pages = _calculate_pages(total, page_size)

        # 计算起始和结束索引
        start = (page - 1) * page_size
        end = start + page_size

        # 切片获取当前页数据
        page_data = data_list[start:end] if start < total else []

        return {
            "data": page_data,
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": pages,
        }

    @classmethod
    async def paginate(
        cls,
        queryset: QuerySet,
        page: int = 1,
        page_size: int = 10,
    ) -> Dict[str, Any]:
        """
        对 Tortoise ORM QuerySet 进行分页查询

        Args:
            queryset: Tortoise ORM 查询集
            page: 当前页码，从 1 开始
            page_size: 每页数量

        Returns:
            Dict[str, Any]: 分页结果字典
        """
        # 参数校验：使用通用逻辑
        page, page_size = _validate_page_params(page, page_size)

        # 获取总数
        total = await queryset.count()
        pages = _calculate_pages(total, page_size)

        # 计算偏移量
        offset = (page - 1) * page_size

        # 分页查询
        page_data = await queryset.offset(offset).limit(page_size)

        return {
            "data": page_data,
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": pages,
        }

    @classmethod
    def to_paginated_response(
        cls,
        page_result: Dict[str, Any],
        msg: str = "获取成功",
    ) -> PaginatedResponse:
        """
        将分页结果转换为 PaginatedResponse

        Args:
            page_result: 分页结果字典
            msg: 响应消息

        Returns:
            PaginatedResponse: 分页响应模型
        """
        return PaginatedResponse(
            code=0,
            msg=msg,
            data=page_result.get("data", []),
            total=page_result.get("total", 0),
            page=page_result.get("page", 1),
            page_size=page_result.get("page_size", 10),
            pages=page_result.get("pages", 0),
        )
