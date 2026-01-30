from typing import Dict, List, Tuple
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# 직접 실행과 모듈 실행 모두 지원
try:
    from .dataset_config import DatasetDefinition, VersionDefinition, load_dataset_definitions, load_app_config
    from .database import get_all_data, save_all_data
    from .models import DatasetState
    from .link_tree import (
        build_keyword_tree,
        load_tagged_database,
        save_tagged_database,
        get_procedures_by_tag,
        search_procedures_by_title,
        TreeNode,
        tree_node_to_dict,
        build_networkx_graph,
        graph_to_visjs_json,
    )
except ImportError:
    # 직접 실행 시 (python app/main.py)
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from dataset_config import DatasetDefinition, VersionDefinition, load_dataset_definitions, load_app_config
    from database import get_all_data, save_all_data
    from models import DatasetState
    from link_tree import (
        build_keyword_tree,
        load_tagged_database,
        save_tagged_database,
        get_procedures_by_tag,
        search_procedures_by_title,
        TreeNode,
        tree_node_to_dict,
        build_networkx_graph,
        graph_to_visjs_json,
    )

# 절대 경로로 static 폴더 설정
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

app = FastAPI(title="Links Manager")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

DATASET_DEFINITIONS: List[DatasetDefinition] = load_dataset_definitions()
DATASET_MAP: Dict[str, DatasetDefinition] = {dataset.id: dataset for dataset in DATASET_DEFINITIONS}
DEFAULT_DATASET_ID = DATASET_DEFINITIONS[0].id
APP_CONFIG = load_app_config()

# 메모리 내 데이터 저장소 (세트별)
_dataset_state: Dict[str, DatasetState] = {}


def _load_data() -> None:
    """각 세트의 CSV 데이터를 메모리에 로드"""
    for definition in DATASET_DEFINITIONS:
        bundles, memos_by_action, links = get_all_data(
            definition.main_csv, definition.memo_csv, definition.link_csv
        )
        _dataset_state[definition.id] = DatasetState(
            bundles=bundles,
            memos_by_action=memos_by_action,
            links=links,
            tagged_database=[],
        )


def _get_dataset(dataset_id: str | None) -> Tuple[str, DatasetDefinition, DatasetState]:
    """dataset 식별자를 검증하고 상태 반환"""
    resolved_id = dataset_id or DEFAULT_DATASET_ID
    if resolved_id not in DATASET_MAP:
        raise HTTPException(status_code=404, detail="Dataset not found")
    state = _dataset_state.get(resolved_id)
    if state is None:
        definition = DATASET_MAP[resolved_id]
        # Links 앱에서는 CSV 파일이 없을 수 있으므로 안전하게 처리
        # get_all_data는 파일이 없으면 빈 딕셔너리를 반환하므로 예외 처리 불필요
        bundles, memos_by_action, links = get_all_data(
            definition.main_csv, definition.memo_csv, definition.link_csv
        )
        
        state = DatasetState(
            bundles=bundles,
            memos_by_action=memos_by_action,
            links=links,
            tagged_database=[],
        )
        _dataset_state[resolved_id] = state
    return resolved_id, DATASET_MAP[resolved_id], state


def _layout_context(dataset_id: str, extra: dict) -> dict:
    context = dict(extra)
    context.update(
        {
            "datasets": DATASET_DEFINITIONS,
            "active_dataset_id": dataset_id,
            "active_dataset": DATASET_MAP.get(dataset_id),
            "app_title": APP_CONFIG.get("app_title", "CoSy Links Manager"),
        }
    )
    return context


@app.on_event("startup")
def on_startup() -> None:
    """앱 시작 시 CSV 파일 자동 로드"""
    _load_data()


@app.get("/", response_class=HTMLResponse)
def read_home(
    request: Request,
    dataset: str | None = None,
    version: str | None = None,
    search_query: str | None = None,
) -> HTMLResponse:
    """홈 페이지 - Links 탭"""
    dataset_id, definition, state = _get_dataset(dataset)
    
    # Links 탭용 데이터 로드
    link_tree_data = None
    other_keywords_data = None
    tagged_database = []
    active_version = None
    hardware_graph_data = None
    
    # 버전 선택 처리
    version_id = version or (definition.versions[0].id if definition.versions else None)
    if version_id:
        for ver in definition.versions:
            if ver.id == version_id:
                active_version = ver
                break
    
    # 버전이 있으면 해당 버전의 데이터 로드
    if active_version:
        # tagged_database 로드
        if active_version.tagged_database_csv:
            tagged_database = load_tagged_database(active_version.tagged_database_csv)
        
        # tree.txt 파싱 및 프로시저 매칭
        if active_version.tree_txt:
            tree_nodes = build_keyword_tree(active_version.tree_txt)
            link_tree_data = [tree_node_to_dict(node, tagged_database) for node in tree_nodes]
            
            # networkx 그래프 생성
            graph = build_networkx_graph(tree_nodes)
            if graph:
                hardware_graph_data = graph_to_visjs_json(graph)
        
        # other_keywords.txt 파싱 및 프로시저 매칭
        if active_version.other_keywords_txt:
            other_nodes = build_keyword_tree(active_version.other_keywords_txt)
            other_keywords_data = [tree_node_to_dict(node, tagged_database) for node in other_nodes]
    
    return templates.TemplateResponse(
        "home.html",
        _layout_context(
            dataset_id,
            {
                "request": request,
                "link_tree_data": link_tree_data,
                "other_keywords_data": other_keywords_data,
                "tagged_database": tagged_database,
                "search_query": search_query or "",
                "active_version": active_version,
                "version": version,
                "hardware_graph_data": hardware_graph_data,
            },
        ),
    )


@app.get("/links/manage", response_class=HTMLResponse)
def manage_links_page(request: Request, dataset: str | None = None, version: str | None = None) -> HTMLResponse:
    """프로시저 관리 페이지"""
    dataset_id, definition, state = _get_dataset(dataset)
    
    # 버전 선택 처리
    version_id = version or (definition.versions[0].id if definition.versions else None)
    active_version = None
    if version_id:
        for ver in definition.versions:
            if ver.id == version_id:
                active_version = ver
                break
    
    # 모든 키워드 수집 (tree.txt + other_keywords.txt)
    all_keywords = set()
    tagged_database = []
    
    if active_version:
        if active_version.tree_txt:
            tree_nodes = build_keyword_tree(active_version.tree_txt)
            for node in tree_nodes:
                all_keywords.update(node.get_all_keywords())
        if active_version.other_keywords_txt:
            other_nodes = build_keyword_tree(active_version.other_keywords_txt)
            for node in other_nodes:
                all_keywords.update(node.get_all_keywords())
        if active_version.tagged_database_csv:
            tagged_database = load_tagged_database(active_version.tagged_database_csv)
    
    return templates.TemplateResponse(
        "manage_links.html",
        _layout_context(
            dataset_id,
            {
                "request": request,
                "tagged_database": tagged_database,
                "all_keywords": sorted(all_keywords),
                "active_version": active_version,
                "version": version,
            },
        ),
    )


@app.post("/links/update-procedure")
async def update_procedure(request: Request) -> RedirectResponse:
    """프로시저 태그 업데이트 (여러 태그는 ';'로 구분)"""
    form = await request.form()
    dataset_id, definition, state = _get_dataset(form.get("dataset"))
    version_id = form.get("version", "")
    code = form.get("code", "").strip()
    new_tag = form.get("tag", "").strip()
    
    # 버전 찾기
    active_version = None
    if version_id:
        for ver in definition.versions:
            if ver.id == version_id:
                active_version = ver
                break
    
    if active_version and active_version.tagged_database_csv:
        # tagged_database 로드
        tagged_database = load_tagged_database(active_version.tagged_database_csv)
        
        # 프로시저 찾아서 태그 업데이트
        for entry in tagged_database:
            if entry.get("code") == code:
                # 태그 정규화: 공백 제거 및 ';'로 구분
                tags = [t.strip() for t in new_tag.split(";") if t.strip()]
                entry["tag"] = ";".join(tags) if tags else ""
                break
        
        # 저장
        save_tagged_database(active_version.tagged_database_csv, tagged_database)
    
    return_url = f"/?dataset={dataset_id}"
    if version_id:
        return_url += f"&version={version_id}"
    return RedirectResponse(url=return_url, status_code=303)


@app.post("/links/add-procedure")
async def add_procedure(request: Request) -> RedirectResponse:
    """새 프로시저 추가"""
    form = await request.form()
    dataset_id, definition, state = _get_dataset(form.get("dataset"))
    version_id = form.get("version", "")
    
    code = form.get("code", "").strip()
    title = form.get("title", "").strip()
    link = form.get("link", "").strip()
    tag = form.get("tag", "").strip()
    
    # 버전 찾기
    active_version = None
    if version_id:
        for ver in definition.versions:
            if ver.id == version_id:
                active_version = ver
                break
    
    if code and title and link and active_version and active_version.tagged_database_csv:
        # tagged_database 로드
        tagged_database = load_tagged_database(active_version.tagged_database_csv)
        
        # 중복 체크
        existing_codes = {e.get("code") for e in tagged_database}
        if code not in existing_codes:
            # 태그 정규화: 공백 제거 및 ';'로 구분
            tags = [t.strip() for t in tag.split(";") if t.strip()] if tag else ["REST"]
            normalized_tag = ";".join(tags)
            
            tagged_database.append({
                "code": code,
                "title": title,
                "link": link,
                "tag": normalized_tag,
            })
            
            # 저장
            save_tagged_database(active_version.tagged_database_csv, tagged_database)
    
    return_url = f"/?dataset={dataset_id}"
    if version_id:
        return_url += f"&version={version_id}"
    return RedirectResponse(url=return_url, status_code=303)


@app.get("/export/links")
def export_links(dataset: str | None = None) -> StreamingResponse:
    """링크 CSV 내보내기"""
    import io
    import csv

    dataset_id, _, state = _get_dataset(dataset)
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["ID", "URL", "Description", "Tags"])
    writer.writeheader()

    for link_id in sorted(state.links.keys()):
        link = state.links[link_id]
        writer.writerow(
            {
                "ID": link.id or "",
                "URL": link.url,
                "Description": link.description,
                "Tags": link.tags,
            }
        )

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{dataset_id}_links.csv"'},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", reload=True)
