from sentence_transformers import SentenceTransformer

from LLM.Deepseek_agent import DeepSeekAgent
from OmniStore.chromadb_store import StoreTool
from TextSlicer.SimpleTextSplitter import SemanticTextSplitter
from KnowledgeGraphManager.KGManager import KgManager


embeddings = SentenceTransformer(
    r'D:\Models_Home\Huggingface\models--BAAI--bge-base-zh\snapshots\0e5f83d4895db7955e4cb9ed37ab73f7ded339b6'
)
from OmniStore.chromadb_store import StoreTool
store = StoreTool(embedding_function=embeddings)
agent = DeepSeekAgent(api_key="sk-xx", embedding_model=embeddings)
splitter = SemanticTextSplitter(2045, 1024)
kg_manager = KgManager(agent=agent,splitter=splitter,embedding_model=embeddings,store=store)
# kg_manager.form_default("kg_manager_test")
print(kg_manager.list_files()['ids'],11111111)
# print(kg_manager.current_G)
#
# query = "介绍以下贝叶斯"
# rag_entity =  kg_manager.text2entity(query)
# print(rag_entity)
# #  社区搜索得到相关实体关联实体以便进行hybridrag
# graph  =  kg_manager.community_louvain_G(rag_entity)
# print(graph)
# results = kg_manager.select_vectors(query,1)
# vec = results
# # hybridrag
# result = agent.hybrid_rag(query,graph,vec)
# print(result)


