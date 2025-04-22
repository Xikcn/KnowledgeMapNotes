import asyncio
from openai import OpenAI
from pydantic import BaseModel
from fastapi import FastAPI, File, UploadFile, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import time
import shutil
import logging
from typing import Dict, List, Optional, AsyncGenerator, Any
from urllib.parse import quote

from OmniStore.storeManager import storeManager
from OmniText.PDFProcessor import PDFProcessor
from concurrent.futures import ThreadPoolExecutor
import threading
import json
import uuid
from collections import deque

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("文件处理服务")


class rag_item(BaseModel):
    request: str
    model: str
    flow: bool = False
    kg_id: Optional[str] = None
    top_k: int = 1
    filename: Optional[str] = None
    messages: Optional[List[Dict[str, str]]] = None  # 确保消息格式正确
    session_id: Optional[str] = None  # 会话ID，用于跟踪特定文件的对话


app = FastAPI(title="文件处理服务", description="支持文件上传和异步处理")

UPLOAD_FOLDER = 'uploads'
TXT_FOLDER = 'txt_files'
RESULT_FOLDER = 'results'
PROCESS_STATUS: Dict[str, str] = {}

# 确保目录存在
for folder in [UPLOAD_FOLDER, TXT_FOLDER, RESULT_FOLDER]:
    os.makedirs(folder, exist_ok=True)

# 初始化知识图谱组件
from OmniStore.chromadb_store import StoreTool
from LLM.Deepseek_agent import DeepSeekAgent
from sentence_transformers import SentenceTransformer
from KnowledgeGraphManager.KGManager import KgManager
from TextSlicer.SimpleTextSplitter import SemanticTextSplitter

# 初始化模型和组件
embeddings = SentenceTransformer(
    r'D:\Models_Home\Huggingface\models--BAAI--bge-base-zh\snapshots\0e5f83d4895db7955e4cb9ed37ab73f7ded339b6'
).to("cuda:0")

api_key = "sk-xx"

# 创建两个独立的存储工具
chromadb_store = StoreTool(storage_path="./chroma_data", embedding_function=embeddings)

client = OpenAI(
    api_key=api_key,
    base_url="https://api.deepseek.com"
)

# 创建两个独立的agent
rag_agent = DeepSeekAgent(client)
kg_agent = DeepSeekAgent(client)

# 创建两个独立的splitter
kg_splitter = SemanticTextSplitter(2045, 1024)

# 创建两个独立的kg_manager
kg_manager = KgManager(agent=kg_agent, splitter=kg_splitter, embedding_model=embeddings, store=chromadb_store)

FILE_PROCESSORS = {
    '.pdf': PDFProcessor,
    # 可扩展，不想写了。。。
}
# 添加CORS支持
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加线程池
executor = ThreadPoolExecutor(max_workers=8)  # 增加线程池大小以处理更多并发请求
# 添加文件处理锁
file_locks = {}
# 添加RAG问答锁
rag_locks = {}

# 消息队列系统
# 存储结构: {session_id: deque([消息1, 消息2, ...]), ...}
message_queues = {}
# 每个会话的事件: {session_id: Event(), ...}
session_events = {}
# 每个会话的响应状态: {session_id: {"status": "processing/completed/error", "response": [..]}, ...}
session_responses = {}


@app.post("/create_session")
async def create_session():
    """创建新的会话ID"""
    session_id = str(uuid.uuid4())
    message_queues[session_id] = deque()
    session_events[session_id] = asyncio.Event()
    session_responses[session_id] = {"status": "idle", "response": None}
    return {"session_id": session_id}


@app.post("/hybridrag")
async def hybridrag(item: rag_item):
    """处理混合RAG请求"""
    try:
        # 如果没有提供session_id则创建新的
        if not item.session_id:
            item.session_id = str(uuid.uuid4())
            message_queues[item.session_id] = deque()
            session_events[item.session_id] = asyncio.Event()
            session_responses[item.session_id] = {"status": "idle", "response": None}

        # 确保会话存在
        if item.session_id not in message_queues:
            message_queues[item.session_id] = deque()
            session_events[item.session_id] = asyncio.Event()
            session_responses[item.session_id] = {"status": "idle", "response": None}

        # 将请求放入队列
        message_queues[item.session_id].append(item)

        # 如果当前没有进行中的处理，启动处理任务
        if session_responses[item.session_id]["status"] == "idle":
            # 启动后台任务处理这个会话的消息
            asyncio.create_task(process_session_queue(item.session_id))

        # 设置状态为处理中
        session_responses[item.session_id]["status"] = "processing"

        # 等待处理完成
        await session_events[item.session_id].wait()
        session_events[item.session_id].clear()

        # 检查处理结果
        response_data = session_responses[item.session_id]["response"]

        # 如果状态为错误，返回错误信息
        if session_responses[item.session_id]["status"] == "error":
            return JSONResponse(
                status_code=500,
                content={"error": response_data or "处理失败"}
            )

        # 返回结果
        return JSONResponse({"result": response_data})

    except Exception as e:
        logger.error(f"处理出错: {str(e)}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/hybridrag/stream")
async def hybridrag_stream(item: rag_item):
    """处理混合RAG请求并以流式方式返回结果"""
    # 生成唯一的请求ID
    request_id = str(uuid.uuid4())

    # 如果没有提供session_id则创建新的
    if not item.session_id:
        item.session_id = str(uuid.uuid4())
        message_queues[item.session_id] = deque()
        session_events[item.session_id] = asyncio.Event()
        session_responses[item.session_id] = {"status": "idle", "response": None}

    async def stream_generator() -> AsyncGenerator[str, None]:
        try:
            loop = asyncio.get_event_loop()
            if item.filename:
                base_name = os.path.splitext(item.filename)[0]

                # 不再检查文件状态，直接尝试获取RAG锁
                if base_name not in rag_locks:
                    rag_locks[base_name] = asyncio.Lock()

                # 获取锁但不阻塞，如果锁被占用则生成一个等待消息
                if not rag_locks[base_name].locked():
                    async with rag_locks[base_name]:
                        logger.info(f"开始处理知识图谱查询: {item.filename}")

                        # 流式输出准备
                        yield "data: " + json.dumps(
                            {"type": "status", "content": "开始处理", "request_id": request_id}) + "\n\n"

                        # 为每次查询创建新的storeManager实例
                        store_manager = storeManager(store=chromadb_store, agent=kg_agent)

                        # 执行RAG流程 - 实体识别
                        rag_entity = await loop.run_in_executor(executor, store_manager.text2entity, item.request,
                                                                base_name)
                        if not rag_entity:  # 如果返回空列表
                            logger.warning(f"未能识别实体: {item.filename}")
                            rag_entity = []  # 确保是空列表而不是None
                        yield "data: " + json.dumps(
                            {"type": "status", "content": "实体识别完成", "request_id": request_id}) + "\n\n"

                        # 执行RAG流程 - 社区检测
                        community_info = await loop.run_in_executor(executor, store_manager.community_louvain_G,
                                                                    base_name, rag_entity)
                        if not community_info:  # 如果返回空列表
                            logger.warning(f"未能进行社区检测: {item.filename}")
                            community_info = []  # 确保是空列表而不是None
                        yield "data: " + json.dumps(
                            {"type": "status", "content": "社区检测完成", "request_id": request_id}) + "\n\n"

                        # 执行RAG流程 - 向量选择
                        results = await loop.run_in_executor(executor, store_manager.select_vectors, item.request,
                                                             base_name,
                                                             item.top_k)
                        if not results:  # 如果返回空列表
                            logger.warning(f"未能选择向量: {item.filename}")
                            results = []  # 确保是空列表而不是None
                        yield "data: " + json.dumps(
                            {"type": "status", "content": "向量选择完成", "request_id": request_id}) + "\n\n"

                        # 准备流式输出
                        logger.info(f"使用流式输出模式: {item.request}")

                        # 创建响应流 - 使用hybrid_rag_stream函数
                        try:
                            response_stream = await loop.run_in_executor(
                                executor,
                                rag_agent.hybrid_rag_stream,
                                item.request,
                                community_info,
                                results,
                                item.messages
                            )

                            # 确保response_stream不为None
                            if response_stream is None:
                                raise ValueError("响应流生成失败")

                            # 处理流式响应
                            full_text = ""
                            for chunk in response_stream:
                                # 检查chunk是否为None
                                if chunk is None:
                                    continue

                                content = rag_agent.process_hybrid_rag_stream_chunk(chunk)
                                if content:
                                    full_text += content
                                    yield "data: " + json.dumps({
                                        "type": "content",
                                        "chunk": content,
                                        "full": full_text,
                                        "request_id": request_id
                                    }) + "\n\n"

                            # 处理最终结果
                            answer, material = rag_agent.extract_material_from_text(full_text)

                            # 发送最终结果
                            yield "data: " + json.dumps({
                                "type": "final",
                                "answer": answer,
                                "material": material,
                                "request_id": request_id
                            }) + "\n\n"
                        except Exception as e:
                            logger.error(f"处理响应流时出错: {str(e)}")
                            yield "data: " + json.dumps({
                                "type": "error",
                                "content": f"处理响应失败: {str(e)}",
                                "request_id": request_id
                            }) + "\n\n"
                else:
                    # 如果锁被占用，将请求入队
                    if item.session_id not in message_queues:
                        message_queues[item.session_id] = deque()

                    message_queues[item.session_id].append(item)

                    # 通知前端请求已入队
                    yield "data: " + json.dumps({
                        "type": "status",
                        "content": "请求已入队，等待处理",
                        "request_id": request_id
                    }) + "\n\n"

                    # 等待其他请求处理完成
                    yield "data: " + json.dumps({
                        "type": "queued",
                        "session_id": item.session_id,
                        "request_id": request_id
                    }) + "\n\n"

        except Exception as e:
            logger.error(f"流式处理出错: {str(e)}", exc_info=True)  # 添加详细错误堆栈
            yield "data: " + json.dumps({
                "type": "error",
                "content": str(e),
                "request_id": request_id
            }) + "\n\n"
        finally:
            yield "data: " + json.dumps({
                "type": "done",
                "request_id": request_id
            }) + "\n\n"

    return StreamingResponse(stream_generator(), media_type="text/event-stream")


# 处理会话队列的后台任务
async def process_session_queue(session_id: str):
    """处理特定会话的消息队列"""
    loop = asyncio.get_event_loop()

    try:
        # 只要队列不为空，就继续处理
        while message_queues[session_id]:
            # 获取下一个待处理的请求
            item = message_queues[session_id].popleft()

            if item.filename:
                base_name = os.path.splitext(item.filename)[0]

                # 确保锁存在
                if base_name not in rag_locks:
                    rag_locks[base_name] = asyncio.Lock()

                async with rag_locks[base_name]:
                    logger.info(f"开始处理队列中的知识图谱查询: {item.filename}")

                    # 为每次查询创建新的storeManager实例
                    store_manager = storeManager(store=chromadb_store, agent=kg_agent)

                    # 执行RAG流程
                    flow = item.flow
                    rag_entity = await loop.run_in_executor(executor, store_manager.text2entity, item.request,
                                                            base_name)
                    community_info = await loop.run_in_executor(executor, store_manager.community_louvain_G,
                                                                base_name, rag_entity)
                    results = await loop.run_in_executor(executor, store_manager.select_vectors, item.request,
                                                         base_name, item.top_k)

                    try:
                        # 使用hybrid_rag函数
                        result = await loop.run_in_executor(
                            executor,
                            rag_agent.hybrid_rag,
                            item.request,
                            community_info,
                            results,
                            item.messages,
                            flow
                        )

                        # 确保结果有效
                        if not result or result == -1:
                            session_responses[session_id]["status"] = "error"
                            session_responses[session_id]["response"] = "生成回答失败"
                        else:
                            session_responses[session_id]["status"] = "completed"
                            session_responses[session_id]["response"] = {
                                "answer": result.get('answer', ''),
                                "material": result.get('material', '')
                            }
                    except Exception as e:
                        logger.error(f"处理队列中的响应时出错: {str(e)}", exc_info=True)
                        session_responses[session_id]["status"] = "error"
                        session_responses[session_id]["response"] = f"处理失败: {str(e)}"

            # 通知等待的请求处理已完成
            session_events[session_id].set()

        # 队列处理完毕，将状态设为空闲
        session_responses[session_id]["status"] = "idle"

    except Exception as e:
        logger.error(f"处理会话队列出错: {str(e)}", exc_info=True)
        session_responses[session_id]["status"] = "error"
        session_responses[session_id]["response"] = str(e)
        session_events[session_id].set()


@app.get("/session_status/{session_id}")
async def get_session_status(session_id: str):
    """获取会话状态"""
    if session_id not in session_responses:
        return JSONResponse(
            status_code=404,
            content={"error": "会话不存在"}
        )

    # 返回会话状态和消息队列长度
    queue_length = len(message_queues.get(session_id, deque()))
    return {
        "status": session_responses[session_id]["status"],
        "queue_length": queue_length
    }


@app.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """清除会话数据"""
    if session_id in message_queues:
        del message_queues[session_id]

    if session_id in session_events:
        del session_events[session_id]

    if session_id in session_responses:
        del session_responses[session_id]

    return {"message": f"会话 {session_id} 已清除"}


def process_knowledge_graph(base_name: str, text_content: str, original_filename: str):
    """处理文本内容生成知识图谱"""
    try:
        # 获取文件处理锁
        if base_name not in file_locks:
            file_locks[base_name] = threading.Lock()

        with file_locks[base_name]:
            logger.info(f"开始处理文件 {base_name} 的知识图谱...")
            start_time = time.time()

            # 更新状态为知识图谱构建中
            PROCESS_STATUS[base_name] = "building_kg"

            # 知识图谱构建过程
            r = kg_manager.知识图谱的构建(text_content)
            logger.info(f"知识图谱构建完成，耗时: {time.time() - start_time:.2f}秒")

            # 更新状态为有向图转换中
            PROCESS_STATUS[base_name] = "converting_kg"

            # 转换为有向图
            kg_manager.三元组转有向图nx(r)

            # 更新状态为知识图谱绘制中
            PROCESS_STATUS[base_name] = "drawing_kg"

            # 绘制知识图谱
            start_time = time.time()
            kg_manager.绘制知识图谱(base_name)
            kg_manager.original_file_type = original_filename  # 使用原始文件名

            # 更新状态为保存知识图谱中
            PROCESS_STATUS[base_name] = "saving_kg"

            kg_manager.save_store()
            logger.info(f"知识图谱绘制完成，耗时: {time.time() - start_time:.2f}秒")

            # 保存并移动结果文件
            result_file = f"{base_name}.html"
            if os.path.exists(result_file):
                shutil.move(result_file, os.path.join(RESULT_FOLDER, result_file))
            else:
                raise FileNotFoundError("未生成结果HTML文件")

            # 更新处理状态为已完成
            PROCESS_STATUS[base_name] = "completed"
            logger.info(f"知识图谱处理完成: {base_name}")

    except Exception as e:
        error_msg = str(e)
        PROCESS_STATUS[base_name] = f"error"
        logger.error(f"处理文件 {base_name} 出错: {error_msg}", exc_info=True)
        raise


def process_uploaded_file(original_path: str, filename: str):
    """后台处理任务（包含文件转换）"""
    try:
        # 获取文件信息
        base_name = os.path.splitext(filename)[0]
        file_ext = os.path.splitext(filename)[1].lower()
        txt_filename = f"{os.path.splitext(filename)[0]}.txt"
        txt_path = os.path.join(TXT_FOLDER, txt_filename)

        # 在开始处理前将状态设置为processing
        PROCESS_STATUS[base_name] = "processing"
        logger.info(f"开始处理文件: {filename}, 状态已设置为processing")

        # 设置原始文件名
        kg_manager.original_file_type = filename  # 使用完整文件名

        # 文件转换处理
        if file_ext in FILE_PROCESSORS:
            # 使用专用处理器转换
            processor = FILE_PROCESSORS[file_ext](output_dir=TXT_FOLDER)
            processor.process([original_path])
            processor.save_as_txt(combine=False)
        elif file_ext == '.txt':
            # 直接复制文本文件
            shutil.copy(original_path, txt_path)
        else:
            raise ValueError(f"不支持的文件类型: {file_ext}")

        # 读取转换后的文本内容
        with open(txt_path, "r", encoding="utf-8") as f:
            text_content = f.read()

        # 更新状态表明开始处理知识图谱
        PROCESS_STATUS[base_name] = "processing_kg"
        logger.info(f"文件 {filename} 转换完成，开始处理知识图谱")

        # 处理知识图谱
        process_knowledge_graph(base_name, text_content, filename)

        # 处理完成后更新状态
        PROCESS_STATUS[base_name] = "completed"
        logger.info(f"文件 {filename} 处理完成，状态已设置为completed")

    except Exception as e:
        error_msg = f"文件处理失败: {str(e)}"
        if 'base_name' in locals():  # 确保base_name已定义
            PROCESS_STATUS[base_name] = "error"
        logger.error(error_msg, exc_info=True)


@app.post("/upload")
async def upload_file(
        file: UploadFile = File(...),
        background_tasks: BackgroundTasks = None
):
    """支持多种格式的文件上传接口"""
    try:
        # 保存原始文件
        filename = file.filename
        base_name = os.path.splitext(filename)[0]
        original_path = os.path.join(UPLOAD_FOLDER, filename)

        with open(original_path, "wb") as f:
            contents = await file.read()
            f.write(contents)

        logger.info(f"文件 {filename} 上传成功，存储为 {original_path}")

        # 初始化处理状态
        PROCESS_STATUS[base_name] = "uploading"

        # 添加后台处理任务
        background_tasks.add_task(process_uploaded_file, original_path, filename)

        return JSONResponse({
            "status": "uploading",
            "message": "文件已上传，正在转换处理中",
            "filename": filename
        })

    except Exception as e:
        error_msg = f"文件上传失败: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": error_msg}
        )


@app.get("/processing-status/{filename}")
async def get_processing_status(filename: str):
    """获取文件处理状态"""
    base_name = os.path.splitext(filename)[0]
    status = PROCESS_STATUS.get(base_name)

    # 状态映射，用于前端展示
    status_map = {
        "uploading": "上传中",
        "processing": "文件处理中",
        "processing_kg": "知识图谱准备中",
        "building_kg": "知识图谱构建中",
        "converting_kg": "知识图谱转换中",
        "drawing_kg": "知识图谱绘制中",
        "saving_kg": "知识图谱保存中",
        "completed": "处理完成",
        "error": "处理出错"
    }

    if status:
        result_exists = os.path.exists(os.path.join(RESULT_FOLDER, f'{base_name}.html'))
        display_status = status_map.get(status, status)

        return JSONResponse({
            "status": status,
            "display_status": display_status,
            "result_exists": result_exists,
            "filename": filename
        })
    else:
        return JSONResponse(
            status_code=404,
            content={"error": "文件不存在或未开始处理"}
        )


@app.get("/file-content/{filename}")
async def get_file_content(filename: str):
    """获取转换后的文本内容"""
    txt_filename = f"{os.path.splitext(filename)[0]}.txt"
    txt_path = os.path.join(TXT_FOLDER, txt_filename)

    if os.path.exists(txt_path):
        try:
            with open(txt_path, "r", encoding="utf-8") as f:
                content = f.read()
            return JSONResponse({"content": content})
        except Exception as e:
            error_msg = str(e)
            logger.error(f"读取文件内容失败: {error_msg}")
            return JSONResponse(
                status_code=500,
                content={"error": f"读取文件内容失败: {error_msg}"}
            )
    else:
        return JSONResponse(
            status_code=404,
            content={"error": "文件不存在或尚未完成转换"}
        )


@app.get("/result/{filename}")
async def get_result(filename: str):
    """获取处理结果的HTML文件"""

    base_name = os.path.splitext(filename)[0]
    print(base_name)
    result_file = f"{base_name}.html"
    result_path = os.path.join(RESULT_FOLDER, result_file)

    if os.path.exists(result_path):
        safe_filename = quote(result_file, safe='')
        return FileResponse(
            result_path,
            media_type="text/html",
            headers={
                "Access-Control-Allow-Origin": "*",
                "Content-Disposition": f"inline; filename*=utf-8''{safe_filename}"
            }
        )
    else:
        status = PROCESS_STATUS.get(base_name, "unknown")
        return JSONResponse(
            status_code=404,
            content={
                "error": "结果文件不存在",
                "status": status,
                "filename": filename
            }
        )


@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {"status": "healthy", "timestamp": time.time()}


@app.get("/list-files")
async def list_files():
    """获取所有已处理文件列表"""
    try:
        # 创建一个专用的storeManager实例来获取文件列表
        file_manager = storeManager(store=chromadb_store, agent=kg_agent)

        # 获取数据库中的文件列表
        db_files = file_manager.list_files()
        db_file_ids = db_files.get('ids', [])
        db_metadatas = db_files.get('metadatas', [])

        # 获取当前正在处理的文件（从PROCESS_STATUS获取）
        processing_statuses = ["uploading", "processing", "processing_kg",
                               "building_kg", "converting_kg", "drawing_kg", "saving_kg"]
        processing_files = {base_name: status for base_name, status in PROCESS_STATUS.items()
                            if status in processing_statuses}

        # 状态映射，用于前端展示
        status_map = {
            "uploading": "上传中",
            "processing": "文件处理中",
            "processing_kg": "知识图谱准备中",
            "building_kg": "知识图谱构建中",
            "converting_kg": "知识图谱转换中",
            "drawing_kg": "知识图谱绘制中",
            "saving_kg": "知识图谱保存中",
            "completed": "处理完成",
            "error": "处理出错"
        }

        # 合并结果：先处理数据库中的文件
        processed_files = []
        for i, file_id in enumerate(db_file_ids):
            if i >= len(db_metadatas):
                continue  # 防止索引错误

            base_name = os.path.splitext(file_id)[0]
            original_filename = db_metadatas[i].get('original_file_type', file_id)

            # 获取状态：优先从PROCESS_STATUS获取
            status = PROCESS_STATUS.get(base_name, "completed")
            display_status = status_map.get(status, status)

            processed_files.append({
                "filename": original_filename,
                "status": status,
                "display_status": display_status
            })

        # 再添加仅在PROCESS_STATUS中的文件（正在处理但尚未添加到数据库的文件）
        db_base_names = [os.path.splitext(file_id)[0] for file_id in db_file_ids]
        for base_name, status in processing_files.items():
            if base_name not in db_base_names:
                display_status = status_map.get(status, status)
                processed_files.append({
                    "filename": f"{base_name}.txt",  # 默认使用txt扩展名
                    "status": status,
                    "display_status": display_status
                })

        return JSONResponse({"files": processed_files})
    except Exception as e:
        logger.error(f"获取文件列表失败: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": f"获取文件列表失败: {str(e)}"}
        )


@app.delete("/delete/{filename}")
async def delete_file(filename: str):
    """删除指定文件及其相关数据"""
    try:
        base_name = os.path.splitext(filename)[0]
        kg_manager.delete_store([base_name])
        return JSONResponse({"message": f"文件 {filename} 已成功删除"})
    except Exception as e:
        logger.error(f"删除文件失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"删除文件失败: {str(e)}"}
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)