/**
 * 週採全域流程列（2026-09-25，草稿裁示「1」）
 *
 * 固定貼在週採每個頁面最上方，讓使用者不管從左側選單哪一頁進來，都能一眼
 * 看出現在在流程第幾步、前後各是什麼。步驟只依路由（pathname）判斷目前在
 * 哪一步，不吃任何業務資料——不呼叫 API、不查權限，純粹是導覽用的視覺元件，
 * 資料不同步造成的風險趨近於零。
 *
 * 只有前 3 步（週期設定／產生請購單／填寫並關閉）目前有實際頁面對得上：
 * 「填寫並關閉」對應 /cycle-purchase/requests 與 /cycle-purchase/requests/:id
 * 這兩個路由（清單頁做「產生＋關閉」，詳情頁做「填寫」，草稿裁示不用細分）。
 * 「彙整」對應 /cycle-purchase/summary。「拋轉Ragic簽核」目前沒有獨立頁面
 * （彙整單頁內的拋轉動作），先不設可點路由，只做視覺佔位。「驗收」「請款」
 * 「稽核」分別對應 receiving / payments / audit-log（含各自 :id 詳情與
 * receiving-report 報表頁）。
 *
 * 只有「已完成」的步驟可以點擊跳轉；目前步驟與未來步驟不可點（避免使用者
 * 跳過關閉直接想點進彙整，卻在彙整頁被擋，體驗更差）。
 */
import React from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { CheckOutlined } from '@ant-design/icons'

type StepState = 'done' | 'current' | 'pending'

interface StepDef {
  label: string
  /** 判斷「目前在這一步」用的路徑前綴，可有多個（清單頁＋詳情頁算同一步） */
  matchPrefixes: string[]
  /** 已完成時可點擊跳轉的路徑；undefined＝不可點（如拋轉Ragic簽核目前無獨立頁） */
  linkTo?: string
}

const STEPS: StepDef[] = [
  { label: '週期設定',      matchPrefixes: ['/cycle-purchase/cycles'],                                   linkTo: '/cycle-purchase/cycles' },
  { label: '產生請購單',    matchPrefixes: [],                                                            linkTo: '/cycle-purchase/requests' },
  { label: '填寫並關閉',    matchPrefixes: ['/cycle-purchase/requests'],                                  linkTo: '/cycle-purchase/requests' },
  { label: '彙整',          matchPrefixes: ['/cycle-purchase/summary'],                                   linkTo: '/cycle-purchase/summary' },
  { label: '拋轉Ragic簽核', matchPrefixes: [] },
  { label: '驗收',          matchPrefixes: ['/cycle-purchase/receiving'],                                 linkTo: '/cycle-purchase/receiving' },
  { label: '請款／稽核',    matchPrefixes: ['/cycle-purchase/payments', '/cycle-purchase/audit-log'],      linkTo: '/cycle-purchase/payments' },
]

// 「產生請購單」與「填寫並關閉」都落在 /cycle-purchase/requests 底下，路由層面
// 分不開，草稿裁示不用細分兩步：實務上一律把 requests 路由視為「填寫並關閉」
// （currentIndex=2），「產生請購單」永遠顯示為已完成（index 1，因為若使用者
// 人在 requests 頁，代表週期設定與產生請購單這兩個前置步驟本來就已經可以做過）。
function currentStepIndex(pathname: string): number {
  if (pathname.startsWith('/cycle-purchase/cycles')) return 0
  if (pathname.startsWith('/cycle-purchase/requests')) return 2
  if (pathname.startsWith('/cycle-purchase/summary')) return 3
  if (pathname.startsWith('/cycle-purchase/receiving') || pathname.startsWith('/cycle-purchase/receiving-report')) return 5
  if (pathname.startsWith('/cycle-purchase/payments') || pathname.startsWith('/cycle-purchase/audit-log')) return 6
  // 料號主檔／供應商等主檔頁面不在主流程上，不特別標示目前步驟（全部灰階）
  return -1
}

function stateOf(index: number, current: number): StepState {
  if (current < 0) return 'pending'
  if (index < current) return 'done'
  if (index === current) return 'current'
  return 'pending'
}

const DONE_COLOR = '#3aa76d'
const CURRENT_COLOR = '#4ba8e8'
const CURRENT_RING = '#ddeffb'
const PENDING_BORDER = '#d7dbe2'
const PENDING_TEXT = '#9aa2b1'
const LINE_DONE = '#3aa76d'
const LINE_PENDING = '#e2e5ea'

const FlowSteps: React.FC = () => {
  const navigate = useNavigate()
  const location = useLocation()
  const current = currentStepIndex(location.pathname)

  const go = (step: StepDef, state: StepState) => {
    if (state !== 'done' || !step.linkTo) return
    navigate(step.linkTo)
  }

  return (
    <div
      style={{
        background: '#ffffff',
        border: '1px solid #e5e7eb',
        borderRadius: 8,
        padding: '14px 24px 12px',
        marginBottom: 16,
        overflowX: 'auto',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', minWidth: 760 }}>
        {STEPS.map((step, i) => {
          const state = stateOf(i, current)
          const clickable = state === 'done' && !!step.linkTo
          return (
            <React.Fragment key={step.label}>
              {i > 0 && (
                <div
                  style={{
                    flexGrow: 1,
                    height: 2,
                    marginTop: 15,
                    background: i - 1 < current ? LINE_DONE : LINE_PENDING,
                  }}
                />
              )}
              <div
                onClick={() => go(step, state)}
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  minWidth: 88,
                  cursor: clickable ? 'pointer' : 'default',
                }}
                title={clickable ? `跳到「${step.label}」` : undefined}
              >
                <div
                  style={{
                    width: 30,
                    height: 30,
                    borderRadius: 999,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexShrink: 0,
                    background: state === 'done' ? DONE_COLOR : state === 'current' ? CURRENT_COLOR : '#ffffff',
                    border: state === 'pending' ? `2px solid ${PENDING_BORDER}` : 'none',
                    boxShadow: state === 'current' ? `0 0 0 4px ${CURRENT_RING}` : 'none',
                  }}
                >
                  {state === 'done' && <CheckOutlined style={{ color: '#fff', fontSize: 13 }} />}
                  {state === 'current' && <div style={{ width: 7, height: 7, borderRadius: 999, background: '#fff' }} />}
                  {state === 'pending' && (
                    <span style={{ fontSize: 12, fontWeight: 700, color: PENDING_TEXT }}>{i + 1}</span>
                  )}
                </div>
                <div
                  style={{
                    marginTop: 6,
                    fontSize: 12.5,
                    textAlign: 'center',
                    fontWeight: state === 'current' ? 700 : 600,
                    color: state === 'done' ? DONE_COLOR : state === 'current' ? '#2c7fbd' : PENDING_TEXT,
                  }}
                >
                  {step.label}
                </div>
                {state === 'current' && (
                  <div style={{ fontSize: 10.5, color: '#8a93a3' }}>目前在這裡</div>
                )}
              </div>
            </React.Fragment>
          )
        })}
      </div>
    </div>
  )
}

export default FlowSteps
