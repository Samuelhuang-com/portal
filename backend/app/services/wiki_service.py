"""
知識庫（Wiki）業務邏輯服務
- CRUD 操作
- 全文關鍵字搜尋（SQLite LIKE，不依賴外部搜尋引擎）
- AI 問答（Anthropic Claude API，需設定 ANTHROPIC_API_KEY）
"""
from __future__ import annotations
import json
import re
import uuid
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Tuple, Dict, Any

from sqlalchemy.orm import Session

from app.models.wiki import WikiArticle, _slugify
from app.models.user import User
from app.schemas.wiki import (
    WikiArticleCreate,
    WikiArticleOut,
    WikiArticleUpdate,
    WikiListResponse,
)


# ─────────────────────────────────────────────────────────────────────────────
# 內部工具
# ─────────────────────────────────────────────────────────────────────────────

def _to_out(article: WikiArticle) -> WikiArticleOut:
    return WikiArticleOut.model_validate(article)


def _unique_slug(db: Session, base_slug: str, exclude_id: str = "") -> str:
    """確保 slug 唯一，若衝突則附加 -2, -3 ..."""
    slug = base_slug
    counter = 2
    while True:
        q = db.query(WikiArticle).filter(WikiArticle.slug == slug)
        if exclude_id:
            q = q.filter(WikiArticle.id != exclude_id)
        if not q.first():
            return slug
        slug = f"{base_slug}-{counter}"
        counter += 1


# ─────────────────────────────────────────────────────────────────────────────
# CRUD
# ─────────────────────────────────────────────────────────────────────────────

def list_articles(
    db: Session,
    *,
    q: str = "",
    category: str = "all",
    tags: List[str] | None = None,
    page: int = 1,
    per_page: int = 20,
    published_only: bool = True,
) -> WikiListResponse:
    query = db.query(WikiArticle)

    if published_only:
        query = query.filter(WikiArticle.is_published == True)

    if category and category != "all":
        query = query.filter(WikiArticle.category == category)

    if q:
        kw = f"%{q}%"
        query = query.filter(
            WikiArticle.title.ilike(kw)
            | WikiArticle.body.ilike(kw)
            | WikiArticle.summary.ilike(kw)
            | WikiArticle.tags.ilike(kw)
        )

    if tags:
        for tag in tags:
            query = query.filter(WikiArticle.tags.ilike(f"%{tag}%"))

    total = query.count()
    items = (
        query.order_by(WikiArticle.updated_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    return WikiListResponse(
        items=[_to_out(a) for a in items],
        total=total,
        page=page,
        per_page=per_page,
    )


def get_article(db: Session, article_id: str) -> Optional[WikiArticle]:
    return db.query(WikiArticle).filter(WikiArticle.id == article_id).first()


def get_article_by_slug(db: Session, slug: str) -> Optional[WikiArticle]:
    return db.query(WikiArticle).filter(WikiArticle.slug == slug).first()


def create_article(
    db: Session, payload: WikiArticleCreate, user: User
) -> WikiArticle:
    base_slug = payload.slug or _slugify(payload.title)
    slug = _unique_slug(db, base_slug)

    article = WikiArticle(
        title=payload.title,
        slug=slug,
        body=payload.body,
        summary=payload.summary or _auto_summary(payload.body),
        category=payload.category,
        tags=json.dumps(payload.tags, ensure_ascii=False),
        author=getattr(user, "full_name", "") or user.username,
        author_id=str(user.id),
        is_published=payload.is_published,
    )
    db.add(article)
    db.commit()
    db.refresh(article)
    return article


def update_article(
    db: Session, article_id: str, payload: WikiArticleUpdate, user: User
) -> Tuple[bool, str]:
    article = get_article(db, article_id)
    if not article:
        return False, "not_found"

    if payload.title is not None:
        article.title = payload.title
        if not payload.slug:
            new_slug = _unique_slug(db, _slugify(payload.title), exclude_id=article_id)
            article.slug = new_slug

    if payload.slug is not None:
        article.slug = _unique_slug(db, payload.slug, exclude_id=article_id)

    if payload.body is not None:
        article.body = payload.body
        if not payload.summary:
            article.summary = _auto_summary(payload.body)

    if payload.summary is not None:
        article.summary = payload.summary

    if payload.category is not None:
        article.category = payload.category

    if payload.tags is not None:
        article.tags = json.dumps(payload.tags, ensure_ascii=False)

    if payload.is_published is not None:
        article.is_published = payload.is_published

    db.commit()
    db.refresh(article)
    return True, ""


def delete_article(db: Session, article_id: str) -> bool:
    article = get_article(db, article_id)
    if not article:
        return False
    db.delete(article)
    db.commit()
    return True


# ─────────────────────────────────────────────────────────────────────────────
# 工具函式
# ─────────────────────────────────────────────────────────────────────────────

def _auto_summary(body: str, max_len: int = 150) -> str:
    """從 Markdown body 擷取前段純文字作為摘要"""
    # 移除 Markdown 語法
    text = re.sub(r"#{1,6}\s+", "", body)
    text = re.sub(r"\*{1,2}([^*]+)\*{1,2}", r"\1", text)
    text = re.sub(r"`[^`]+`", "", text)
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
    text = re.sub(r"^\s*[-*>|]+\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_len] + ("…" if len(text) > max_len else "")


# ─────────────────────────────────────────────────────────────────────────────
# AI 問答
# ─────────────────────────────────────────────────────────────────────────────

def _find_relevant_articles(
    db: Session, question: str, category: str, top_k: int = 5
) -> List[WikiArticle]:
    """關鍵字比對找出最相關文章（不依賴向量搜尋，SQLite 即可）"""
    # 拆出問題中的關鍵詞（以 2 字以上為準）
    keywords = [w for w in re.split(r"[\s,，。？！？!?、]+", question) if len(w) >= 2]

    q = db.query(WikiArticle).filter(WikiArticle.is_published == True)
    if category and category != "all":
        q = q.filter(WikiArticle.category == category)

    all_articles = q.all()

    if not all_articles:
        return []

    if not keywords:
        return all_articles[:top_k]

    # 依關鍵詞匹配數量排序
    def score(article: WikiArticle) -> int:
        text = (article.title + " " + article.body + " " + article.tags).lower()
        return sum(1 for kw in keywords if kw.lower() in text)

    scored = sorted(all_articles, key=score, reverse=True)
    # 至少回傳 1 篇（即使分數 0）
    return scored[:top_k]


def ask_ai(
    db: Session,
    question: str,
    category: str = "all",
) -> dict:
    """
    呼叫 Anthropic Claude API 回答問題。
    若未設定 ANTHROPIC_API_KEY，回傳提示訊息。
    """
    from app.core.config import settings

    sources = _find_relevant_articles(db, question, category)

    # ── 無 API key → 退化為純搜尋摘要模式 ────────────────────────────────────
    api_key = getattr(settings, "ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        if sources:
            bullets = "\n".join(
                f"• **{a.title}**：{a.summary or _auto_summary(a.body)}" for a in sources
            )
            answer = (
                f"⚠️ AI 問答功能需設定 `ANTHROPIC_API_KEY`（見 `.env`）。\n\n"
                f"以下是知識庫中與「{question}」相關的文章：\n\n{bullets}"
            )
        else:
            answer = (
                f"⚠️ AI 問答功能需設定 `ANTHROPIC_API_KEY`（見 `.env`）。\n\n"
                f"知識庫中暫無與此問題相關的文章，請先新增 SOP 或 Wiki 文章。"
            )
        return {
            "answer": answer,
            "sources": [_to_out(a) for a in sources],
            "model_used": None,
        }

    # ── 有 API key → 呼叫 Claude ──────────────────────────────────────────────
    try:
        import anthropic as _anthropic

        context_parts = []
        for a in sources:
            context_parts.append(
                f"## {a.title}\n**分類**：{a.category}\n\n{a.body[:1500]}"
            )
        context = "\n\n---\n\n".join(context_parts)

        system_prompt = (
            "你是「維春集團 Portal」的知識庫助手。"
            "根據以下提供的知識庫文章內容，用繁體中文回答使用者的問題。"
            "請直接根據文章內容回答，若知識庫中沒有相關資訊，請明確說明。"
            "回答要簡潔清楚，適當使用條列式格式。"
        )

        user_message = (
            f"【知識庫內容】\n\n{context}\n\n"
            f"【使用者問題】\n{question}"
        ) if context else question

        client = _anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        answer = response.content[0].text
        model_used = response.model

    except ImportError:
        answer = (
            "❌ 缺少 `anthropic` 套件。請在後端執行：\n"
            "```\npip install anthropic\n```\n然後重啟後端伺服器。"
        )
        model_used = None
    except Exception as e:
        answer = f"❌ AI 問答發生錯誤：{str(e)}"
        model_used = None

    return {
        "answer": answer,
        "sources": [_to_out(a) for a in sources],
        "model_used": model_used,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 知識庫圖譜
# ─────────────────────────────────────────────────────────────────────────────

def build_graph(db: Session, category: str = "all") -> Dict[str, Any]:
    """
    建立知識庫圖譜資料（nodes + edges）。
    邊的來源：
      1. 標籤重疊（type: "tag"）— 兩篇文章共用 ≥1 個標籤
      2. body 內 [[文章標題]] 引用（type: "link"）
    """
    query = db.query(WikiArticle).filter(WikiArticle.is_published == True)
    if category and category != "all":
        query = query.filter(WikiArticle.category == category)

    articles = query.all()

    # ── nodes ──────────────────────────────────────────────────────────────
    nodes = []
    title_to_id: Dict[str, str] = {}
    article_tags_map: Dict[str, List[str]] = {}

    for article in articles:
        tags = json.loads(article.tags) if isinstance(article.tags, str) else (article.tags or [])
        nodes.append({
            "id":       article.id,
            "title":    article.title,
            "slug":     article.slug,
            "category": article.category,
            "tags":     tags,
            "summary":  article.summary or "",
        })
        title_to_id[article.title] = article.id
        article_tags_map[article.id] = tags

    # ── edges ──────────────────────────────────────────────────────────────
    edges: List[Dict[str, Any]] = []
    seen_edges: set = set()

    def _add_edge(source: str, target: str, edge_type: str, **kwargs):
        key = (min(source, target), max(source, target), edge_type)
        if key not in seen_edges and source != target:
            seen_edges.add(key)
            edges.append({"source": source, "target": target, "type": edge_type, **kwargs})

    # 1. 標籤重疊
    for i, a in enumerate(articles):
        tags_a = set(article_tags_map.get(a.id, []))
        for b in articles[i + 1:]:
            tags_b = set(article_tags_map.get(b.id, []))
            shared = sorted(tags_a & tags_b)
            if shared:
                _add_edge(a.id, b.id, "tag", shared_tags=shared)

    # 2. [[連結]] 解析
    link_pattern = re.compile(r'\[\[([^\]]+)\]\]')
    for article in articles:
        for match in link_pattern.findall(article.body or ""):
            target_id = title_to_id.get(match.strip())
            if target_id:
                _add_edge(article.id, target_id, "link")

    return {"nodes": nodes, "edges": edges}


# ─────────────────────────────────────────────────────────────────────────────
# 自動補 [[連結]]
# ─────────────────────────────────────────────────────────────────────────────

_RELATED_HEADER = "\n\n---\n\n## 相關文章\n\n"
_RELATED_PATTERN = re.compile(r'\n\n---\n\n## 相關文章\n\n[\s\S]*$')


def auto_link_articles(db: Session, dry_run: bool = False) -> Dict[str, Any]:
    """
    掃描所有已發佈文章，找出標籤重疊或同分類的相關文章，
    在每篇文章 body 結尾加入「## 相關文章」區塊（含 [[連結]]）。
    若 body 已有該區塊則先移除再重寫（冪等操作）。
    dry_run=True 時只回傳計畫，不寫入 DB。
    """
    articles = db.query(WikiArticle).filter(WikiArticle.is_published == True).all()
    title_map: Dict[str, str] = {a.title: a.id for a in articles}
    tags_map: Dict[str, List[str]] = {}
    for a in articles:
        tags_map[a.id] = json.loads(a.tags) if isinstance(a.tags, str) else (a.tags or [])

    updated = 0
    skipped = 0
    plan: List[Dict[str, Any]] = []

    for article in articles:
        tags_a = set(tags_map.get(article.id, []))

        related: List[WikiArticle] = []
        for other in articles:
            if other.id == article.id:
                continue
            tags_b = set(tags_map.get(other.id, []))
            if tags_a & tags_b:
                related.append(other)
            elif other.category == article.category and len(related) < 3:
                related.append(other)
        related = related[:5]

        if not related:
            skipped += 1
            continue

        clean_body = _RELATED_PATTERN.sub("", article.body or "").rstrip()
        links = "\n".join(f"- [[{r.title}]]" for r in related)
        new_body = clean_body + _RELATED_HEADER + links

        plan.append({
            "id":    article.id,
            "title": article.title,
            "links": [r.title for r in related],
        })

        if not dry_run:
            article.body = new_body
            updated += 1

    if not dry_run:
        db.commit()

    return {
        "updated": updated,
        "skipped": skipped,
        "plan":    plan,
        "dry_run": dry_run,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Obsidian 雙向同步
# ─────────────────────────────────────────────────────────────────────────────

def _wiki_dir() -> Path:
    return Path(__file__).resolve().parent.parent.parent.parent / "docs" / "wiki"


def _safe_filename(slug: str) -> str:
    name = re.sub(r'[<>:"/\\|?*]', "-", slug)
    return (name[:80] if name else "article") + ".md"


def _write_article_to_md(article: WikiArticle, base_dir: Path) -> Path:
    """將一篇文章寫入 docs/wiki/{category}/{slug}.md"""
    import yaml

    category_dir = base_dir / article.category
    category_dir.mkdir(parents=True, exist_ok=True)

    tags = json.loads(article.tags) if isinstance(article.tags, str) else (article.tags or [])

    meta: Dict[str, Any] = {
        "id":           article.id,
        "title":        article.title,
        "slug":         article.slug,
        "category":     article.category,
        "tags":         tags,
        "author":       article.author,
        "author_id":    article.author_id,
        "is_published": bool(article.is_published),
        "created_at":   article.created_at.isoformat() if article.created_at else "",
        "updated_at":   article.updated_at.isoformat() if article.updated_at else "",
    }

    frontmatter = yaml.dump(
        meta, allow_unicode=True, default_flow_style=False,
        sort_keys=False, width=120,
    )
    filename = _safe_filename(article.slug)
    filepath = category_dir / filename
    filepath.write_text(f"---\n{frontmatter}---\n\n{article.body}\n", encoding="utf-8")
    return filepath


def _read_md_file(filepath: Path) -> Optional[Dict[str, Any]]:
    try:
        import yaml
        text = filepath.read_text(encoding="utf-8")
        if not text.startswith("---"):
            return {
                "title":    filepath.stem,
                "body":     text.strip(),
                "category": filepath.parent.name if filepath.parent.name in ("sop", "dev") else "sop",
                "tags":     [],
            }
        parts = text.split("---", 2)
        if len(parts) < 3:
            return None
        meta = yaml.safe_load(parts[1]) or {}
        body = parts[2].strip()
        meta["body"] = body
        return meta
    except Exception:
        return None


def export_to_obsidian(db: Session) -> Dict[str, Any]:
    base_dir = _wiki_dir()
    base_dir.mkdir(parents=True, exist_ok=True)

    articles = db.query(WikiArticle).filter(WikiArticle.is_published == True).all()

    exported = 0
    skipped = 0
    errors: List[str] = []

    for article in articles:
        try:
            category_dir = base_dir / article.category
            filename = _safe_filename(article.slug)
            filepath = category_dir / filename

            if filepath.exists():
                existing = _read_md_file(filepath)
                if existing:
                    existing_updated = existing.get("updated_at", "")
                    db_updated = article.updated_at.isoformat() if article.updated_at else ""
                    if existing_updated and db_updated and existing_updated >= db_updated:
                        skipped += 1
                        continue

            _write_article_to_md(article, base_dir)
            exported += 1
        except Exception as e:
            errors.append(f"{article.title}：{e}")

    return {
        "exported": exported,
        "skipped":  skipped,
        "errors":   errors,
        "wiki_dir": str(base_dir),
    }


def import_from_obsidian(db: Session) -> Dict[str, Any]:
    """
    從 docs/wiki/ 讀取所有 .md 檔案，同步進 DB。
    - 有 id 且 DB 中存在 → 比對 updated_at，較新則更新
    - 有 id 但 DB 中不存在 → 新增（保留原 id）
    - 無 id → 新增（產生新 id，並寫回 id 到 .md 檔）
    回傳：{ imported, updated, skipped, errors, wiki_dir }
    """
    from app.core.time import twnow

    base_dir = _wiki_dir()
    if not base_dir.exists():
        return {
            "imported": 0, "updated": 0, "skipped": 0,
            "errors": [f"docs/wiki/ 資料夾不存在：{base_dir}"],
            "wiki_dir": str(base_dir),
        }

    md_files = list(base_dir.glob("**/*.md"))

    imported = 0
    updated  = 0
    skipped  = 0
    errors: List[str] = []

    for filepath in md_files:
        try:
            meta = _read_md_file(filepath)
            if not meta:
                skipped += 1
                continue

            title  = str(meta.get("title", filepath.stem)).strip()
            body   = str(meta.get("body", "")).strip()
            category = str(meta.get("category", "sop"))
            if category not in ("sop", "dev"):
                category = filepath.parent.name if filepath.parent.name in ("sop", "dev") else "sop"

            tags_raw = meta.get("tags", [])
            tags_list = tags_raw if isinstance(tags_raw, list) else [tags_raw]
            tags_json = json.dumps([str(t) for t in tags_list], ensure_ascii=False)

            slug   = str(meta.get("slug", _slugify(title)))
            author = str(meta.get("author", "Obsidian"))
            author_id = str(meta.get("author_id", "obsidian"))
            is_published = bool(meta.get("is_published", True))

            file_updated_str = str(meta.get("updated_at", ""))
            article_id = str(meta.get("id", "")).strip()

            existing: Optional[WikiArticle] = None
            if article_id:
                existing = db.query(WikiArticle).filter(WikiArticle.id == article_id).first()
            if not existing:
                existing = db.query(WikiArticle).filter(WikiArticle.slug == slug).first()

            if existing:
                db_updated_str = existing.updated_at.isoformat() if existing.updated_at else ""
                if file_updated_str and db_updated_str and file_updated_str <= db_updated_str:
                    skipped += 1
                    continue

                existing.title       = title
                existing.body        = body
                existing.category    = category
                existing.tags        = tags_json
                existing.author      = author
                existing.is_published = is_published
                db.commit()
                updated += 1
            else:
                new_id = article_id if article_id else str(uuid.uuid4())
                new_slug = _unique_slug(db, slug)
                article = WikiArticle(
                    id=new_id,
                    title=title,
                    slug=new_slug,
                    body=body,
                    summary=_auto_summary(body),
                    category=category,
                    tags=tags_json,
                    author=author,
                    author_id=author_id,
                    is_published=is_published,
                )
                db.add(article)
                db.commit()
                db.refresh(article)

                if not article_id:
                    _write_article_to_md(article, base_dir)

                imported += 1

        except Exception as e:
            errors.append(f"{filepath.name}：{e}")

    return {
        "imported": imported,
        "updated":  updated,
        "skipped":  skipped,
        "errors":   errors,
        "wiki_dir": str(base_dir),
    }
