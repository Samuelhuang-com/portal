"""
knowledge_graph_generator.py
────────────────────────────
Portal 專案知識圖譜產生器

功能：
  1. 掃描 backend/ 所有 .py 檔 → 提取 module / class / function + import 關係
  2. 掃描 frontend/src/ 所有 .ts / .tsx 檔 → 提取 component / hook / 函式 + import 關係
  3. 以 networkx 建構有向圖（依賴邊）
  4. 輸出自含式 HTML（vis.js Network，不需 CDN）

呼叫方式：
  python knowledge_graph_generator.py <project_root> <output_dir>
"""

import ast
import json
import math
import os
import re
import sys
from pathlib import Path


# ── 顏色 / 節點群組設定 ──────────────────────────────────────────────────────
GROUP_CONFIG = {
    "py_module":    {"color": "#4BA8E8", "shape": "box",       "size": 22},
    "py_class":     {"color": "#1B3A5C", "shape": "ellipse",   "size": 18},
    "py_function":  {"color": "#6BB5E8", "shape": "dot",       "size": 12},
    "ts_component": {"color": "#764ba2", "shape": "ellipse",   "size": 18},
    "ts_hook":      {"color": "#a855f7", "shape": "diamond",   "size": 14},
    "ts_module":    {"color": "#667eea", "shape": "box",       "size": 20},
    "ts_function":  {"color": "#9d7fe8", "shape": "dot",       "size": 12},
    "router":       {"color": "#e74c3c", "shape": "star",      "size": 22},
    "api_endpoint": {"color": "#e67e22", "shape": "triangle",  "size": 14},
    "db_model":     {"color": "#27ae60", "shape": "database",  "size": 18},
    "schema":       {"color": "#2ecc71", "shape": "box",       "size": 14},
    "service":      {"color": "#f39c12", "shape": "hexagon",   "size": 18},
}

EDGE_COLORS = {
    "imports":    "#94a3b8",
    "defines":    "#1B3A5C",
    "uses":       "#4BA8E8",
    "api_route":  "#e74c3c",
    "inherits":   "#27ae60",
}


# ── Python 分析 ───────────────────────────────────────────────────────────────

def _module_key(filepath: Path, root: Path) -> str:
    rel = filepath.relative_to(root)
    parts = list(rel.with_suffix("").parts)
    return ".".join(parts).replace("\\", ".")


def _classify_py_module(filepath: Path) -> str:
    name = filepath.stem
    parent = filepath.parent.name
    if parent == "routers":
        return "router"
    if parent == "models":
        return "db_model"
    if parent == "schemas":
        return "schema"
    if parent == "services":
        return "service"
    if name == "main":
        return "py_module"
    return "py_module"


def analyze_python_file(filepath: Path, root: Path) -> dict:
    """
    回傳 { module_key, nodes: [...], edges: [...] }
    """
    mod_key = _module_key(filepath, root)
    nodes = []
    edges = []

    # Module 節點
    mod_type = _classify_py_module(filepath)
    nodes.append({
        "id": mod_key,
        "label": filepath.stem,
        "title": str(filepath.relative_to(root)),
        "group": mod_type,
    })

    try:
        src = filepath.read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(src)
    except Exception:
        return {"module_key": mod_key, "nodes": nodes, "edges": edges}

    # Imports → edges
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                edges.append({
                    "from": mod_key,
                    "to": alias.name.replace("-", "_"),
                    "label": "imports",
                    "type": "imports",
                    "dashes": True,
                })
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                target = node.module
                # 相對 import → 轉換成絕對 key
                if node.level and node.level > 0:
                    parts = mod_key.split(".")
                    base = parts[: max(0, len(parts) - node.level)]
                    target = ".".join(base + [target]) if target else ".".join(base)
                edges.append({
                    "from": mod_key,
                    "to": target,
                    "label": "imports",
                    "type": "imports",
                    "dashes": True,
                })

    # Top-level class / function 定義
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef):
            cls_id = f"{mod_key}.{node.name}"
            # 分類：Model / Schema / Router class
            if "Base" in [b.id if isinstance(b, ast.Name) else "" for b in node.bases]:
                group = "db_model"
            elif "BaseModel" in [b.id if isinstance(b, ast.Name) else "" for b in node.bases]:
                group = "schema"
            else:
                group = "py_class"

            nodes.append({
                "id": cls_id,
                "label": node.name,
                "title": f"class {node.name} in {filepath.stem}",
                "group": group,
            })
            edges.append({
                "from": mod_key, "to": cls_id,
                "label": "defines", "type": "defines",
            })
            # Methods（只取 public）
            for item in ast.iter_child_nodes(node):
                if isinstance(item, ast.FunctionDef) and not item.name.startswith("_"):
                    fn_id = f"{cls_id}.{item.name}"
                    nodes.append({
                        "id": fn_id,
                        "label": item.name,
                        "title": f"method {item.name} in {node.name}",
                        "group": "py_function",
                    })
                    edges.append({
                        "from": cls_id, "to": fn_id,
                        "label": "defines", "type": "defines",
                    })

        elif isinstance(node, ast.FunctionDef):
            if not node.name.startswith("_"):
                fn_id = f"{mod_key}.{node.name}"
                # 偵測 FastAPI router 裝飾器
                is_route = any(
                    (isinstance(d, ast.Attribute) and d.attr in ("get","post","put","delete","patch"))
                    or (isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute)
                        and d.func.attr in ("get","post","put","delete","patch"))
                    for d in node.decorator_list
                )
                group = "api_endpoint" if is_route else "py_function"
                nodes.append({
                    "id": fn_id,
                    "label": node.name,
                    "title": f"{'@route' if is_route else 'def'} {node.name} in {filepath.stem}",
                    "group": group,
                })
                edges.append({
                    "from": mod_key, "to": fn_id,
                    "label": "defines", "type": "defines",
                })

    return {"module_key": mod_key, "nodes": nodes, "edges": edges}


# ── TypeScript / TSX 分析 ─────────────────────────────────────────────────────

_RE_TS_IMPORT  = re.compile(r"""^import\s+.*?\s+from\s+['"]([^'"]+)['"]""", re.MULTILINE)
_RE_TS_EXPORT_FN = re.compile(r"""^export\s+(?:default\s+)?(?:async\s+)?function\s+(\w+)""", re.MULTILINE)
_RE_TS_CONST_FN  = re.compile(r"""^export\s+(?:default\s+)?const\s+(\w+)\s*[:=]""", re.MULTILINE)
_RE_TS_INTERFACE = re.compile(r"""^(?:export\s+)?interface\s+(\w+)""", re.MULTILINE)
_RE_TS_TYPE      = re.compile(r"""^export\s+type\s+(\w+)""", re.MULTILINE)
_RE_TS_CLASS     = re.compile(r"""^export\s+(?:default\s+)?class\s+(\w+)""", re.MULTILINE)


def _ts_module_key(filepath: Path, root: Path) -> str:
    rel = filepath.relative_to(root)
    parts = list(rel.with_suffix("").parts)
    return "ts:" + "/".join(parts)


def _classify_ts_symbol(name: str, filepath: Path) -> str:
    if name.startswith("use") and name[3:4].isupper():
        return "ts_hook"
    if name[0:1].isupper():
        return "ts_component"
    return "ts_function"


def _classify_ts_module(filepath: Path) -> str:
    parts = filepath.parts
    if "pages" in parts:
        return "ts_component"
    if "api" in parts:
        return "ts_module"
    if "router" in parts:
        return "ts_module"
    if "stores" in parts:
        return "ts_module"
    return "ts_module"


def analyze_ts_file(filepath: Path, root: Path) -> dict:
    mod_key = _ts_module_key(filepath, root)
    nodes = []
    edges = []

    mod_type = _classify_ts_module(filepath)
    label = filepath.stem if filepath.stem != "index" else filepath.parent.name
    nodes.append({
        "id": mod_key,
        "label": label,
        "title": str(filepath.relative_to(root)),
        "group": mod_type,
    })

    try:
        src = filepath.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return {"module_key": mod_key, "nodes": nodes, "edges": edges}

    # Imports → edges（只保留相對 import，即 '@/' 或 './' 或 '../'）
    for m in _RE_TS_IMPORT.finditer(src):
        imp = m.group(1)
        if imp.startswith("@/"):
            target = "ts:" + imp[2:]  # @/ → src/
        elif imp.startswith("./") or imp.startswith("../"):
            # 解析相對路徑
            base = filepath.parent
            resolved = (base / imp).resolve()
            try:
                rel = resolved.relative_to(root)
                target = "ts:" + "/".join(rel.parts)
            except ValueError:
                continue
        else:
            continue  # 忽略 node_modules 等外部套件

        edges.append({
            "from": mod_key, "to": target,
            "label": "imports", "type": "imports", "dashes": True,
        })

    # 匯出的函式 / 元件
    for pattern in [_RE_TS_EXPORT_FN, _RE_TS_CONST_FN]:
        for m in pattern.finditer(src):
            name = m.group(1)
            if name in ("default",):
                continue
            sym_id = f"{mod_key}#{name}"
            group = _classify_ts_symbol(name, filepath)
            nodes.append({
                "id": sym_id,
                "label": name,
                "title": f"{group} {name} in {filepath.name}",
                "group": group,
            })
            edges.append({
                "from": mod_key, "to": sym_id,
                "label": "defines", "type": "defines",
            })

    return {"module_key": mod_key, "nodes": nodes, "edges": edges}


# ── 圖譜建構 ──────────────────────────────────────────────────────────────────

def build_graph(project_root: Path) -> tuple[list, list]:
    """
    掃描整個 project_root，回傳 (nodes, edges)。
    """
    all_nodes: list[dict] = []
    all_edges: list[dict] = []
    known_ids: set[str] = set()

    def add_result(result: dict):
        for n in result["nodes"]:
            if n["id"] not in known_ids:
                known_ids.add(n["id"])
                all_nodes.append(n)
        all_edges.extend(result["edges"])

    backend_root = project_root / "backend"
    frontend_root = project_root / "frontend" / "src"

    # Python
    if backend_root.exists():
        for py_file in sorted(backend_root.rglob("*.py")):
            if any(p in py_file.parts for p in ["__pycache__", ".venv", "venv", "migrations"]):
                continue
            add_result(analyze_python_file(py_file, backend_root))

    # TypeScript / TSX
    if frontend_root.exists():
        for ts_file in sorted(frontend_root.rglob("*.ts")) + sorted(frontend_root.rglob("*.tsx")):
            if "node_modules" in ts_file.parts:
                continue
            add_result(analyze_ts_file(ts_file, frontend_root))

    # 去除指向不存在節點的邊（孤立 import）
    valid_ids = {n["id"] for n in all_nodes}
    filtered_edges = [
        e for e in all_edges
        if e["from"] in valid_ids and e["to"] in valid_ids
    ]

    return all_nodes, filtered_edges


# ── HTML 產生 ─────────────────────────────────────────────────────────────────

_VIS_JS_CDN = "https://unpkg.com/vis-network@9.1.9/dist/vis-network.min.js"
_VIS_CSS_CDN = "https://unpkg.com/vis-network@9.1.9/dist/vis-network.min.css"

_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Portal 專案知識圖譜</title>
<link rel="stylesheet" href="{vis_css}">
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
       background: #0f172a; color: #e2e8f0; height: 100vh; overflow: hidden; }}
#header {{ padding: 12px 20px; background: #1e293b; border-bottom: 1px solid #334155;
           display: flex; align-items: center; gap: 16px; }}
#header h1 {{ font-size: 15px; font-weight: 600; color: #93c5fd; }}
#stats {{ font-size: 12px; color: #64748b; }}
#controls {{ margin-left: auto; display: flex; gap: 8px; align-items: center; }}
#controls label {{ font-size: 12px; color: #94a3b8; }}
#controls select, #controls input {{ background: #0f172a; color: #e2e8f0;
  border: 1px solid #334155; border-radius: 4px; padding: 3px 6px; font-size: 12px; }}
#mynetwork {{ width: 100%; height: calc(100vh - 48px); }}
#legend {{ position: fixed; bottom: 16px; left: 16px; background: rgba(30,41,59,.92);
           border: 1px solid #334155; border-radius: 8px; padding: 12px 16px;
           font-size: 11px; max-width: 180px; }}
#legend h3 {{ font-size: 11px; color: #93c5fd; margin-bottom: 8px; font-weight: 600; }}
.legend-item {{ display: flex; align-items: center; gap: 6px; margin-bottom: 4px; }}
.legend-dot {{ width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }}
#tooltip {{ position: fixed; background: #1e293b; border: 1px solid #334155;
            border-radius: 6px; padding: 8px 12px; font-size: 11px; pointer-events: none;
            display: none; z-index: 999; max-width: 260px; line-height: 1.5; }}
</style>
</head>
<body>
<div id="header">
  <h1>🔭 Portal 專案知識圖譜</h1>
  <span id="stats"></span>
  <div id="controls">
    <label>群組篩選：</label>
    <select id="groupFilter" onchange="filterGroup(this.value)">
      <option value="all">全部</option>
      <option value="backend">後端 Python</option>
      <option value="frontend">前端 TypeScript</option>
      <option value="router">Router / API</option>
      <option value="db">DB Models</option>
    </select>
    <label>搜尋：</label>
    <input id="searchBox" type="text" placeholder="節點名稱…" oninput="searchNode(this.value)" style="width:120px">
  </div>
</div>
<div id="mynetwork"></div>
<div id="tooltip"></div>
<div id="legend">
  <h3>圖例</h3>
  <div class="legend-item"><div class="legend-dot" style="background:#e74c3c"></div><span>Router</span></div>
  <div class="legend-item"><div class="legend-dot" style="background:#e67e22"></div><span>API Endpoint</span></div>
  <div class="legend-item"><div class="legend-dot" style="background:#27ae60"></div><span>DB Model</span></div>
  <div class="legend-item"><div class="legend-dot" style="background:#2ecc71"></div><span>Schema</span></div>
  <div class="legend-item"><div class="legend-dot" style="background:#f39c12"></div><span>Service</span></div>
  <div class="legend-item"><div class="legend-dot" style="background:#4BA8E8"></div><span>Py Module</span></div>
  <div class="legend-item"><div class="legend-dot" style="background:#764ba2"></div><span>TS Component</span></div>
  <div class="legend-item"><div class="legend-dot" style="background:#a855f7"></div><span>React Hook</span></div>
  <div class="legend-item"><div class="legend-dot" style="background:#667eea"></div><span>TS Module</span></div>
</div>

<script src="{vis_js}"></script>
<script>
const RAW_NODES = {nodes_json};
const RAW_EDGES = {edges_json};
const GROUP_CFG = {group_cfg_json};

const BACKEND_GROUPS = new Set(['py_module','py_class','py_function','router','api_endpoint','db_model','schema','service']);
const FRONTEND_GROUPS = new Set(['ts_component','ts_hook','ts_module','ts_function']);

function groupColor(g) {{
  return (GROUP_CFG[g] || {{}}).color || '#94a3b8';
}}
function groupShape(g) {{
  return (GROUP_CFG[g] || {{}}).shape || 'dot';
}}
function groupSize(g) {{
  return (GROUP_CFG[g] || {{}}).size || 12;
}}

function buildDatasets(nodeSubset) {{
  const nodeIds = new Set(nodeSubset.map(n => n.id));
  const visNodes = nodeSubset.map(n => ({{
    id: n.id,
    label: n.label,
    title: n.title || n.id,
    color: groupColor(n.group),
    shape: groupShape(n.group),
    size: groupSize(n.group),
    font: {{ color: '#e2e8f0', size: n.group.includes('module') || n.group === 'router' ? 12 : 10 }},
    borderWidth: 1.5,
    borderWidthSelected: 3,
  }}));

  const edgeColors = {{ imports:'#334155', defines:'#475569', uses:'#4BA8E8', api_route:'#e74c3c', inherits:'#27ae60' }};
  const visEdges = RAW_EDGES
    .filter(e => nodeIds.has(e.from) && nodeIds.has(e.to))
    .map((e,i) => ({{
      id: i,
      from: e.from, to: e.to,
      label: '',
      color: {{ color: edgeColors[e.type] || '#334155', opacity: 0.6 }},
      dashes: !!e.dashes,
      arrows: {{ to: {{ enabled: true, scaleFactor: 0.5 }} }},
      width: e.type === 'defines' ? 1 : 0.8,
    }}));

  return {{ visNodes, visEdges }};
}}

let network, nodesDS, edgesDS;

function initNetwork(nodeSubset) {{
  const {{ visNodes, visEdges }} = buildDatasets(nodeSubset);
  nodesDS = new vis.DataSet(visNodes);
  edgesDS = new vis.DataSet(visEdges);

  const container = document.getElementById('mynetwork');
  network = new vis.Network(container, {{ nodes: nodesDS, edges: edgesDS }}, {{
    physics: {{
      enabled: true,
      solver: 'forceAtlas2Based',
      forceAtlas2Based: {{ gravitationalConstant: -60, centralGravity: 0.005, springLength: 120, damping: 0.5 }},
      stabilization: {{ iterations: 150 }},
    }},
    layout: {{ improvedLayout: false }},
    interaction: {{ hover: true, tooltipDelay: 100, navigationButtons: true, keyboard: true }},
    edges: {{ smooth: {{ type: 'dynamic', roundness: 0.3 }} }},
  }});

  document.getElementById('stats').textContent =
    `節點：${{visNodes.length}}  邊：${{visEdges.length}}`;
}}

function filterGroup(val) {{
  let subset = RAW_NODES;
  if (val === 'backend')  subset = RAW_NODES.filter(n => BACKEND_GROUPS.has(n.group));
  if (val === 'frontend') subset = RAW_NODES.filter(n => FRONTEND_GROUPS.has(n.group));
  if (val === 'router')   subset = RAW_NODES.filter(n => n.group === 'router' || n.group === 'api_endpoint');
  if (val === 'db')       subset = RAW_NODES.filter(n => n.group === 'db_model' || n.group === 'schema');
  nodesDS.clear(); edgesDS.clear();
  const {{ visNodes, visEdges }} = buildDatasets(subset);
  nodesDS.add(visNodes); edgesDS.add(visEdges);
  document.getElementById('stats').textContent = `節點：${{visNodes.length}}  邊：${{visEdges.length}}`;
}}

function searchNode(q) {{
  if (!q || !network) return;
  const matched = RAW_NODES.filter(n => n.label.toLowerCase().includes(q.toLowerCase())).map(n => n.id);
  if (matched.length) network.selectNodes(matched, true);
}}

initNetwork(RAW_NODES);
</script>
</body>
</html>
"""


def generate_html(nodes: list, edges: list, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    group_cfg_json = json.dumps(GROUP_CONFIG, ensure_ascii=False)
    nodes_json = json.dumps(nodes, ensure_ascii=False)
    edges_json = json.dumps(edges, ensure_ascii=False)

    html = _HTML_TEMPLATE.format(
        vis_js=_VIS_JS_CDN,
        vis_css=_VIS_CSS_CDN,
        nodes_json=nodes_json,
        edges_json=edges_json,
        group_cfg_json=group_cfg_json,
    )
    output_path.write_text(html, encoding="utf-8")


def generate_json(nodes: list, edges: list, output_path: Path) -> None:
    output_path.write_text(
        json.dumps({"nodes": nodes, "edges": edges}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


# ── CLI 入口 ──────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 3:
        print(f"Usage: python {sys.argv[0]} <project_root> <output_dir>", file=sys.stderr)
        sys.exit(1)

    project_root = Path(sys.argv[1]).resolve()
    output_dir = Path(sys.argv[2]).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"[graphify] Scanning {project_root} …", flush=True)
    nodes, edges = build_graph(project_root)
    print(f"[graphify] Found {len(nodes)} nodes, {len(edges)} edges", flush=True)

    html_path = output_dir / "graph.html"
    json_path = output_dir / "graph.json"

    generate_html(nodes, edges, html_path)
    generate_json(nodes, edges, json_path)

    print(f"[graphify] Output → {html_path}", flush=True)


if __name__ == "__main__":
    main()
