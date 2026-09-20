"""
防重复提交注解 (repeat_submit) 单元测试
"""
import pytest
from fastapi import Request
from starlette.datastructures import Headers

from app.annotations import repeat_submit, RepeatSubmit
from app.core.redis import RedisUtil
from app.core.response import ApiResponse


def make_mock_request(path: str = "/api/test", headers_dict: dict | None = None) -> Request:
    """构建模拟 Request 对象"""
    scope = {
        "type": "http",
        "method": "POST",
        "path": path,
        "headers": Headers(headers_dict or {}).raw,
        "client": ("127.0.0.1", 12345),
    }
    return Request(scope)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_repeat_submit_basic_flow(redis_mock):
    """测试防重复提交正常提交与重复提交拦截逻辑"""
    call_count = 0

    @repeat_submit(interval_seconds=5, message="请勿重复操作")
    async def create_item(request: Request, data: dict):
        nonlocal call_count
        call_count += 1
        return {"success": True, "count": call_count}

    req = make_mock_request("/api/v1/items")
    payload = {"name": "test_item"}

    # 1. 首次调用：成功执行
    res1 = await create_item(req, payload)
    assert res1 == {"success": True, "count": 1}
    assert call_count == 1

    # 2. 5秒间隔内二次调用：触发防重拦截，返回 code=15 错误响应
    res2 = await create_item(req, payload)
    assert isinstance(res2, ApiResponse)
    assert res2.code == 15
    assert res2.msg == "请勿重复操作"
    assert call_count == 1  # 业务函数未再次被执行


@pytest.mark.unit
@pytest.mark.asyncio
async def test_repeat_submit_header_idempotency(redis_mock):
    """测试基于 X-Idempotency-Key 请求头的幂等锁定"""

    @repeat_submit(interval_seconds=10, header_name="X-Idempotency-Key")
    async def submit_order(request: Request):
        return {"order_id": 1001}

    header_key = "uniq-uuid-999"
    req1 = make_mock_request("/api/orders", {"x-idempotency-key": header_key})
    req2 = make_mock_request("/api/orders", {"x-idempotency-key": header_key})

    # 首次带 header 提交成功
    res1 = await submit_order(req1)
    assert res1 == {"order_id": 1001}

    # Redis 中应产生 header 锁定 Key
    lock_val = await redis_mock.get(f"repeat_submit:header:{header_key}")
    assert lock_val == b"1" or lock_val == "1"

    # 重复带相同 header 提交被拦截
    res2 = await submit_order(req2)
    assert isinstance(res2, ApiResponse)
    assert res2.code == 15


@pytest.mark.unit
@pytest.mark.asyncio
async def test_repeat_submit_exception_release_lock(redis_mock):
    """测试业务函数抛出异常时自动释放防重锁"""

    should_fail = True

    @repeat_submit(interval_seconds=10)
    async def flaky_operation(request: Request):
        nonlocal should_fail
        if should_fail:
            raise ValueError("业务异常，模拟事务失败")
        return {"status": "ok"}

    req = make_mock_request("/api/flaky")

    # 1. 第一次调用引发业务异常
    with pytest.raises(ValueError, match="业务异常"):
        await flaky_operation(req)

    # 验证 Redis 中的防重锁已被主动删除
    keys = await redis_mock.keys("repeat_submit:*")
    assert len(keys) == 0

    # 2. 修正状态后再次提交：应当允许提交并成功执行
    should_fail = False
    res = await flaky_operation(req)
    assert res == {"status": "ok"}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_repeat_submit_redis_down_fail_open():
    """测试 Redis 连接不可用时的 Fail-Open 降级放行策略"""
    # 模拟 Redis 未连接
    RedisUtil._redis = None

    call_count = 0

    @RepeatSubmit(interval_seconds=5)
    async def process_task(request: Request):
        nonlocal call_count
        call_count += 1
        return {"executed": True}

    req = make_mock_request("/api/task")

    # 即使连续调用，由于 Redis 不可用，全量降级放行并正常执行
    res1 = await process_task(req)
    res2 = await process_task(req)

    assert res1 == {"executed": True}
    assert res2 == {"executed": True}
    assert call_count == 2


@pytest.mark.unit
def test_repeat_submit_invalid_interval():
    """测试参数校验：interval_seconds 必须大于 0"""
    with pytest.raises(ValueError, match="interval_seconds 必须大于 0"):
        repeat_submit(interval_seconds=0)

    with pytest.raises(ValueError, match="interval_seconds 必须大于 0"):
        repeat_submit(interval_seconds=-5)
