[根目录](../../CLAUDE.md) > [app](../) > **utils**

# Utils 模块 CLAUDE.md

> 最后更新：2026-05-06

## 模块职责

工具函数模块，提供通用的辅助工具类：
- 分页工具（适配 Tortoise ORM）
- 字符串处理工具（空白判断、大小写转换等）
- 时间格式化工具（时间解析与格式化）
- 命名风格转换工具（驼峰与下划线互转）
- Excel 导入导出工具（数据导出、导入、模板生成）

## 入口与启动

| 文件 | 工具类 | 职责 |
|------|--------|------|
| `page_util.py` | `PageUtil` | 分页查询与切片分页 |
| `string_util.py` | `StringUtil` | 字符串判断与转换 |
| `time_format_util.py` | `TimeFormatUtil` | 时间格式化与解析 |
| `case_util.py` | `CamelCaseUtil`, `SnakeCaseUtil` | 命名风格转换 |
| `excel_util.py` | `ExcelUtil` | Excel 导入导出 |

## 对外接口

### PageUtil 分页工具

```python
from app.utils.page_util import PageUtil

# Tortoise ORM 分页查询
page_result = await PageUtil.paginate(
    queryset=User.all(),
    page=1,
    page_size=20,
)
# 返回：{"data": [...], "total": 100, "page": 1, "page_size": 20, "pages": 5}

# 列表切片分页
page_result = PageUtil.get_page_obj(
    data_list=all_items,
    page=1,
    page_size=20,
)

# 转换为分页响应模型
response = PageUtil.to_paginated_response(page_result, msg="获取成功")
```

### StringUtil 字符串工具

```python
from app.utils.string_util import StringUtil

# 空白判断
StringUtil.is_blank("  ")       # True（全空格）
StringUtil.is_empty("")         # True（空字符串）
StringUtil.is_not_empty("abc")  # True

# HTTP 判断
StringUtil.is_http("https://example.com")  # True

# 大小写忽略判断
StringUtil.contains_ignore_case("Hello World", "world")  # True
StringUtil.equals_ignore_case("ABC", "abc")              # True

# 下划线转驼峰
StringUtil.convert_to_camel_case("user_name")  # "UserName"

# 字典值查找（忽略大小写）
StringUtil.get_mapping_value_by_key_ignore_case({"Name": "Alice"}, "name")  # "Alice"
```

### TimeFormatUtil 时间工具

```python
from app.utils.time_format_util import TimeFormatUtil

# 时间格式化
TimeFormatUtil.format_time("2026-05-06T10:30:00", "%Y-%m-%d %H:%M:%S")
# 返回："2026-05-06 10:30:00"

# 日期解析
TimeFormatUtil.parse_date("2026-05-06T10:30:00")  # 返回 date 对象

# 字典时间格式化
time_dict = {"created_at": "2026-05-06T10:30:00", "updated_at": "2026-05-06T12:00:00"}
formatted = TimeFormatUtil.format_time_dict(time_dict, "%Y-%m-%d")
# 返回：{"created_at": "2026-05-06", "updated_at": "2026-05-06"}

# 列表时间格式化
time_list = ["2026-05-06T10:30:00", "2026-05-06T12:00:00"]
formatted = TimeFormatUtil.format_time_list(time_list, "%Y-%m-%d")
# 返回：["2026-05-06", "2026-05-06"]
```

### CamelCaseUtil/SnakeCaseUtil 命名转换

```python
from app.utils.case_util import CamelCaseUtil, SnakeCaseUtil

# 下划线转小驼峰
CamelCaseUtil.snake_to_camel("user_name")  # "userName"
CamelCaseUtil.snake_to_camel("created_at")  # "createdAt"

# 批量转换字典键名
data = {"user_name": "Alice", "created_at": "2026-05-06"}
camel_data = CamelCaseUtil.transform_result(data)
# 返回：{"userName": "Alice", "createdAt": "2026-05-06"}

# 小驼峰转下划线
SnakeCaseUtil.camel_to_snake("userName")  # "user_name"
SnakeCaseUtil.camel_to_snake("createdAt")  # "created_at"

# 批量转换字典键名
data = {"userName": "Alice", "createdAt": "2026-05-06"}
snake_data = SnakeCaseUtil.transform_result(data)
# 返回：{"user_name": "Alice", "created_at": "2026-05-06"}
```

### ExcelUtil 导入导出

```python
from app.utils.excel_util import ExcelUtil

# 数据导出
data = [{'id': 1, 'name': 'Alice'}, {'id': 2, 'name': 'Bob'}]
columns = {'id': 'ID', 'name': '姓名'}
return ExcelUtil.export_excel(data, columns, 'users.xlsx', '用户列表')

# 数据导入
with open('import.xlsx', 'rb') as f:
    data = ExcelUtil.import_excel(
        f.read(),
        columns={'姓名': 'name', '年龄': 'age'},
        skip_header=True,
    )

# 生成模板
columns = {'name': '姓名', 'age': '年龄'}
example_data = [{'name': '示例', 'age': 25}]
return ExcelUtil.get_excel_template(columns, 'user_template.xlsx', example_data=example_data)
```

## 关键依赖与配置

### 依赖

| 依赖 | 用途 |
|------|------|
| `tortoise-orm` | PageUtil 分页查询 |
| `openpyxl` | Excel 处理 |
| `python-dateutil` | 时间解析（可选） |

### dateutil 可选依赖

```python
# time_format_util.py 自动检测 dateutil
try:
    from dateutil.parser import parse
    HAS_DATEUTIL = True
except ImportError:
    HAS_DATEUTIL = False
```

## 数据模型

本模块为工具类，无数据模型。

## 测试与质量

建议添加测试：

```python
# tests/test_utils/test_page_util.py
async def test_paginate():
    result = await PageUtil.paginate(User.all(), page=1, page_size=10)
    assert result["page"] == 1
    assert result["page_size"] == 10

# tests/test_utils/test_string_util.py
def test_is_blank():
    assert StringUtil.is_blank("  ") is True
    assert StringUtil.is_blank("abc") is False

# tests/test_utils/test_excel_util.py
def test_export_excel():
    data = [{'id': 1, 'name': 'Alice'}]
    response = ExcelUtil.export_excel(data, {'id': 'ID', 'name': '姓名'})
    assert response.media_type == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
```

## 常见问题 (FAQ)

**Q: PageUtil.paginate 与 ResponseBuilder.paginated 有什么区别？**

- `PageUtil.paginate` 返回字典格式，适合内部使用
- `ResponseBuilder.paginated` 返回 Pydantic 模型，适合 API 响应
- 可使用 `PageUtil.to_paginated_response()` 转换

**Q: 为什么 time_format_util 需要 dateutil？**

dateutil 提供更强大的时间解析能力，支持多种格式。未安装时会使用 `datetime.fromisoformat` 作为降级方案。

**Q: ExcelUtil 如何处理大数据量导出？**

大数据量建议分批导出或使用异步后台任务：

```python
from fastapi import BackgroundTasks

@router.get("/export")
async def export_large_data(background_tasks: BackgroundTasks):
    # 后台生成文件并存储
    background_tasks.add_task(generate_large_excel)
    return {"message": "导出任务已提交"}
```

**Q: 命名转换工具如何处理嵌套结构？**

`transform_result` 方法支持嵌套字典和列表的递归转换：

```python
data = {
    "user_name": "Alice",
    "profile": {
        "created_at": "2026-05-06",
        "tags": [{"tag_name": "admin"}]
    }
}
result = CamelCaseUtil.transform_result(data)
# {
#     "userName": "Alice",
#     "profile": {
#         "createdAt": "2026-05-06",
#         "tags": [{"tagName": "admin"}]
#     }
# }
```

## 相关文件清单

| 文件 | 行数 | 说明 |
|------|------|------|
| `page_util.py` | ~153 行 | 分页工具类 |
| `string_util.py` | ~209 行 | 字符串工具类 |
| `time_format_util.py` | ~120 行 | 时间格式化工具 |
| `case_util.py` | ~86 行 | 命名风格转换工具 |
| `excel_util.py` | ~327 行 | Excel 导入导出工具 |

## 变更记录 (Changelog)

### 2026-05-06

- 创建模块级 CLAUDE.md
- 整理工具函数接口文档