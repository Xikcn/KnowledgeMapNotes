# 基于知识图谱的笔记系统
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/Xikcn/KnowledgeMapNotes)

## 项目展示
https://github.com/user-attachments/assets/5b62e85b-1340-4b79-814c-994380a8e146

## 项目简介
这是一个基于知识图谱的笔记系统，通过将PDF文档转换为知识图谱，实现高效的知识管理和检索。系统支持PDF文档处理、实体关系提取、知识图谱构建与可视化，并提供基于RAG和知识图谱的智能问答功能。

## 主要功能
- PDF文档处理与转换
- 知识图谱自动构建
- 文档智能问答
- 知识实体关系可视化
- 增量更新知识库

## 技术栈
### 后端功能实现
1. pdf转txt（提取pdf的表格，获取图片信息）
2. 向量数据库（ChromaDB）
3. 提示词工程
4. RAG，HybridRAG
5. 知识图谱构建（kg-gen）
6. 图的社区查询
7. 消息队列（采用简单方式，不采用redis方便单机部署）
8. 增量更新（增加新增块的实体与关系，删除消失块相关实体与关系）
9. FastAPI

### 前端技术栈
1. Vue 3
2. Element Plus
3. ECharts
4. Axios
5. Vite

## 系统架构
- 文档处理模块：负责PDF文档的解析和文本提取
- 知识图谱模块：实现实体识别、关系抽取和知识图谱构建
- 检索模块：基于向量数据库的语义检索
- API服务：FastAPI实现的RESTful接口
- 前端应用：Vue3实现的用户界面

## 详细使用说明
### 文档上传与处理
1. 访问系统首页，点击"上传文档"按钮
2. 选择要上传的PDF文件，点击确认
3. 系统会自动处理文档并构建知识图谱
4. 处理完成后，可以在文档列表中查看已上传的文件

### 知识图谱查询
1. 在文档列表中选择要查询的文档
2. 点击"查看知识图谱"按钮
3. 系统会显示文档的知识图谱可视化结果
4. 可以通过点击节点查看详细信息，或者使用搜索功能定位特定实体

### 智能问答
1. 在文档列表中选择要问答的文档
2. 点击"开始问答"按钮
3. 在输入框中输入问题
4. 系统会基于文档内容和知识图谱提供回答

## 安装与使用
### 环境要求
- Python 3.8+
- Node.js 16+
- CUDA支持（推荐）
- torch( 可选，不用删除代码中的相关部分即可，不影响使用，主要是to() )

## API服务申请
### 获取视觉模型（如果不开启可以不用）
https://bailian.console.aliyun.com/?tab=api#/api
```pycon
vl_client = OpenAI(
    # 若没有配置环境变量，请用百炼API Key将下行替换为：api_key="sk-xxx"
    api_key='sk-xx',
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)
```

### 嵌入模型的使用
建议下载到本地离线处理（Huggingface）也可以使用网络库，会自动下载到本地，第二次换成本地可以快速启动
如果无法下载建议，去Huggingface官网下载到本地，直接使用本地模型
* 添加镜像
```python
import os
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
```

* bge-base-zh本地模型使用
```python
from sentence_transformers import SentenceTransformer
# 初始化模型和组件
# embeddings = SentenceTransformer('BAAI/bge-base-zh').to(device)
embeddings = SentenceTransformer(
    r"D:\Models_Home\Huggingface\hub\models--BAAI--bge-base-zh\snapshots\0e5f83d4895db7955e4cb9ed37ab73f7ded339b6"
    )
```


### 后端安装
```bash
# 安装依赖
pip install -r requirements.txt
# uv安装依赖
# uv pip install -r requirements.txt
# 启动服务
python app.py
```

### 前端安装
```bash
# 进入前端目录
cd projects/vue
# 安装依赖
npm install
# 启动开发服务器
npm run dev
```

### 完整部署流程
1. 克隆仓库
```bash
git clone https://github.com/yourusername/knowledge-map-notes.git
cd knowledge-map-notes
```

2. 安装后端依赖
```bash
pip install -r requirements.txt
```

3. 安装前端依赖
```bash
cd projects/vue
npm install
```

4. 构建前端（生产环境）
```bash
npm run build
```

5. 启动后端服务
```bash
cd ../..
python app.py
```

6. 访问系统
浏览器中打开 http://localhost:8000


## 目录结构
- `app.py`: 主应用入口
- `OmniText/`: 文本处理模块
- `KnowledgeGraphManager/`: 知识图谱管理模块
- `LLM/`: 大语言模型交互
- `TextSlicer/`: 文本分割工具
- `embedding_tools/`: 向量嵌入工具
- `projects/vue/`: 前端Vue项目
- `prompt/`: 提示词模板
- `chroma_data/`: 向量数据库存储
- `uploads/`: 上传文件存储
- `txt_files/`: 处理后文本存储
- `results/`: 结果输出目录
- `docs/`: 文档说明
- `lib/`: 通用库函数
- `output/`: 临时输出文件
- `images/`: 图片资源


## 常见问题
### Q: 系统支持哪些类型的PDF文件？
A: 系统支持大多数标准PDF文件，包括文本PDF和扫描PDF（需OCR）。

### Q: 如何更新知识图谱？
A: 重新上传文档或使用增量更新功能可更新知识图谱。

## 待完成的功能
- 问题生成（通过rag你好会自动生成）
- 前端加入差异对比（展示没必要）
- 对于实体可联网获取相关知识，如果当前知识图谱无法解决（待新增）
- 文本分块进行rag的部分有问题（有些文本丢失）
- 生成试卷进行学生的复习（允许联网生成易错选项）
- 对上传的笔记可以进行检查功能，如有存在公理上的错误则提示用户进行修改
- 增量更新没删除需要删除的块只新增块了（解决bid生成的问题）
- 携带聊天内容会对增量更新后问答具有一部分记忆（无伤大雅，关闭携带历史记录即可，或者清理聊天记录）

## 可替换的技术栈
* mineru 用于pdf转markdown，替换多模态2txt功能
* 

## 许可证
MIT

