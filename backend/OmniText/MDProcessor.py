import os
import re
from typing import Union, List, Dict, Optional

class MDProcessor:
    def __init__(self, output_dir: str = "output",vl_client=None):
        self.output_dir = output_dir
        self.results = {}  # {filename: [内容列表]}
        os.makedirs(self.output_dir, exist_ok=True)

    def _parse_qa_table(self, md_text: str) -> List[str]:
        """
        解析markdown中的QA表格，转为Qn:... An:... </end>格式
        """
        lines = md_text.splitlines()
        qa_section = False
        qa_rows = []
        for idx, line in enumerate(lines):
            if re.match(r"^##\s*问答", line):
                qa_section = True
                continue
            if qa_section:
                # 表头和分隔符跳过
                if re.match(r"^\|\s*问题", line) or re.match(r"^\|\s*:?[-]+", line):
                    continue
                # 空行或下一个section结束
                if line.strip() == '' or line.startswith('#'):
                    break
                # 匹配表格行
                if line.startswith('|'):
                    # 去除首尾|，按|分割
                    cells = [cell.strip() for cell in line.strip('|').split('|')]
                    if len(cells) >= 2:
                        qa_rows.append((cells[0], cells[1]))
        # 转换为Qn/An格式
        output = []
        for i, (q, a) in enumerate(qa_rows, 1):
            q = q.replace('[换行]', '\n').replace('目前：', '').strip()
            a = a.replace('[换行]', '\n').strip()
            if q or a:
                output.append(f"Q{i}:{q}\nA{i}:{a}\n</end>")
        return output

    def process(self, md_files: Union[str, List[str]], use_img2txt: bool = False):
        if isinstance(md_files, str):
            md_files = [md_files]
        for path in md_files:
            if not os.path.exists(path):
                print(f"文件不存在: {path}")
                continue
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            filename = os.path.basename(path)
            parsed = self._parse_qa_table(content)
            self.results[filename] = parsed

    def save_as_txt(self, combine: bool = False, output_path: Optional[str] = None):
        if not self.results:
            print("没有可保存的结果")
            return
        if combine:
            combined = []
            for filename, content in self.results.items():
                combined.append(f"\n{'=' * 20} {filename} {'=' * 20}\n")
                combined.extend(content)
            final_path = output_path or os.path.join(self.output_dir, "combined_md_output.txt")
            with open(final_path, "w", encoding="utf-8") as f:
                f.write("\n".join(combined))
            print(f"合并保存到: {final_path}")
        else:
            for filename, content in self.results.items():
                if output_path:
                    if os.path.dirname(output_path):
                        final_path = output_path
                    else:
                        final_path = os.path.join(self.output_dir, output_path)
                else:
                    final_path = os.path.join(self.output_dir, f"{os.path.splitext(filename)[0]}.txt")
                with open(final_path, "w", encoding="utf-8") as f:
                    f.write("\n".join(content))
                print(f"保存到: {final_path}")

    def get_output(self, combine: bool = False) -> Union[str, Dict[str, str]]:
        if not self.results:
            return "" if combine else {}
        if combine:
            combined = []
            for filename, content in self.results.items():
                combined.append(f"\n{'=' * 20} {filename} {'=' * 20}\n")
                combined.extend(content)
            return "\n".join(combined)
        else:
            return {filename: "\n".join(content) for filename, content in self.results.items()}
