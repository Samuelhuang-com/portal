/**
 * 週期採購 — Dashboard
 *
 * 2026-07-11（拿掉「批次」後改版）：
 *   - 移除「開放中批次」統計（批次實體已拿掉，見 cycle_purchase_request.py
 *     開頭說明）。
 *   - 新增「待辦提醒」：登入者自己部門（依 CpDepartment.owner_user_id 判斷）
 *     還沒填/被退回要改的請購單，以及（若有簽核權限）全部待簽核的請購單。
 *     第一版先只做這裡的 Dashboard 卡片，之後若要加 email 通知另外規劃。
 *
 * 完整 KPI／彙整／採購／驗收／請款等流程留待後續階段（見規劃評估報告第八節）。
 *
 * 2026-07-17（第三次調整，請購單流程大改版）：拿掉送出／核准，「待簽核」卡片
 * 改成「本月待關閉」，改看 cycle_purchase_close 權限，提醒買家記得在月底前
 * 把當月的請購單關閉（見 services/cycle_purchase_request_service.py
 * get_dashboard_todos 開頭說明）。
 *
 * 2026-08-09（錯誤處理修正，起因：Samuel 回報「dashboard 完全沒有資料出現」）：
 * 根因是 DB migration 沒跑、`GET /cycles` 回 500。但**症狀被這一頁的寫法放大**成
 * 「什麼都沒有」：三支統計 API 原本用 `Promise.all`，任一支失敗整組 reject，
 * `setCounts` 完全不會被呼叫 —— 供應商與料號那兩支明明是好的，卡片卻一起停在 0。
 * 而且整個檔案沒有任何 `.catch`，錯誤被吞掉，畫面上看不出「這是壞掉」還是
 * 「本來就沒資料」。兩者的處理方式天差地遠，不能讓使用者分不出來。
 *
 * 改法：
 *   - `Promise.all` → `Promise.allSettled`：一支掛掉不影響另外兩支，能顯示的先顯示。
 *   - 每支各自記錄失敗，頁面頂端用紅色 Alert 明確列出是哪幾支失敗。
 *   - 待辦那支也補上 `.catch`。
 * ⚠️ 這裡刻意**不**在失敗時把卡片藏起來或顯示「—」：數字停在 0 但旁邊有紅字說明，
 *    比整塊消失更容易讓人意識到「是抓不到，不是真的沒有」。
 */
import { useEffect, useState } from 'react'
import { Alert, Badge, Card, Col, Empty, List, Row, Statistic, Typography } from 'antd'
import {
  ShopOutlined, DatabaseOutlined, CalendarOutlined, ClockCircleOutlined, LockOutlined,
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { getCycles, getItems, getTodos, getVendors } from '@/api/cyclePurchase'
import type { CpRequest, TodoSummary } from '@/types/cyclePurchase'

const { Title } = Typography

/**
 * 把 axios 的錯誤轉成「人看得懂的一行字」。
 *
 * ⚠️ 不能直接用 `err.response.data.detail`：FastAPI 的 **422 參數驗證錯誤**，
 *    `detail` 是一個**物件陣列**（`[{loc, msg, type}, ...]`）而不是字串，
 *    塞進樣板字串會變成 `[object Object]`（2026-08-09 實際踩到）。
 *    只有 `HTTPException(detail="...")` 丟出來的才是字串。
 */
function apiErrorMessage(err: any): string {
  const detail = err?.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    // 422：把每一筆的欄位位置與訊息組起來，例如「query.per_page：Input should be >= 5」
    const parts = detail
      .map((d: any) => {
        const loc = Array.isArray(d?.loc) ? d.loc.join('.') : ''
        const msg = d?.msg || JSON.stringify(d)
        return loc ? `${loc}：${msg}` : msg
      })
      .filter(Boolean)
    if (parts.length) return `參數驗證失敗（${parts.join('；')}）`
  }
  if (detail && typeof detail === 'object') return JSON.stringify(detail)
  const status = err?.response?.status
  return err?.message ? (status ? `${err.message}（HTTP ${status}）` : err.message) : '載入失敗'
}

export default function CpDashboardPage() {
  const navigate = useNavigate()
  const [counts, setCounts] = useState({
    vendors: 0,
    items: 0,
    activeCycles: 0,
  })
  const [todos, setTodos] = useState<TodoSummary | null>(null)
  const [todosLoading, setTodosLoading] = useState(true)
  const [loadErrors, setLoadErrors] = useState<string[]>([])

  useEffect(() => {
    // 只加入還沒出現過的訊息。這支本身是純的（updater 只依 prev 算新值，沒有副作用），
    // 所以 React 18 StrictMode 重複呼叫 updater、或 dev 模式把 effect 跑兩次，
    // 都不會讓同一則錯誤被列兩次。
    const addErrors = (msgs: string[]) =>
      setLoadErrors((prev) => {
        const merged = [...prev]
        for (const m of msgs) if (!merged.includes(m)) merged.push(m)
        return merged
      })

    // allSettled 而非 all：一支 API 掛掉不該讓另外兩支的數字也消失（見檔案開頭說明）
    // ⚠️ per_page 最小值是 5（後端 Query(20, ge=5, le=200)）。這裡只是要拿 total，
    //    抓幾筆都無所謂，但**不能傳 1**，會回 422。原本就是傳 1，所以「啟用中料號」
    //    其實一直都是 0 —— 只是錯誤被 Promise.all 吞掉，沒人發現（2026-08-09 修正）。
    Promise.allSettled([
      getVendors({ is_active: true }),
      getItems({ is_active: true, per_page: 5 }),
      getCycles({ status: 'active' }),
    ]).then(([vendorsRes, itemsRes, cyclesRes]) => {
      // ⚠️ 先把結果算完再 setState，**不要在 setCounts 的 updater 裡面 push 錯誤訊息**。
      //    updater 必須是純函式，React 18 StrictMode 會刻意重複呼叫它來抓副作用——
      //    原本把 errors.push 寫在裡面，結果同一則錯誤被列了兩次（2026-08-09 實際踩到）。
      const errors: string[] = []
      const pick = (
        res: PromiseSettledResult<any>,
        label: string,
        read: (data: any) => number,
      ): number | null => {
        if (res.status === 'fulfilled') return read(res.value.data)
        errors.push(`${label}：${apiErrorMessage(res.reason)}`)
        return null   // null＝這支失敗，保留前一次的值
      }
      const next = {
        vendors: pick(vendorsRes, '啟用中供應商', (d) => d.length),
        items: pick(itemsRes, '啟用中料號', (d) => d.total),
        activeCycles: pick(cyclesRes, '啟用中週期', (d) => d.length),
      }
      setCounts((prev) => ({
        vendors: next.vendors ?? prev.vendors,
        items: next.items ?? prev.items,
        activeCycles: next.activeCycles ?? prev.activeCycles,
      }))
      if (errors.length) addErrors(errors)
    })
    getTodos()
      .then((r) => setTodos(r.data))
      .catch((err: any) => addErrors([`我的待辦：${apiErrorMessage(err)}`]))
      .finally(() => setTodosLoading(false))
  }, [])

  const renderRequestItem = (r: CpRequest) => (
    <List.Item onClick={() => navigate(`/cycle-purchase/requests/${r.id}`)} style={{ cursor: 'pointer' }}>
      <List.Item.Meta
        title={r.request_no}
        description={`${r.cycle_name || ''}／${r.period_label}　${r.company} - ${r.department_name}`}
      />
    </List.Item>
  )

  return (
    <div>
      <Title level={4} style={{ marginBottom: 16 }}>週採（週期採購管理）</Title>

      {loadErrors.length > 0 && (
        <Alert
          type="error"
          showIcon
          style={{ marginBottom: 16 }}
          message="部分資料載入失敗，畫面上的數字不完整"
          description={(
            <>
              <ul style={{ paddingLeft: 18, margin: '0 0 8px' }}>
                {loadErrors.map((e, i) => <li key={i}>{e}</li>)}
              </ul>
              <span>
                若訊息是「no such column」，代表資料庫欄位還沒補齊 ——
                執行 <code>apply_cycle_purchase_summary_migration.bat</code> 後重啟後端即可。
              </span>
            </>
          )}
        />
      )}

      <Alert
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
        message="上線範圍"
        description="目前已提供：基礎設定（供應商／部門／成本中心／會計科目主檔）、料號主檔與料號對照表、週期設定、請購單（含產生本期請購單、填寫、關閉／重新開啟）。彙整單／採購單／驗收單／請款單等流程在後續階段陸續開放，詳見規劃評估報告第八節分期計畫。"
      />

      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={8}>
          <Card size="small">
            <Statistic title="啟用中供應商" value={counts.vendors} prefix={<ShopOutlined />} />
          </Card>
        </Col>
        <Col span={8}>
          <Card size="small">
            <Statistic title="啟用中料號" value={counts.items} prefix={<DatabaseOutlined />} />
          </Card>
        </Col>
        <Col span={8}>
          <Card size="small">
            <Statistic title="啟用中週期" value={counts.activeCycles} prefix={<CalendarOutlined />} />
          </Card>
        </Col>
      </Row>

      <Row gutter={16}>
        <Col span={12}>
          <Card
            size="small"
            title={
              <span>
                <ClockCircleOutlined style={{ marginRight: 8 }} />
                我的待辦（我部門本月待關閉）
              </span>
            }
            loading={todosLoading}
          >
            {todos && todos.my_pending.length > 0 ? (
              <List dataSource={todos.my_pending} renderItem={renderRequestItem} size="small" />
            ) : (
              <Empty
                description={
                  todos ? '目前沒有待處理的請購單' : ''
                }
                image={Empty.PRESENTED_IMAGE_SIMPLE}
              />
            )}
          </Card>
        </Col>
        <Col span={12}>
          <Card
            size="small"
            title={
              <span>
                <LockOutlined style={{ marginRight: 8 }} />
                本月待關閉
                {todos && todos.pending_close_count > 0 && (
                  <Badge count={todos.pending_close_count} style={{ marginLeft: 8 }} />
                )}
              </span>
            }
            loading={todosLoading}
          >
            {todos && todos.pending_close.length > 0 ? (
              <List dataSource={todos.pending_close} renderItem={renderRequestItem} size="small" />
            ) : (
              <Empty
                description={todos ? '這個月沒有還沒關閉的請購單（或您沒有關閉權限）' : ''}
                image={Empty.PRESENTED_IMAGE_SIMPLE}
              />
            )}
          </Card>
        </Col>
      </Row>
    </div>
  )
}
