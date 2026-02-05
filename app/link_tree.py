"""Link tree parsing and management."""

from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
import csv
import json

try:
    import networkx as nx
    HAS_NETWORKX = True
except ImportError:
    HAS_NETWORKX = False


class TreeNode:
    """트리 노드 클래스"""
    
    def __init__(self, keyword: str, level: int = 0):
        self.keyword = keyword
        self.level = level
        self.children: List[TreeNode] = []
        self.parent: Optional[TreeNode] = None
    
    def add_child(self, child: "TreeNode"):
        child.parent = self
        self.children.append(child)
    
    def get_all_keywords(self) -> Set[str]:
        """자신과 모든 자식 노드의 키워드를 반환"""
        keywords = {self.keyword}
        for child in self.children:
            keywords.update(child.get_all_keywords())
        return keywords


def parse_tree_file(file_path: Path) -> Optional[TreeNode]:
    """indent 기반 트리 파일 파싱 (공백 4개 단위로 위계 표현)"""
    if not file_path.exists():
        return None
    
    lines = file_path.read_text(encoding="utf-8").splitlines()
    root = TreeNode("ROOT", level=-1)
    stack: List[TreeNode] = [root]
    
    for line in lines:
        stripped = line.rstrip()
        if not stripped:
            continue
        
        # 앞의 공백 개수 계산 (4개 공백 = 1 레벨)
        leading_spaces = len(line) - len(line.lstrip())
        level = leading_spaces // 4
        
        keyword = stripped.strip()
        node = TreeNode(keyword, level)
        
        # 적절한 부모 찾기
        while len(stack) > 1 and stack[-1].level >= level:
            stack.pop()
        
        parent = stack[-1]
        parent.add_child(node)
        stack.append(node)
    
    return root


def build_keyword_tree(file_path: Path) -> List[TreeNode]:
    """트리 파일을 파싱하여 루트의 자식 노드 리스트 반환"""
    root = parse_tree_file(file_path)
    if root is None:
        return []
    return root.children


def load_tagged_database(csv_path: Path) -> List[Dict[str, str]]:
    """tagged_database.csv 로드
    
    지원하는 컬럼명:
    - code/name: "코드", "code", "Code", "CODE", "name", "Name", "NAME"
    - title: "제목", "title", "Title", "TITLE"
    - link: "link", "url", "Link", "URL", "링크"
    - tag: "tag", "Tag", "TAG", "태그"
    """
    if not csv_path.exists():
        return []
    
    entries: List[Dict[str, str]] = []
    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # code/name 컬럼 찾기 (대소문자 무시, 한국어/영어 모두 지원)
            # 'Name' 컬럼이 우선, 없으면 'code' 컬럼 사용
            code = ""
            for key in row.keys():
                if key.lower() in ["name"]:
                    code = row[key].strip()
                    break
            if not code:
                for key in row.keys():
                    if key.lower() in ["코드", "code"]:
                        code = row[key].strip()
                        break
            
            # title 컬럼 찾기
            title = ""
            for key in row.keys():
                if key.lower() in ["제목", "title"]:
                    title = row[key].strip()
                    break
            
            # link 컬럼 찾기
            link = ""
            for key in row.keys():
                if key.lower() in ["link", "url", "링크"]:
                    link = row[key].strip()
                    break
            
            # tag 컬럼 찾기
            tag = ""
            for key in row.keys():
                if key.lower() in ["tag", "태그"]:
                    tag = row[key].strip()
                    break
            
            entries.append({
                "code": code,
                "title": title,
                "link": link,
                "tag": tag,
            })
    
    return entries


def load_pcs_database(csv_path: Path) -> List[Dict[str, str]]:
    """pcs_database.csv 로드 (title, link, tag만 포함)
    
    지원하는 컬럼명:
    - title: "제목", "title", "Title", "TITLE"
    - link: "link", "url", "Link", "URL", "링크"
    - tag: "tag", "Tag", "TAG", "태그"
    """
    if not csv_path.exists():
        return []
    
    entries: List[Dict[str, str]] = []
    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # title 컬럼 찾기
            title = ""
            for key in row.keys():
                if key.lower() in ["제목", "title"]:
                    title = row[key].strip()
                    break
            
            # link 컬럼 찾기
            link = ""
            for key in row.keys():
                if key.lower() in ["link", "url", "링크"]:
                    link = row[key].strip()
                    break
            
            # tag 컬럼 찾기
            tag = ""
            for key in row.keys():
                if key.lower() in ["tag", "태그"]:
                    tag = row[key].strip()
                    break
            
            entries.append({
                "title": title,
                "link": link,
                "tag": tag,
            })
    
    return entries


def get_procedures_by_tag(
    tagged_entries: List[Dict[str, str]],
    keyword_set: Set[str]
) -> List[Dict[str, str]]:
    """특정 키워드 세트에 매칭되는 프로시저 반환
    
    태그는 ';'로 구분된 여러 값을 가질 수 있습니다.
    하나라도 매칭되면 반환합니다.
    """
    results: List[Dict[str, str]] = []
    for entry in tagged_entries:
        tag_str = entry.get("tag", "").strip()
        if not tag_str:
            continue
        
        # ';'로 구분된 태그들을 파싱
        entry_tags = {t.strip() for t in tag_str.split(";") if t.strip()}
        
        # 하나라도 매칭되면 결과에 추가
        if entry_tags & keyword_set:  # 교집합이 있으면
            results.append(entry)
    return results


def search_procedures_by_title(
    tagged_entries: List[Dict[str, str]],
    query: str
) -> List[Dict[str, str]]:
    """제목에 키워드가 포함된 프로시저 검색"""
    if not query:
        return []
    
    query_lower = query.lower()
    results: List[Dict[str, str]] = []
    for entry in tagged_entries:
        title = entry.get("title", "").lower()
        if query_lower in title:
            results.append(entry)
    return results


def save_tagged_database(csv_path: Path, entries: List[Dict[str, str]]) -> None:
    """tagged_database.csv 저장
    
    기본적으로 한국어 컬럼명("코드", "제목")을 사용하지만,
    기존 파일이 있으면 해당 파일의 컬럼명을 유지합니다.
    'Name' 컬럼이 있으면 우선 사용, 없으면 'code' 컬럼 사용.
    """
    # 기존 파일이 있으면 컬럼명 확인
    fieldnames = ["코드", "제목", "link", "tag"]
    if csv_path.exists():
        with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames:
                # 기존 컬럼명 사용 (대소문자 유지)
                fieldnames = list(reader.fieldnames)
    
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for entry in entries:
            row = {}
            # 각 컬럼명에 맞게 매핑
            for fieldname in fieldnames:
                field_lower = fieldname.lower()
                if field_lower in ["name"]:
                    # 'Name' 컬럼이 있으면 우선 사용
                    row[fieldname] = entry.get("code", "")
                elif field_lower in ["코드", "code"]:
                    # 'Name' 컬럼이 없을 때만 'code' 컬럼 사용
                    if "name" not in [f.lower() for f in fieldnames]:
                        row[fieldname] = entry.get("code", "")
                elif field_lower in ["제목", "title"]:
                    row[fieldname] = entry.get("title", "")
                elif field_lower in ["link", "url", "링크"]:
                    row[fieldname] = entry.get("link", "")
                elif field_lower in ["tag", "태그"]:
                    row[fieldname] = entry.get("tag", "")
                else:
                    row[fieldname] = ""
            writer.writerow(row)


def tree_node_to_dict(node: TreeNode, tagged_entries: List[Dict[str, str]]) -> Dict:
    """트리 노드를 딕셔너리로 변환 (프로시저 포함)
    
    각 노드는 자신의 키워드에만 매칭되는 프로시저만 표시합니다.
    하위 노드의 키워드는 포함하지 않습니다.
    """
    # 해당 노드의 키워드만 사용 (하위 노드 제외)
    keyword_set = {node.keyword}
    procedures = get_procedures_by_tag(tagged_entries, keyword_set)
    
    return {
        "keyword": node.keyword,
        "level": node.level,
        "procedures": procedures,
        "children": [tree_node_to_dict(child, tagged_entries) for child in node.children]
    }


def build_networkx_graph(tree_nodes: List[TreeNode]) -> Optional[object]:
    """트리 노드들을 networkx DiGraph로 변환
    
    같은 키워드라도 다른 부모를 가지면 다른 노드로 처리합니다.
    노드 ID는 부모 경로를 포함한 고유 ID를 사용합니다.
    """
    if not HAS_NETWORKX:
        return None
    
    G = nx.DiGraph()
    
    def add_node_recursive(node: TreeNode, parent_path: str = ""):
        """재귀적으로 노드와 엣지 추가
        
        parent_path: 부모 노드들의 경로 (예: "root/parent")
        """
        # 부모 경로를 포함한 고유 노드 ID 생성
        if parent_path:
            node_id = f"{parent_path}/{node.keyword}"
        else:
            node_id = node.keyword
        
        # 노드 추가 (레벨 정보 및 원본 키워드 포함)
        G.add_node(node_id, level=node.level, keyword=node.keyword)
        
        # 부모-자식 관계 엣지 추가
        if parent_path:
            # 부모 노드 ID 찾기 (같은 키워드지만 다른 경로일 수 있음)
            parent_id = parent_path
            if parent_id not in G:
                # 부모 노드가 없으면 생성 (이전 레벨에서 생성되었을 수 있음)
                parent_keyword = parent_path.split("/")[-1]
                G.add_node(parent_id, level=node.level - 1, keyword=parent_keyword)
            G.add_edge(parent_id, node_id)
        
        # 자식 노드 재귀 처리
        for child in node.children:
            add_node_recursive(child, node_id)
    
    # 루트 노드들 처리
    for root_node in tree_nodes:
        add_node_recursive(root_node)
    
    return G


def graph_to_visjs_json(G: object) -> Optional[Dict]:
    """networkx 그래프를 vis.js 형식의 JSON으로 변환"""
    if not HAS_NETWORKX or G is None:
        return None
    
    nodes = []
    edges = []
    
    # 노드 데이터 생성
    for node_id in G.nodes():
        level = G.nodes[node_id].get("level", 0)
        keyword = G.nodes[node_id].get("keyword", node_id)
        
        # 노드 스타일: 흰색 배경, 검은색 테두리, 검은색 글자
        # label은 원본 키워드만 표시 (경로는 숨김)
        node_data = {
            "id": node_id,
            "label": keyword,
            "level": level,
            "color": {
                "background": "#ffffff",
                "border": "#000000",
                "highlight": {
                    "background": "#f3f4f6",
                    "border": "#000000"
                }
            },
            "font": {
                "color": "#000000",
                "size": 14
            },
            "shape": "box",
            "borderWidth": 2,
        }
        nodes.append(node_data)
    
    # 엣지 데이터 생성 (검은색)
    for source, target in G.edges():
        edges.append({
            "from": source,
            "to": target,
            "arrows": "to",
            "color": {
                "color": "#000000",
                "highlight": "#000000"
            },
            "smooth": {"type": "curvedCW", "roundness": 0.2},
        })
    
    return {
        "nodes": nodes,
        "edges": edges,
    }

