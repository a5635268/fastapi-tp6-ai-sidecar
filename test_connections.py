"""
数据库连接测试脚本
测试 MySQL 和 Redis 连接状态
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

from tortoise import Tortoise
from redis import asyncio as aioredis
from app.core.config import settings


async def test_mysql():
    """测试 MySQL 连接"""
    print("\n" + "="*50)
    print("测试 MySQL 连接")
    print("="*50)
    print(f"数据库 URL: {settings.DATABASE_URL}")

    try:
        # 初始化 Tortoise ORM（无业务模型）
        await Tortoise.init(
            db_url=settings.DATABASE_URL,
            modules={"models": []},
        )

        # 执行简单查询测试连接
        conn = Tortoise.get_connection("default")
        result = await conn.execute_query("SELECT 1 as test")

        print("✅ MySQL 连接成功!")
        print(f"   测试查询结果: {result[1][0]['test']}")

        # 关闭连接
        await Tortoise.close_connections()
        return True

    except Exception as e:
        print(f"❌ MySQL 连接失败!")
        print(f"   错误信息: {str(e)}")
        return False


async def test_redis():
    """测试 Redis 连接"""
    print("\n" + "="*50)
    print("测试 Redis 连接")
    print("="*50)
    print(f"Redis 地址: {settings.REDIS_HOST}:{settings.REDIS_PORT}")
    print(f"Redis 数据库: {settings.REDIS_DATABASE}")

    try:
        # 构建 Redis URL
        redis_url = f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DATABASE}"
        if settings.REDIS_PASSWORD:
            redis_url = f"redis://:{settings.REDIS_PASSWORD}@{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DATABASE}"

        # 创建 Redis 客户端
        redis_client = await aioredis.from_url(
            redis_url,
            encoding="utf-8",
            decode_responses=True
        )

        # 执行 PING 命令测试连接
        ping_result = await redis_client.ping()

        # 测试基本操作
        test_key = "test_connection"
        test_value = "hello_fastapi"

        await redis_client.set(test_key, test_value, ex=10)
        get_result = await redis_client.get(test_key)

        print("✅ Redis 连接成功!")
        print(f"   PING 结果: {ping_result}")
        print(f"   SET/GET 测试: {get_result}")

        # 关闭连接
        await redis_client.close()
        return True

    except Exception as e:
        print(f"❌ Redis 连接失败!")
        print(f"   错误信息: {str(e)}")
        return False


async def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("FastAPI 项目连接测试")
    print("="*60)

    # 测试 MySQL
    mysql_ok = await test_mysql()

    # 测试 Redis
    redis_ok = await test_redis()

    # 总结
    print("\n" + "="*60)
    print("测试结果总结")
    print("="*60)
    print(f"MySQL: {'✅ 成功' if mysql_ok else '❌ 失败'}")
    print(f"Redis: {'✅ 成功' if redis_ok else '❌ 失败'}")

    if mysql_ok and redis_ok:
        print("\n🎉 所有连接测试通过! 项目可以正常启动。")
        return 0
    else:
        print("\n⚠️  部分连接测试失败，请检查配置和服务状态。")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)