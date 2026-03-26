FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量，防止 python 写入字节码并让标准输出直接到终端
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Shanghai

# 复制依赖文件
COPY requirements.txt /app/

# 安装依赖（使用清华源加速可选项，如果你在国内推荐开启）
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 复制所有项目代码到工作区
COPY . /app/

# 暴露 FastAPI 运行端口
EXPOSE 8000

# 启动服务
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
