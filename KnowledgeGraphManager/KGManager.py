import json
import re
from collections import defaultdict
from community import community_louvain
from pyvis.network import Network
import networkx as nx


class KgManager:
    def __init__(self,agent,splitter,embedding_model,store):
        self.store = store
        # 大模型的对象
        self.Agent = agent
        # 用于分割文本
        self.splitter = splitter
        # 文本嵌入模型
        self.embeddings = embedding_model
        # 文件名
        self.file = ""
        # 原始文件类型
        self.original_file_type = ""
        # 当前 文本块bid-对应的关系的表
        self.kg_triplet = []
        # 当前 实体-实体标签映射表
        self.bidirectional_mapping = {
            "entity_to_label": {},
            "label_to_entities": defaultdict(list)
        }
        # 当前 有向图
        self.current_G = nx.DiGraph()
        # 当前 文本分块
        self.Bolts = []

    def form_default(self,filename):
        default_data = self.store.load_state(filename)
        if default_data:
            self.file = default_data['file']
            self.kg_triplet = default_data['kg_triplet']
            self.bidirectional_mapping = default_data['bidirectional_mapping']
            self.current_G = default_data['current_G']
            self.Bolts = default_data['Bolts']
            self.original_file_type = default_data.get('original_file_type', '.txt')
        else:
            return None


    # 实体与实体类型的字典建立
    def _build_bidirectional_mapping(self, data):
        mapping = {
            "entity_to_label": {},
            "label_to_entities": defaultdict(list)
        }
        seen_entities = set()

        for entity, label in data:
            if entity not in seen_entities:
                mapping["entity_to_label"][entity] = label
                mapping["label_to_entities"][label].append(entity)
                seen_entities.add(entity)

        return mapping

    # 实体-标签表 利用实体获取标签
    def get_entity_label(self, knowledge_graph, entity):
        return knowledge_graph["entity_to_label"].get(entity, "未知标签")

    # 实体-标签表 利用标签获取实体
    def get_entities_by_label(self, knowledge_graph, label):
            return knowledge_graph["label_to_entities"].get(label, [])

    # 用于将文本分块处理
    def _Txt2Bolts(self,text):
        # begin  存入向量数据库
        documents = []
        embed = []
        ids = []
        self.Bolts = self.splitter.split_text(text)
        for bid, Bolt in self.Bolts:
            ids.append(bid)
            documents.append(Bolt)
            embed.append(self.embeddings.encode(Bolt))
        return self.Bolts


    def 实体提取(self,input_parameter):
        entity_label = []
        prompt = open("./prompt/v2/entity_extraction2.txt", encoding='utf-8').read()
        output = self.Agent.ollama_safe_generate_response(prompt, input_parameter)
        entity_label += output["entities"]
            # print(output)
        return entity_label

    def 关系提取(self,input_parameter,entity):
        prompt2 = open("./prompt/v2/relationship_extraction2.txt", encoding='utf-8').read()
        output2 = self.Agent.ollama_safe_generate_response(
            prompt2, "笔记内容：" + input_parameter + "\n实体列表：" + json.dumps(entity))
        relations = output2["relations"]
        return relations


    def 知识融合(self,relations):
        pass
        relations_tuning = relations
        return relations_tuning

    # 输入处理好的分割文本，输出bid与实体-关系三元集合
    def 知识图谱的构建(self,text=None):
        if type(text) == str:
            self.Bolts = self._Txt2Bolts(text)
        elif type(text) == list:
            self.Bolts = text
        elif text is None:
           pass
        kg_triplet = []
        entity_labels = []
        for bid, Bolt in self.Bolts:
            entity_label = self.实体提取(Bolt)
            # 修复BUG，应为entity和label同时传入模型导致认为标签也是实体名而非实体类型
            entity = [i[0] for i in entity_label]
            relation = self.关系提取(Bolt,entity)
            # 没写知识融合，考虑个根据用户喜好进行融合
            self.知识融合(relation)
            entity_labels+=entity_label
            kg_triplet += [{"bid": bid, "relation": relation}]

        self.bidirectional_mapping = self._build_bidirectional_mapping(entity_labels)
        self.kg_triplet = kg_triplet
        return kg_triplet



    def 三元组转有向图nx(self,relations):
        knowledge_graph = self.bidirectional_mapping
        self.current_G = nx.DiGraph()
        for relation in relations:
            for rel in relation['relation']:
                source = rel['source']
                target = rel['target']
                context = rel['context']
                relation = rel['relation']

                # 添加节点
                self.current_G.add_node(source,
                                        title=self.get_entity_label(knowledge_graph, source),
                                        group=self.get_entity_label(knowledge_graph, source))
                self.current_G.add_node(target,
                                        title=self.get_entity_label(knowledge_graph, target),
                                        group=self.get_entity_label(knowledge_graph, target))

                # 添加边（初始状态）
                self.current_G.add_edge(source, target,
                                        title=context,
                                        label=relation,
                                        font={"size": 0},  # 初始标签隐藏
                                        color='#97c2fc',
                                        width=2,
                                        hoverWidth=4,
                                        chosen={  # 点击选中样式
                                            "edge": {
                                                "color": "#00FF00",
                                                "width": 4
                                            }
                                        })
        return self.current_G

    # 增量更新找到要处理的块
    def _replace_blocks_and_find_changes(self, original_blocks, new_text, split_text_fun):
        def normalize_text(text):
            """去除首尾空格、合并多余空格、换行转换为空格"""
            return re.sub(r'\s+', ' ', text.strip())

        """用原文块替换未变部分，找出新增和删除的块"""
        normalized_new_text = normalize_text(new_text)  # 归一化新文本
        replaced_text = normalized_new_text  # 复制新文本
        matched_blocks = set()  # 记录匹配的块文本

        # **第一步**：替换未变的部分
        for bid, text in original_blocks:
            norm_text = normalize_text(text)
            if norm_text in replaced_text:
                replaced_text = replaced_text.replace(norm_text, bid, 1)
                matched_blocks.add(norm_text)

        # **第二步**：计算删除的块（原文本中未出现在新文本中的部分）
        deleted_blocks = [(bid, text) for bid, text in original_blocks if
                          normalize_text(text) not in normalized_new_text]

        # **第三步**：用 `block_id` 作为分隔符，分割出变动部分
        split_pattern = '|'.join(re.escape(bid) for bid, _ in original_blocks)
        unmatched_parts = re.split(split_pattern, replaced_text)  # 只保留变动部分
        unmatched_parts = [normalize_text(part) for part in unmatched_parts if part.strip()]  # 清理空格

        # **第四步**：用你的 `split_text()` 切割新增内容
        added_texts = []
        for part in unmatched_parts:
            added_texts.extend([t for t in split_text_fun(part) if t])

        # **第五步**：分配新增块 ID
        added_blocks = [text for i, text in enumerate(added_texts)]

        return replaced_text, deleted_blocks, added_blocks

    def 增量更新(self, new_text:str):
        replaced_new_text, deleted_blocks, added_blocks = self._replace_blocks_and_find_changes(
            self.Bolts,
            new_text,
            self.splitter.split_text)

        # 输出
        # print("新文本替换后的文本:")
        # print(replaced_new_text)
        #
        # print("\n被删除的块:")
        # for bid, text in deleted_blocks:
        #     print(f"{bid}: {text}")
        #
        # print("\n新增的块:")
        # for bid, text in added_blocks:
        #     print(f"{bid}: {text}")
        bids_to_remove = []

        # 被删除的块
        for bid, text in deleted_blocks:
            bids_to_remove.append(bid)

        filtered_data = [item for item in self.kg_triplet if item['bid'] not in bids_to_remove]

        self.store.vector_collection.delete(
            where={"file": self.file},
            ids=bids_to_remove
        )

        add_data = []


        # 新增的块
        for bid, text in added_blocks:
            add_data.append((bid, text))

        self.kg_triplet = self.知识图谱的构建(add_data)
        new_kg_triplet = self.kg_triplet + filtered_data

        return new_kg_triplet


    # 绘制图谱保存为html并且返回network的nx.DiGraph()有向图对象
    def 绘制知识图谱(self, name):
        self.file = name
        # 使用pyvis可视化
        net = Network(notebook=True, height="750px", width="100%",
                      bgcolor="#ffffff", font_color="black", directed=True)
        # 配置选项
        options = {
            "edges": {
                "font": {
                    "size": 0,
                    "face": "arial",
                    "align": "middle"
                },
                "color": {
                    "inherit": False,
                    "highlight": "#FFA500",
                    "hover": "#FFA500"
                },
                "selectionWidth": 1.5,
                "smooth": {"type": "continuous"}
            },
            "interaction": {
                "hover": True,
                "tooltipDelay": 150,
                "hideEdgesOnDrag": False,
                "multiselect": True  # 允许多选
            }
        }
        net.set_options(json.dumps(options, indent=2))

        # 从NetworkX图导入数据
        net.from_nx(self.current_G)

        # 生成HTML文件
        html_file = f"{name}.html"
        net.show(html_file)

        # 增强交互功能
        with open(html_file, "r+", encoding="utf-8") as f:
            content = f.read()

            js_injection = """
              <style>
                  .control-panel {
                      position: absolute;
                      top: 10px;
                      right: 10px;
                      z-index: 1000;
                      background: rgba(255,255,255,0.9);
                      padding: 10px;
                      border-radius: 5px;
                      box-shadow: 0 2px 10px rgba(0,0,0,0.2);
                  }
                  .control-btn {
                      padding: 8px 12px;
                      margin: 5px;
                      border: none;
                      border-radius: 4px;
                      cursor: pointer;
                      font-size: 14px;
                      transition: all 0.3s;
                  }
                  .control-btn:hover {
                      transform: translateY(-2px);
                      box-shadow: 0 2px 5px rgba(0,0,0,0.2);
                  }
                  #showAllBtn {
                      background-color: #4CAF50;
                      color: white;
                  }
                  #hideAllBtn {
                      background-color: #f44336;
                      color: white;
                  }
                  #toggleBtn {
                      background-color: #2196F3;
                      color: white;
                  }
                  #resetBtn {
                      background-color: #9E9E9E;
                      color: white;
                  }
                  .status-indicator {
                      margin-top: 10px;
                      font-size: 12px;
                      color: #555;
                  }
              </style>

              <script>
              // 全局状态管理
              const edgeStates = {};
              let globalHideMode = true;

              document.addEventListener("DOMContentLoaded", function() {
                  // 初始化所有边状态
                  network.body.data.edges.get().forEach(edge => {
                      edgeStates[edge.id] = {
                          clicked: false,
                          labelVisible: false
                      };
                  });

                  // 创建控制面板
                  const container = document.getElementById("mynetwork");
                  const panel = document.createElement("div");
                  panel.className = "control-panel";
                  panel.innerHTML = `
                      <button id="showAllBtn" class="control-btn">显示所有标签</button>
                      <button id="hideAllBtn" class="control-btn">隐藏未点击标签</button>
                      <button id="toggleBtn" class="control-btn">切换显示状态</button>
                      <button id="resetBtn" class="control-btn">重置所有状态</button>
                      <div class="status-indicator">已复习: <span id="counter">0</span>/${network.body.data.edges.get().length}</div>
                  `;
                  container.parentNode.insertBefore(panel, container);

                  // 更新计数器
                  function updateCounter() {
                      const count = Object.values(edgeStates).filter(s => s.clicked).length;
                      document.getElementById("counter").innerText = count;
                  }

                  // 显示所有标签
                  document.getElementById("showAllBtn").onclick = function() {
                      network.body.data.edges.get().forEach(edge => {
                          edge.font = {size: 14};
                          edge.color = {color: "#97c2fc"};
                          network.body.data.edges.update(edge);
                          edgeStates[edge.id].labelVisible = true;
                      });
                      globalHideMode = false;
                      updateCounter();
                  };

                  // 隐藏未点击标签
                  document.getElementById("hideAllBtn").onclick = function() {
                      network.body.data.edges.get().forEach(edge => {
                          if (!edgeStates[edge.id].clicked) {
                              edge.font = {size: 0};
                              edge.color = {color: "#97c2fc"};
                              network.body.data.edges.update(edge);
                              edgeStates[edge.id].labelVisible = false;
                          }
                      });
                      globalHideMode = true;
                      updateCounter();
                  };

                  // 切换显示状态
                  document.getElementById("toggleBtn").onclick = function() {
                      globalHideMode = !globalHideMode;
                      network.body.data.edges.get().forEach(edge => {
                          edge.font = {size: globalHideMode && !edgeStates[edge.id].clicked ? 0 : 14};
                          network.body.data.edges.update(edge);
                          edgeStates[edge.id].labelVisible = !globalHideMode || edgeStates[edge.id].clicked;
                      });
                      updateCounter();
                  };

                  // 重置所有状态
                  document.getElementById("resetBtn").onclick = function() {
                      network.body.data.edges.get().forEach(edge => {
                          edge.font = {size: 0};
                          edge.color = {color: "#97c2fc"};
                          network.body.data.edges.update(edge);
                          edgeStates[edge.id] = {
                              clicked: false,
                              labelVisible: false
                          };
                      });
                      globalHideMode = true;
                      updateCounter();
                  };

                  // 点击边持久化显示
                  network.on("selectEdge", function(params) {
                      const edge = network.body.data.edges.get(params.edges[0]);
                      edgeStates[edge.id].clicked = true;
                      edge.font = {size: 14};
                      edge.color = {color: "#00FF00", highlight: "#00FF00"};
                      network.body.data.edges.update(edge);
                      updateCounter();
                  });

                  // 悬停边时高亮
                  network.on("hoverEdge", function(params) {
                      const edge = network.body.data.edges.get(params.edge);
                      if (!edgeStates[edge.id].clicked) {
                          edge.color = {color: "#FFA500", highlight: "#FFA500"};
                          network.body.data.edges.update(edge);
                      }
                  });

                  // 移出边时恢复
                  network.on("blurEdge", function(params) {
                      const edge = network.body.data.edges.get(params.edge);
                      if (!edgeStates[edge.id].clicked) {
                          edge.color = {color: "#97c2fc", highlight: "#97c2fc"};
                          network.body.data.edges.update(edge);
                      }
                  });

                  updateCounter();
              });
              </script>
              """
            content = content.replace("</body>", js_injection + "</body>")
            content = content.replace(f' <script src="lib/bindings/utils.js"></script>','')
            f.seek(0)
            f.write(content)
            f.truncate()

        print(f"知识图谱已生成，保存为 {html_file}")
        return self.current_G

    # 获取提问的实体（存在与知识图谱的）
    def text2entity(self, text):
        prompt = open("./prompt/v2/entity_q2merge.txt", encoding='utf-8').read()
        entity = [str(i) for i in self.current_G]
        input_parameter = f"实体列表：{entity}\n问题：{text}"
        output = self.Agent.ollama_safe_generate_response(prompt, input_parameter)
        return output['entities']


    # 社区搜索
    def community_louvain_G(self,entity_names):
        knowledge_base = []
        # 执行社区检测（在整个图上）
        partition = community_louvain.best_partition(self.current_G.to_undirected())
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
        subgraph = self.current_G.subgraph(community_nodes)

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
        modularity = community_louvain.modularity(partition, self.current_G.to_undirected())
        print(f"\nModularity of the entire graph: {modularity}")

        return knowledge_base


    # 对比两个有向图对象的差异
    def compare_and_visualize(self, G2, output_file="diff_graph"):
        G1 = self.current_G.to_undirected()
        """比较两个有向图并用pyvis高亮差异"""
        # 创建合并图（包含G1和G2的所有节点和边）
        G_diff = nx.DiGraph()

        # 记录差异
        diff = {
            "added_nodes": set(G2.nodes()) - set(G1.nodes()),
            "removed_nodes": set(G1.nodes()) - set(G2.nodes()),
            "added_edges": set(G2.edges()) - set(G1.edges()),
            "removed_edges": set(G1.edges()) - set(G2.edges()),
            "node_attr_changes": {},
            "edge_attr_changes": {}
        }

        # 检查节点属性变化
        common_nodes = set(G1.nodes()) & set(G2.nodes())
        for node in common_nodes:
            if G1.nodes[node] != G2.nodes[node]:
                diff["node_attr_changes"][node] = {
                    "old": G1.nodes[node],
                    "new": G2.nodes[node]
                }

        # 检查边属性变化
        common_edges = set(G1.edges()) & set(G2.edges())
        for u, v in common_edges:
            if G1.edges[u, v] != G2.edges[u, v]:
                diff["edge_attr_changes"][(u, v)] = {
                    "old": G1.edges[u, v],
                    "new": G2.edges[u, v]
                }

        # 将差异信息添加到图
        for node in G1.nodes() | G2.nodes():
            G_diff.add_node(node)

            # 设置节点颜色和标题（悬停显示详情）
            if node in diff["added_nodes"]:
                G_diff.nodes[node]["color"] = "green"
                G_diff.nodes[node]["title"] = f"新增节点: {node}"
            elif node in diff["removed_nodes"]:
                G_diff.nodes[node]["color"] = "red"
                G_diff.nodes[node]["title"] = f"删除节点: {node}"
            elif node in diff["node_attr_changes"]:
                G_diff.nodes[node]["color"] = "yellow"
                changes = diff["node_attr_changes"][node]
                G_diff.nodes[node]["title"] = (
                    f"节点属性修改: {node}\n"
                    f"旧值: {changes['old']}\n"
                    f"新值: {changes['new']}"
                )
            else:
                G_diff.nodes[node]["color"] = "skyblue"

        for u, v in G1.edges() | G2.edges():
            if (u, v) in diff["added_edges"]:
                G_diff.add_edge(u, v, color="green", title=f"新增边: ({u}→{v})")
            elif (u, v) in diff["removed_edges"]:
                G_diff.add_edge(u, v, color="red", title=f"删除边: ({u}→{v})")
            elif (u, v) in diff["edge_attr_changes"]:
                changes = diff["edge_attr_changes"][(u, v)]
                G_diff.add_edge(u, v, color="yellow",
                                title=f"边属性修改: ({u}→{v})\n旧值: {changes['old']}\n新值: {changes['new']}")
            else:
                G_diff.add_edge(u, v, color="gray")

        # 用pyvis绘制动态图
        nt = Network(height="900px", width="100%", notebook=True)
        nt.from_nx(G_diff)

        # 保存并显示
        nt.show(f"{output_file}.html")

    def save_store(self):
        """将当前状态保存到存储"""
        if self.store:
            self.store.save_state(self)

    def load_store(self, filename):
        """从存储加载指定文件名的状态"""
        if self.store:
            state = self.store.load_state(filename)
            if state:
                self.file = state["file"]
                self.kg_triplet = state["kg_triplet"]
                self.bidirectional_mapping = state["bidirectional_mapping"]
                self.current_G = state["current_G"]
                self.Bolts = state["Bolts"]
                self.original_file_type = state.get('original_file_type', '.txt')
                return True
        return False

    def delete_store(self, filenames: list):
        return self.store.delete_states(filenames)


    def list_files(self):
        return self.store.list_files()


    def select_vectors(self,query,n_results):
        results = self.store.select_vectors(
            query=query,
            file=self.file,
            n_results=n_results
        )

        return results["documents"]







