import asyncio
from typing import List

class Command:
    # 命令名称：相当于 python fast <name>
    name = "test"
    
    # 命令描述信息
    description = "这是一个基础测试命令示例"

    async def execute(self, *args: str) -> None:
        """
        命令具体的执行逻辑
        """
        print("====== 正在执行 test 脚本 ======")
        print(f"您传递过来的外部参数是: {args}")
        
        # 演示异步任务
        await asyncio.sleep(1)
        
        print("✅ 测试命令行任务执行成功！")
