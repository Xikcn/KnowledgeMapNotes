FROM python:3.12-slim

ENV HF_ENDPOINT=https://hf-mirror.com

WORKDIR /app

# 复制依赖文件并安装
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install modelscope -i https://pypi.tuna.tsinghua.edu.cn/simple
RUN modelscope download --model BAAI/bge-base-zh --local_dir /app/models/bge-base-zh
RUN modelscope download --model BAAI/bge-reranker-base --local_dir /app/models/bge-reranker-base
RUN pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
# 复制应用代码
COPY . .

# 暴露端口
EXPOSE 8000

# 启动应用
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]