from pydantic import BaseModel
from fastapi import FastAPI, File, UploadFile, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import time
import shutil
import logging
from typing import Dict, List, Optional
from urllib.parse import quote
from OmniText.PDFProcessor import PDFProcessor
from concurrent.futures import ThreadPoolExecutor
import threading

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
)

api_key = "sk-xx"

# 创建两个独立的存储工具
rag_store = StoreTool(embedding_function=embeddings)
kg_store = StoreTool(embedding_function=embeddings)

# 创建两个独立的agent
rag_agent = DeepSeekAgent(api_key=api_key, embedding_model=embeddings)
kg_agent = DeepSeekAgent(api_key=api_key, embedding_model=embeddings)

# 创建两个独立的splitter
rag_splitter = SemanticTextSplitter(2045, 1024)
kg_splitter = SemanticTextSplitter(2045, 1024)

# 创建两个独立的kg_manager
rag_manager = KgManager(agent=rag_agent, splitter=rag_splitter, embedding_model=embeddings, store=rag_store)
kg_manager = KgManager(agent=kg_agent, splitter=kg_splitter, embedding_model=embeddings, store=kg_store)

FILE_PROCESSORS = {
    '.pdf': PDFProcessor,
    # 可扩展添加其他类型处理器，例如：
    # '.docx': DocxProcessor,
    # '.pptx': PptxProcessor
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
executor = ThreadPoolExecutor(max_workers=4)
# 添加文件处理锁
file_locks = {}
# 添加RAG问答锁
rag_locks = {}


@app.post("/hybridrag")
async def hybridrag(item: rag_item):
    """处理混合RAG请求"""
    try:
        # 如果提供了文件名，检查文件处理状态
        if item.filename:
            base_name = os.path.splitext(item.filename)[0]

            # 检查文件处理状态
            status = PROCESS_STATUS.get(base_name)

            # 如果文件正在处理中，返回处理状态
            if status == "processing":
                return JSONResponse({
                    "status": "processing",
                    "message": "文件正在处理中，请稍后再试"
                })

            # 如果文件处理完成或未开始处理，尝试加载知识图谱
            if status == "completed" or status is None:
                try:
                    # 只在加载知识图谱时加锁
                    if base_name not in rag_locks:
                        rag_locks[base_name] = threading.Lock()

                    with rag_locks[base_name]:
                        rag_manager.load_store(base_name)
                        logger.info(f"已加载文件 {item.filename} 的知识图谱")
                except Exception as e:
                    logger.error(f"加载知识图谱失败: {str(e)}")
                    return JSONResponse({
                        "status": "error",
                        "message": "加载知识图谱失败，请稍后重试"
                    })
            else:
                return JSONResponse({
                    "status": "error",
                    "message": "文件处理失败"
                })

            # 提取实体
            rag_entity = rag_manager.text2entity(item.request)
            logger.info(f"提取的实体: {rag_entity}")

            # 社区搜索得到相关实体关联实体
            community_info = rag_manager.community_louvain_G(rag_entity)
            logger.info(f"社区搜索结果: {community_info}")

            # 获取相关向量
            results = rag_manager.select_vectors(item.request, item.top_k)

            # hybridrag处理
            result = rag_agent.hybrid_rag(item.request, community_info, results, item.messages)
            logger.info(f"混合RAG结果: {result}")

            response = {
                "answer": result['answer'],
                "material": result['material']
            }
            return JSONResponse({"result": response})

    except Exception as e:
        logger.error(f"处理RAG请求出错: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": f"处理RAG请求出错: {str(e)}"}
        )


def process_knowledge_graph(base_name: str, text_content: str, original_filename: str):
    """处理文本内容生成知识图谱"""
    try:
        # 获取文件处理锁
        if base_name not in file_locks:
            file_locks[base_name] = threading.Lock()

        with file_locks[base_name]:
            logger.info(f"开始处理文件 {base_name} 的知识图谱...")
            start_time = time.time()

            # 知识图谱构建过程
            r = kg_manager.知识图谱的构建(text_content)
            logger.info(f"知识图谱构建完成，耗时: {time.time() - start_time:.2f}秒")

            # 转换为有向图
            kg_manager.三元组转有向图nx(r)

            # 绘制知识图谱
            start_time = time.time()
            kg_manager.绘制知识图谱(base_name)
            kg_manager.original_file_type = original_filename  # 使用原始文件名
            kg_manager.save_store()
            logger.info(f"知识图谱绘制完成，耗时: {time.time() - start_time:.2f}秒")

            # 保存并移动结果文件
            result_file = f"{base_name}.html"
            if os.path.exists(result_file):
                shutil.move(result_file, os.path.join(RESULT_FOLDER, result_file))
            else:
                raise FileNotFoundError("未生成结果HTML文件")

            # 更新处理状态
            PROCESS_STATUS[base_name] = "completed"

            # 同步到RAG管理器
            try:
                rag_manager.load_store(base_name)
                logger.info(f"已同步知识图谱到RAG管理器: {base_name}")
            except Exception as e:
                logger.error(f"同步知识图谱到RAG管理器失败: {str(e)}")

    except Exception as e:
        error_msg = str(e)
        PROCESS_STATUS[base_name] = f"error: {error_msg}"
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

        # 更新状态为处理中
        PROCESS_STATUS[base_name] = "processing"

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

        process_knowledge_graph(base_name, text_content, filename)

        # 更新最终状态
        PROCESS_STATUS[base_name] = "completed"
        logger.info(f"文件 {filename} 处理完成")

    except Exception as e:
        error_msg = f"文件处理失败: {str(e)}"
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

    if status:
        result_exists = os.path.exists(os.path.join(RESULT_FOLDER, f'{base_name}.html'))
        return JSONResponse({
            "status": status,
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
        # 获取所有文件ID
        files = kg_manager.list_files()['ids']
        metadatas = kg_manager.list_files()['metadatas']

        # 处理文件名，确保格式统一
        processed_files = []
        for i, file_id in enumerate(files):
            base_name = os.path.splitext(file_id)[0]
            # 获取原始文件名
            original_filename = metadatas[i].get('original_file_type', file_id)

            processed_files.append({
                "filename": original_filename,  # 使用原始文件名
                "status": PROCESS_STATUS.get(base_name, "completed")
            })

        return JSONResponse({"files": processed_files})
    except Exception as e:
        logger.error(f"获取文件列表失败: {str(e)}")
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