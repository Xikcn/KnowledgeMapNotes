from OmniText.PDFProcessor import PDFProcessor
import os
import shutil




# 判断文件列表中文件是pdf还是txt选择对应的函数执,最终需要纯文本
# 处理多个文件
files = [
    r"D:\Python_workspace\AI_NOTE\docs\文献综述4.pdf",
    r"D:\Python_workspace\AI_NOTE\docs\test_text.txt"
]

# 创建输出目录
output_dir = "output/text"
image_dir = "output/images"
os.makedirs(output_dir, exist_ok=True)

# 分离PDF和TXT文件
pdf_files = [f for f in files if f.lower().endswith('.pdf')]
txt_files = [f for f in files if f.lower().endswith('.txt')]

# 处理pdf
# 初始化处理器
processor = PDFProcessor(output_dir=output_dir, image_dir=image_dir)
processor.process(pdf_files)
# 保存为单独文件
processor.save_as_txt(combine=False)


# 处理TXT文件：复制到输出目录并读取内容
for txt_path in txt_files:
    # 复制TXT文件到输出目录
    shutil.copy2(txt_path, output_dir)



from LLM.Deepseek_agent  import  DeepSeekAgent
from sentence_transformers import SentenceTransformer
from KnowledgeGraphManager.KGManager import KgManager
from TextSlicer.SimpleTextSplitter import SemanticTextSplitter

embeddings = SentenceTransformer(
    r'D:\Models_Home\Huggingface\models--BAAI--bge-base-zh\snapshots\0e5f83d4895db7955e4cb9ed37ab73f7ded339b6'
)
agent = DeepSeekAgent(api_key="sk-xx", embedding_model=embeddings)
splitter = SemanticTextSplitter(2045, 1024)
# store
from OmniStore.chromadb_store import StoreTool
store = StoreTool(embedding_function=embeddings)
kg_manager = KgManager(agent=agent,splitter=splitter,embedding_model=embeddings,store=store)

f = open(r"D:\Python_workspace\AI_NOTE\output\text\test_text.txt",encoding='utf-8').read()


r = kg_manager.知识图谱的构建(f)
kg_manager.三元组转有向图nx(r)
G1 = kg_manager.绘制知识图谱("kg_manager_test1")
print(kg_manager.list_files())
print(store.load_state("kg_manager_test1"))
query = "介绍贝叶斯"
rag_entity =  kg_manager.text2entity(query)
print(rag_entity)
#  社区搜索得到相关实体关联实体以便进行hybridrag
graph  =  kg_manager.community_louvain_G(rag_entity)
print(graph)
results = kg_manager.select_vectors(query,1)
vec = results
# hybridrag
result = agent.hybrid_rag(query,graph,vec,[])
print(result)
kg_manager.save_store()
kg_manager.delete_store(["kg_manager_test"])
print(store.list_files())

print(store.load_state("kg_manager_test1"))











