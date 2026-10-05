"""樓層巡檢圖：套用 2026-10-05 點位清單（樓層巡檢圖_點位清單與修正紀錄_1005.xlsx）

Revision ID: fmap1005
Revises: fmapfbi
Create Date: 2026-10-05

內容與後端啟動步驟 services/floor_map/bootstrap.sync_point_list 共用同一個函式（開發環境不跑 alembic，
啟動時也會做一次；兩邊可重跑、不會重複）：
  商場工務巡檢：新增 SF-B11（B1F）、SF-B21（B2F）、SF-B31（B3F）、SF-B41（B4F）；
                AH-R21／R23／R27／R32 供應區域更新；B1~B4 電信設備補機房位置
  整棟巡檢　　：B4F 汙廢水 1 點拆成 SP-1～3、WP-1～3 六點（舊點改名為 SP-1 保留位置）；
                發電機、電信設備、油脂截流槽、連續壁、下水塔補機房位置，冷卻水塔／發電機補供應區域
不動 x／y／placement；使用者自己改過的機房位置／供應區域不會被蓋掉；已停用的點不會被重新啟用。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "fmap1005"
down_revision: Union[str, None] = "fmapfbi"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from app.services.floor_map.bootstrap import TABLE, _SEED, sync_point_list

    bind = op.get_bind()
    if not sa.inspect(bind).has_table(TABLE):
        return
    for module in _SEED:
        sync_point_list(bind, module, tag="migration:fmap1005")


def downgrade() -> None:
    # 只移除本次新增的點；改名與屬性更新不還原（資料修正，非結構變更）
    bind = op.get_bind()
    if sa.inspect(bind).has_table("floor_map_points"):
        bind.execute(sa.text(
            "DELETE FROM floor_map_points WHERE created_by IN ('migration:fmap1005', 'pointlist:20261005')"
        ))
