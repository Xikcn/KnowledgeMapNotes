import json
import re
import time
from openai import OpenAI


class DeepSeekAgent:
    def __init__(self,api_key,embedding_model):
        # 大模型
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com"
        )
        self.rag_client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com"
        )
        # 回答问题使用的嵌入模型
        self.embeddings = embedding_model


    def temp_sleep(self, seconds=0.1):
        time.sleep(seconds)

    def ollama_safe_generate_response(self, prompt, input_parameter, repeat=3):
        for i in range(repeat):
            try:
                curr_gpt_response = self.ollama_request(prompt, input_parameter)
                x = ""
                if 'json' in curr_gpt_response:
                    pattern = r"```json\s*({.*?})\s*```"
                    match = re.search(pattern, curr_gpt_response, re.DOTALL)
                    if match:
                        json_content = match.group(1)
                        x = json.loads(json_content)
                    else:
                        print("未找到匹配的 JSON 内容")
                        continue
                return x
            except:
                print("ERROR")
        return -1

    def ollama_request(self, prompt, input_parameter):
        self.temp_sleep()
        response = self.client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": prompt},
                {'role': 'user', 'content': input_parameter}],
            temperature=1
        )
        output = response.choices[0].message.content
        return output


    def ollama_safe_generate_response_rag(self, prompt, input_parameter,messages, repeat=3):
        for i in range(repeat):
            try:
                curr_gpt_response = self.ollama_request_rag(prompt, input_parameter,messages)
                x = ""
                if 'json' in curr_gpt_response:
                    pattern = r"```json\s*({.*?})\s*```"
                    match = re.search(pattern, curr_gpt_response, re.DOTALL)
                    if match:
                        json_content = match.group(1)
                        x = json.loads(json_content)
                    else:
                        print("未找到匹配的 JSON 内容")
                        continue
                return x
            except:
                print("ERROR")
        return -1

    def ollama_request_rag(self, prompt, input_parameter, messages):
        # 确保消息格式正确
        formatted_messages = [{"role": "system", "content": prompt}]
        if messages:
            formatted_messages.extend(messages)
        formatted_messages.append({'role': 'user', 'content': input_parameter})

        response = self.rag_client.chat.completions.create(
            model="deepseek-chat",
            messages=formatted_messages,
            temperature=1
        )
        output = response.choices[0].message.content
        return output

    def hybrid_rag(self, query, graph, vectors, messages):
        prompt = open("./prompt/v2/rag_v1_hybrid.txt", encoding='utf-8').read()
        input_parameter = open("./prompt/v2/rag_v1_query_hy.txt", encoding='utf-8').read()
        graph_relation = "\n".join(graph)
        context = "\n".join(vectors)
        input_parameter = input_parameter.replace("{{query}}", query)
        input_parameter = input_parameter.replace("{{relation}}", graph_relation)
        input_parameter = input_parameter.replace("{{context}}", context)

        # 确保 messages 是列表且格式正确
        if not isinstance(messages, list):
            messages = []
        if messages and isinstance(messages[0], dict):
            messages = [{"role": msg.get("role", ""), "content": msg.get("content", "")} for msg in messages]

        output = self.ollama_safe_generate_response_rag(prompt, input_parameter, messages)
        return output


