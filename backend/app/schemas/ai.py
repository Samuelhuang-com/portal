"""
AI 助理 Pydantic Schemas
"""
from typing import Optional
from pydantic import BaseModel


class ChatMessage(BaseModel):
    """對話歷史中的單則訊息"""
    role: str   # "user" | "assistant"
    content: str


class AIQueryRequest(BaseModel):
    """POST /api/v1/ai/query-workorder 請求體"""
    question: str
    messages: list[ChatMessage] = []   # 歷史對話（最多保留 10 則）


class RepairRow(BaseModel):
    """工單查詢結果中的單筆資料列（供前端表格渲染）"""
    location: str           # "飯店" | "商場"
    case_no: str
    title: str
    floor: str
    status: str             # "已結案" | "未結案"
    occurred_at: str        # "YYYY-MM-DD" 或空字串
    responsible_unit: str
    close_days: Optional[float] = None
    total_fee: float = 0.0


class AIQueryResponse(BaseModel):
    """POST /api/v1/ai/query-workorder 回應體"""
    answer: str                         # Claude 自然語言回答
    has_table: bool = False             # 是否有表格資料可渲染
    table_data: list[RepairRow] = []    # 表格資料列（has_table=True 時有效）
    total_count: Optional[int] = None   # 符合條件的總筆數（包含截斷部分）


class AIHistoryItem(BaseModel):
    """GET /api/v1/ai/history 單筆歷史記錄"""
    id: str
    question: str
    answer: str
    has_table: bool = False
    table_data: list[RepairRow] = []
    total_count: Optional[int] = None
    from_cache: bool = False
    created_at: str             # "YYYY-MM-DD HH:MM"
