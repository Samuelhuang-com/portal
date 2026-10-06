/**
 * 人員動態「工作視角」— 說明 Drawer（2026-10-06）
 * 內容：①狀態（桌子畫面）②工作中人物樣式 P01～P15（動畫）③判斷順序 ④資料來源與限制
 * 樣式清單／判斷順序來自 staffPoses.tsx（POSE_RULES／RULE_ORDER），須與後端 _pose_of 一致。
 */
import React from 'react'
import { Drawer, Table, Tag, Typography } from 'antd'

import { Desk, PoseArt, POSE_LABEL, POSE_RULES, RULE_ORDER, WMODE, type WMode } from './staffPoses'

const { Title, Paragraph, Text } = Typography
const STAGE = 'linear-gradient(160deg, #0d1e30 0%, #13304d 100%)'
const DEMO_COLOR = '#4BA8E8'

const STATE_TEXT: Record<WMode | 'open', string> = {
  work:  '有一筆工作的開始～結束包含這個時間。人物依工作內容換樣式（見下方）；坐在桌前打字是預設樣式 P01。',
  gap:   '上一筆已結束、下一筆還沒開始：這段時間工作日誌沒有紀錄（未取到值），人物站在桌旁、頭上一個問號。不代表沒在工作。',
  off:   '今天第一筆紀錄還沒開始：桌子是空的。',
  after: '當天最後一筆已結束、之後沒有紀錄：螢幕關、人離開。',
  open:  '已打卡開始、還沒填結束（工程人員到現場打卡）：今天＝視為做到現在，人物頭上紅點閃爍，卡片標「進行中」。過去日期＝視為 10 分鐘並標「未填結束」。',
}

export default function StaffWorkHelp({ open, onClose }: { open: boolean; onClose: () => void }) {
  const groups = [...new Set(POSE_RULES.map(r => r.group))]
  return (
    <Drawer title="工作視角 — 畫面說明" placement="right" width={760} open={open} onClose={onClose} destroyOnClose>
      <Paragraph type="secondary" style={{ marginTop: -4 }}>
        每位人員一張桌子，依飯店工務／商場工務分區；時間與「大樓視角」共用（今天預設 LIVE 跟著現在走，可拖曳或播放回放）。
        所有狀態都來自<b>工作日誌</b>（各模組工單子表的開始／結束時間），不是定位或刷卡。
      </Paragraph>

      {/* ① 狀態 */}
      <Title level={5}>① 狀態</Title>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 330px), 1fr))', gap: 10 }}>
        {([['work', false], ['work', true], ['gap', false], ['off', false], ['after', false]] as [WMode, boolean][]).map(([m, isOpen]) => (
          <div key={m + String(isOpen)} style={{ display: 'flex', gap: 10, alignItems: 'center', border: '1px solid #e6ebf1', borderRadius: 8, padding: 8 }}>
            <div style={{ background: STAGE, borderRadius: 6, flex: 'none' }}>
              <Desk color={DEMO_COLOR} mode={m} open={isOpen} />
            </div>
            <div style={{ minWidth: 0 }}>
              <Tag color={isOpen ? 'red' : WMODE[m].color} style={{ color: isOpen ? undefined : '#0d1e30', fontWeight: 600 }}>
                {isOpen ? '進行中' : WMODE[m].label}
              </Tag>
              <div style={{ fontSize: 12, color: '#555', marginTop: 4 }}>{isOpen ? STATE_TEXT.open : STATE_TEXT[m]}</div>
            </div>
          </div>
        ))}
      </div>

      {/* ② 工作中人物樣式 */}
      <Title level={5} style={{ marginTop: 20 }}>② 工作中的人物樣式（依工作內容）</Title>
      {groups.map(g => (
        <div key={g} style={{ marginBottom: 12 }}>
          <Text type="secondary" style={{ fontSize: 12 }}>{g}</Text>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 220px), 1fr))', gap: 8, marginTop: 4 }}>
            {POSE_RULES.filter(r => r.group === g).map(r => (
              <div key={r.id} style={{ border: '1px solid #e6ebf1', borderRadius: 8, padding: 8, display: 'flex', flexDirection: 'column', gap: 4 }}>
                <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                  <Tag color="blue" style={{ margin: 0, fontFamily: 'ui-monospace, Consolas, monospace' }}>{r.id}</Tag>
                  <b>{POSE_LABEL[r.id]}</b>
                </div>
                <div style={{ background: STAGE, borderRadius: 6, display: 'flex', justifyContent: 'center' }}>
                  {r.id === 'P01' ? <Desk color={DEMO_COLOR} mode="work" open={false} /> : <PoseArt pose={r.id} color={DEMO_COLOR} />}
                </div>
                <div style={{ fontSize: 12 }}>{r.rule}</div>
                <div style={{ fontSize: 12, color: '#888' }}>例：{r.example}</div>
              </div>
            ))}
          </div>
        </div>
      ))}

      {/* ③ 判斷順序 */}
      <Title level={5} style={{ marginTop: 20 }}>③ 判斷順序</Title>
      <Paragraph type="secondary" style={{ fontSize: 12 }}>由上往下，第一個符合的就用。報修類型採報修統計同一套標準類型（例：「衛厠」視同「衛廁」、「冷氣」視同「空調」）。</Paragraph>
      <Table
        size="small" pagination={false} rowKey={r => r.k}
        dataSource={RULE_ORDER.map(([cond, id], i) => ({ k: i + 1, cond, id }))}
        columns={[
          { title: '順序', dataIndex: 'k', width: 56, align: 'center' },
          { title: '條件', dataIndex: 'cond' },
          { title: '樣式', dataIndex: 'id', width: 170,
            render: (id: string) => <span><Tag color="blue" style={{ fontFamily: 'ui-monospace, Consolas, monospace' }}>{id}</Tag>{POSE_LABEL[id]}</span> },
        ]}
      />

      {/* ④ 限制 */}
      <Title level={5} style={{ marginTop: 20 }}>④ 資料來源與限制</Title>
      <ul style={{ paddingLeft: 18, fontSize: 13, color: '#555' }}>
        <li>工作中／未取到值的判斷只看工作日誌的時間；沒有時間的紀錄排不上時間軸，會在員工現況卡片註明筆數。</li>
        <li>分區（飯店工務／商場工務）依該人員當天多數工作的場域判斷。</li>
        <li>LIVE 每 5 分鐘重抓資料，Ragic 同步本身也有間隔，畫面會比現場晚幾分鐘到十幾分鐘。</li>
        <li>人物樣式只是依工作類型的示意，不代表現場實際使用的工具。</li>
      </ul>
    </Drawer>
  )
}
