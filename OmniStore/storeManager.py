import random
from community import community_louvain


class  storeManager:
    def __init__(self,store,agent):
        self.store = store
        self.agent = agent

    def list_files(self):
        return self.store.list_files()


    def get_G(self, file):
        try:
            state = self.store.load_state(file)
            if state is None or 'current_G' not in state:
                print(f"找不到文件的知识图谱状态: {file}")
                return None

            current_G = state['current_G']
            return current_G
        except Exception as e:
            print(f"加载知识图谱出错: {file}, 错误: {str(e)}")
            return None

    def get_n_entity(self,file,n):
        # "bidirectional_mapping": {
        #     "entity_to_label": dict(json.l
        try:
            state = self.store.load_state(file)
            if state is None or 'bidirectional_mapping' not in state:
                print(f"找不到文件的实体状态: {file}")
                return None

            entity = list(state['bidirectional_mapping']['entity_to_label'].keys())
            if len(entity) <= n:
                return entity
            return random.sample(entity, n)

        except Exception as e:
            print(f"加载知识图谱出错: {file}, 错误: {str(e)}")
            return None

    def edge_max_node(self,file,n):
        current_g = self.get_G(file)
        degrees = current_g.degree()
        sorted_degrees = sorted(degrees, key=lambda x: x[1], reverse=True)
        return sorted_degrees[:n]



    def text2entity(self, query: str, file: str):
        current_g = self.get_G(file)
        # 添加对current_G为None的检查
        if current_g is None:
            print(f"无法获取知识图谱数据: {file}")
            return []

        prompt = open("./prompt/v2/entity_q2merge.txt", encoding='utf-8').read()
        entity = [str(i) for i in current_g]
        input_parameter = f"实体列表：{entity}\n问题：{query}"
        output = self.agent.ollama_safe_generate_response(prompt, input_parameter)
        return output['entities']

    def select_vectors(self, query, file, n_results):
        try:
            results = self.store.select_vectors(
                query=query,
                file=file,
                n_results=n_results
            )
            return results.get("documents", [])
        except Exception as e:
            print(f"选择向量失败: {file}, 错误: {str(e)}")
            return []


    def community_louvain_G(self,file,entity_names):
        current_G = self.get_G(file)
        if current_G is None:
            print(f"无法获取知识图谱数据进行社区检测: {file}")
            return []

        knowledge_base = []

        # 执行社区检测（在整个图上）
        partition = community_louvain.best_partition(current_G.to_undirected())
        for node, community_id in partition.items():
            pass
            # print(f"Node {node} belongs to community {community_id}")

        # 获取每个输入实体的社区编号
        community_ids = set()
        for entity in entity_names:
            if entity in partition:
                community_ids.add(partition[entity])

        # 提取特定社区内的所有节点
        community_nodes = [node for node, comm_id in partition.items() if comm_id in community_ids]

        # 构建包含选定社区内所有节点的子图
        subgraph = current_G.subgraph(community_nodes)

        # 输出结果
        # print("Selected Community Nodes and Edges:")

        # 打印每个节点及其社区编号和属性
        for node in subgraph.nodes(data=True):
            node_name = node[0]
            node_attributes = node[1]
            community_id = partition.get(node_name, 'No Community')
            # print(f"Node: {node_name}, Attributes: {node_attributes}, Community ID: {community_id}")

        # 打印边的信息，检查是否存在'title'属性，如果不存在则使用默认值
        for edge in subgraph.edges(data=True):
            relation = edge[2].get('title', 'No Title')  # 如果没有'title'属性，则返回默认值'No Title'
            # print(edge,111111111111111)
            # print(f"Edge from {edge[0]} to {edge[1]}, Relation: {relation}")
            knowledge_base.append(
                f"Edge from {edge[0]} to {edge[1]}, Relation: {relation}, context:{edge[2].get('title', 'No Title')}")

        # 如果需要更详细的社区信息，可以计算模块度等
        modularity = community_louvain.modularity(partition, current_G.to_undirected())
        print(f"\nModularity of the entire graph: {modularity}")

        return knowledge_base




