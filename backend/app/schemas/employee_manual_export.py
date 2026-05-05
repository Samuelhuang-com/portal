"""
員工操作手冊匯出 — Pydantic Schemas
"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ModuleInfo(BaseModel):
    key: str
    name: str
    description: str
    menu_path: str


class GenerateRequest(BaseModel):
    module_key: str
    doc_types: list[str]        # e.g. ["manual", "supervisor", "faq", "training", "voice", "newbie", "troubleshoot"]
    export_format: str = "zip"  # "markdown" | "zip"


class GenerateResult(BaseModel):
    module_key: str
    module_name: str
    generated_files: list[str]
    export_path: str
    generated_at: datetime
    download_url: str


class ExportStatusResponse(BaseModel):
    module_key: str
    module_name: str
    has_export: bool
    generated_at: Optional[datetime] = None
    files: list[str] = []
    download_url: Optional[str] = None
