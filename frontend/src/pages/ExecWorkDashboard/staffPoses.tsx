/**
 * 人員動態「工作視角」— 工作中的人物樣式 P02～P15（P01＝坐著打字，畫在 StaffWorkBoard 的桌子上）
 * 2026-10-06 使用者採用 P01～P15；樣式代碼由後端 work_journal_path._pose_of 判斷。
 * 每款是一段 SVG（viewBox 0 0 170 140），人物主色＝該人員代表色。
 */
import React from 'react'

export const POSE_LABEL: Record<string, string> = {
  P01: '坐著打字', P02: '巡檢・手電筒', P03: '巡檢・檢查板', P04: '抄表', P05: '保養・扳手',
  P06: '客房保養・推車', P07: '報修・工具箱', P08: '空調', P09: '衛廁', P10: '水電・照明',
  P11: '內裝', P12: '門鎖・弱電', P13: '緊急事件', P14: '訓練／會議', P15: '上級交辦',
}

const SKIN = '#f2c9a0', HAT = '#F5C542', DARK = '#0d1e30', MET = '#9fb3c8'

function person(c: string, o: { hat?: boolean; siren?: boolean; legs?: 'walk' | 'stand'; armR?: string; armL?: string; bodyCls?: string } = {}) {
  const legs = o.legs === 'stand'
    ? `<rect x="70" y="88" width="7" height="30" rx="3" fill="#2b4058"/><rect x="83" y="88" width="7" height="30" rx="3" fill="#2b4058"/>`
    : `<rect class="swp-walkL" x="70" y="88" width="7" height="30" rx="3" fill="#2b4058"/><rect class="swp-walkR" x="83" y="88" width="7" height="30" rx="3" fill="#2b4058"/>`
  return `<g class="${o.bodyCls ?? ''}">${legs}
    <path d="M65 90 Q65 52 80 52 Q95 52 95 90 Z" fill="${c}"/>${o.armL ?? ''}
    <circle cx="80" cy="38" r="12" fill="${SKIN}"/><circle cx="76" cy="37" r="1.5" fill="${DARK}"/><circle cx="84" cy="37" r="1.5" fill="${DARK}"/>
    ${o.hat ? `<path d="M66 34 Q66 20 80 20 Q94 20 94 34 Z" fill="${HAT}"/><rect x="63" y="32" width="34" height="4" rx="2" fill="${HAT}"/><rect x="78" y="21" width="4" height="12" fill="#e0ac2a"/>` : ''}
    ${o.siren ? `<rect x="74" y="16" width="12" height="8" rx="3" fill="#ff4d4f" class="swp-siren"/><rect x="72" y="23" width="16" height="4" rx="1" fill="#555"/>` : ''}
    ${o.armR ?? ''}</g>`
}
const arm = (c: string, x1: number, y1: number, x2: number, y2: number) =>
  `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="${c}" stroke-width="7" stroke-linecap="round"/><circle cx="${x2}" cy="${y2}" r="4" fill="${SKIN}"/>`

function art(pose: string, c: string): string {
  const A = (x1: number, y1: number, x2: number, y2: number) => arm(c, x1, y1, x2, y2)
  const hangL = A(68, 60, 64, 84)
  switch (pose) {
    case 'P02': return person(c, { hat: true, armL: hangL, armR: `${A(92, 60, 108, 68)}<rect x="106" y="62" width="14" height="8" rx="2" fill="#555"/>
      <g class="swp-sweep"><polygon points="120,62 165,44 165,92 120,70" fill="#FFE58F" opacity=".45"/></g>` })
    case 'P03': return person(c, { hat: true, legs: 'stand',
      armL: `${A(68, 60, 92, 74)}<rect x="88" y="58" width="26" height="34" rx="2" fill="#c9a26b"/><rect x="91" y="62" width="20" height="27" fill="#fff"/>
        <text x="93" y="72" font-size="9" fill="#389e0d" class="swp-check">✔</text><text x="93" y="84" font-size="9" fill="#389e0d" class="swp-check2">✔</text>`,
      armR: `<g class="swp-tick">${A(92, 60, 104, 72)}<rect x="102" y="62" width="3" height="12" fill="#333" transform="rotate(30 103 68)"/></g>` })
    case 'P04': return `<circle cx="134" cy="56" r="20" fill="#e8eef5" stroke="${MET}" stroke-width="3"/><circle cx="134" cy="56" r="2.5" fill="#333"/>
      <line class="swp-needle" x1="134" y1="56" x2="134" y2="40" stroke="#ff4d4f" stroke-width="2.5" stroke-linecap="round"/><rect x="131" y="76" width="6" height="40" fill="${MET}"/>`
      + person(c, { legs: 'stand', armL: hangL, armR: `${A(92, 60, 104, 70)}<rect x="98" y="58" width="16" height="22" rx="2" fill="#333"/><rect x="100" y="60" width="12" height="17" fill="#4BA8E8"/>` })
    case 'P05': return `<rect x="118" y="40" width="10" height="84" fill="${MET}"/><circle cx="123" cy="66" r="9" fill="#d9534f"/><rect x="118" y="62" width="10" height="8" fill="#a33"/>`
      + person(c, { hat: true, legs: 'stand', armL: hangL, armR: `<g class="swp-wrench">${A(92, 60, 108, 66)}<rect x="104" y="62" width="18" height="5" rx="2" fill="#ccc"/><circle cx="121" cy="64.5" r="4" fill="none" stroke="#ccc" stroke-width="3"/></g>` })
    case 'P06': return `<g class="swp-push">` + person(c, { armR: A(92, 62, 112, 72), armL: A(68, 62, 112, 74) })
      + `<rect x="112" y="66" width="44" height="40" rx="3" fill="#6c8bab"/><rect x="116" y="70" width="16" height="10" fill="#fff"/><rect x="136" y="70" width="16" height="10" fill="#bfe3ff"/><rect x="116" y="84" width="36" height="8" fill="#ffd6e7"/>
      <circle cx="118" cy="112" r="5" fill="#333"/><circle cx="150" cy="112" r="5" fill="#333"/></g>`
    case 'P07': return person(c, { bodyCls: 'swp-bob', armL: A(68, 60, 62, 82),
      armR: `${A(92, 60, 96, 86)}<rect x="86" y="86" width="26" height="16" rx="2" fill="#d9534f"/><rect x="94" y="82" width="10" height="5" rx="2" fill="none" stroke="#333" stroke-width="2"/>` })
    case 'P08': return `<rect x="100" y="12" width="40" height="10" rx="2" fill="${MET}"/><g class="swp-air"><path d="M108 26 v8 M120 26 v8 M132 26 v8" stroke="#bfe3ff" stroke-width="2"/></g>
      <path d="M40 124 L52 40 M64 124 L52 40" stroke="#b07a3a" stroke-width="4"/><path d="M44 104 h16 M46 88 h12 M48 72 h8" stroke="#b07a3a" stroke-width="3"/>`
      + person(c, { legs: 'stand', armL: A(68, 60, 60, 82), armR: `<g class="swp-reach">${A(92, 56, 104, 28)}<rect x="102" y="16" width="3" height="12" fill="#333"/></g>` })
    case 'P09': return `<rect x="108" y="96" width="34" height="24" rx="4" fill="#e8eef5"/><ellipse cx="125" cy="96" rx="19" ry="6" fill="#cfd8e3"/><rect x="134" y="66" width="12" height="30" rx="3" fill="#e8eef5"/>`
      + person(c, { legs: 'stand', armL: hangL, armR: `<g class="swp-plunge">${A(92, 60, 112, 72)}<rect x="113" y="64" width="4" height="30" fill="#8b5a2b"/><path d="M107 94 Q115 86 123 94 Z" fill="#c0392b"/></g>` })
    case 'P10': return `<rect x="96" y="8" width="44" height="6" fill="${MET}"/><circle class="swp-bulb" cx="118" cy="26" r="20" fill="#FFE58F" opacity=".35"/><circle cx="118" cy="24" r="8" fill="#FFE58F"/><rect x="114" y="14" width="8" height="5" fill="#999"/>`
      + person(c, { legs: 'stand', armL: hangL, armR: A(92, 56, 112, 30) })
    case 'P11': return `<rect x="124" y="20" width="12" height="104" fill="#8a6d4b"/><rect x="120" y="58" width="4" height="10" fill="#ccc"/>`
      + person(c, { legs: 'stand', armL: hangL, armR: `<g class="swp-hammer">${A(92, 58, 110, 62)}<rect x="108" y="48" width="4" height="22" fill="#8b5a2b"/><rect x="104" y="46" width="14" height="7" rx="1" fill="#777"/></g>` })
    case 'P12': return `<rect x="118" y="14" width="40" height="110" rx="2" fill="#5a7894"/><rect x="124" y="56" width="10" height="18" rx="2" fill="#222"/><circle class="swp-led" cx="129" cy="60" r="2.5" fill="#ff4d4f"/><circle cx="150" cy="68" r="3" fill="#d4b14a"/>`
      + person(c, { legs: 'stand', armL: hangL, armR: `${A(92, 60, 114, 64)}<rect x="112" y="58" width="8" height="12" rx="1" fill="#fff"/>` })
    case 'P13': return `<g class="swp-speed"><path d="M40 52 h18 M34 66 h22 M40 80 h16" stroke="#ff7875" stroke-width="3" stroke-linecap="round"/></g>`
      + person(c, { siren: true, bodyCls: 'swp-run', armR: A(92, 60, 106, 52), armL: A(68, 60, 56, 74) })
    case 'P14': return `<rect x="100" y="16" width="62" height="44" rx="2" fill="#f5f7fa" stroke="${MET}" stroke-width="3"/><path d="M108 30 h30 M108 40 h40 M108 50 h22" stroke="#4BA8E8" stroke-width="3"/><rect x="128" y="60" width="4" height="64" fill="${MET}"/>`
      + person(c, { legs: 'stand', armL: hangL, armR: `<g class="swp-point">${A(92, 56, 112, 56)}<line x1="112" y1="56" x2="132" y2="56" stroke="#333" stroke-width="2"/></g>` })
    case 'P15': return person(c, { bodyCls: 'swp-bob', armL: A(68, 60, 62, 82),
      armR: `${A(92, 60, 100, 76)}<rect x="94" y="70" width="20" height="24" rx="1" fill="#fff" stroke="#c9d3de"/><path d="M98 76 h12 M98 81 h12 M98 86 h8" stroke="#9fb3c8" stroke-width="2"/>` })
    default: return ''
  }
}

/** 是否為「離開桌子去現場」的樣式（P01 以外且有對應圖） */
export const isFieldPose = (pose?: string | null) => !!pose && pose !== 'P01' && !!POSE_LABEL[pose]

export function PoseArt({ pose, color, open }: { pose: string; color: string; open?: boolean }) {
  return (
    <svg viewBox="0 0 170 140" width={150} height={124} aria-hidden="true" className="swp">
      <ellipse cx="85" cy="128" rx="62" ry="5" fill="rgba(0,0,0,0.28)" />
      <circle className="swp-ring" cx="80" cy="38" r="15" fill="none" stroke={color} strokeWidth="2" />
      <g dangerouslySetInnerHTML={{ __html: art(pose, color) }} />
      {open && <circle className="swp-open" cx="96" cy="22" r="5" fill="#ff4d4f" />}
    </svg>
  )
}

export const POSE_CSS = `
.swp-walkL{animation:swpWalkL .7s ease-in-out infinite alternate;transform-origin:73px 92px}
.swp-walkR{animation:swpWalkR .7s ease-in-out infinite alternate;transform-origin:86px 92px}
.swp-sweep{animation:swpSweep 2.4s ease-in-out infinite;transform-origin:110px 66px}
.swp-bob{animation:swpBob .7s ease-in-out infinite}
.swp-tick{animation:swpTick 1.2s ease-in-out infinite;transform-origin:98px 62px}
.swp-check{animation:swpFade 2.4s steps(1) infinite}
.swp-check2{animation:swpFade2 2.4s steps(1) infinite}
.swp-needle{animation:swpNeedle 1.8s ease-in-out infinite alternate;transform-origin:134px 56px}
.swp-wrench{animation:swpWrench .9s ease-in-out infinite alternate;transform-origin:108px 66px}
.swp-push{animation:swpPush 1.6s ease-in-out infinite alternate}
.swp-reach{animation:swpReach 1.4s ease-in-out infinite alternate;transform-origin:92px 54px}
.swp-air{animation:swpAir 1.2s linear infinite}
.swp-plunge{animation:swpPlunge .5s ease-in-out infinite alternate}
.swp-bulb{animation:swpBulb 1.6s steps(1) infinite}
.swp-hammer{animation:swpHammer .45s ease-in infinite alternate;transform-origin:94px 58px}
.swp-led{animation:swpLed 2s steps(1) infinite}
.swp-siren{animation:swpSiren .5s steps(1) infinite}
.swp-run{animation:swpRun .35s ease-in-out infinite alternate}
.swp-speed{animation:swpSpeed .5s linear infinite}
.swp-point{animation:swpPoint 1.6s ease-in-out infinite alternate;transform-origin:92px 56px}
.swp-ring{animation:swpRing 1.6s ease-out infinite;transform-box:fill-box;transform-origin:center}
.swp-open{animation:swpSiren 1s ease-in-out infinite}
@keyframes swpWalkL{from{transform:rotate(-12deg)}to{transform:rotate(12deg)}}
@keyframes swpWalkR{from{transform:rotate(12deg)}to{transform:rotate(-12deg)}}
@keyframes swpSweep{0%,100%{transform:rotate(-10deg)}50%{transform:rotate(12deg)}}
@keyframes swpBob{50%{transform:translateY(-2px)}}
@keyframes swpTick{0%,100%{transform:rotate(0)}50%{transform:rotate(-14deg)}}
@keyframes swpFade{0%{opacity:0}35%{opacity:1}}
@keyframes swpFade2{0%{opacity:0}65%{opacity:1}}
@keyframes swpNeedle{from{transform:rotate(-50deg)}to{transform:rotate(40deg)}}
@keyframes swpWrench{from{transform:rotate(-25deg)}to{transform:rotate(20deg)}}
@keyframes swpPush{from{transform:translateX(-6px)}to{transform:translateX(6px)}}
@keyframes swpReach{from{transform:rotate(-8deg)}to{transform:rotate(8deg)}}
@keyframes swpAir{from{opacity:.9;transform:translateY(0)}to{opacity:0;transform:translateY(16px)}}
@keyframes swpPlunge{to{transform:translateY(8px)}}
@keyframes swpBulb{0%{opacity:.15}50%{opacity:1}}
@keyframes swpHammer{from{transform:rotate(-40deg)}to{transform:rotate(15deg)}}
@keyframes swpLed{0%{fill:#ff4d4f}55%{fill:#5BE49B}}
@keyframes swpSiren{0%{opacity:1}50%{opacity:.25}}
@keyframes swpRun{to{transform:translateY(-3px)}}
@keyframes swpSpeed{from{transform:translateX(0);opacity:.8}to{transform:translateX(-14px);opacity:0}}
@keyframes swpPoint{from{transform:rotate(-70deg)}to{transform:rotate(-95deg)}}
@keyframes swpRing{from{opacity:.8;transform:scale(.6)}to{opacity:0;transform:scale(1.6)}}
@media (prefers-reduced-motion:reduce){.swp *{animation:none!important}}
`

// ── 工作視角狀態（StaffWorkBoard／說明 Drawer 共用）──
export type WMode = 'work' | 'gap' | 'off' | 'after'
export const WMODE: Record<WMode, { label: string; color: string; order: number }> = {
  work:  { label: '工作中',     color: '#5BE49B', order: 0 },
  gap:   { label: '未取到值',   color: '#FFB547', order: 1 },
  off:   { label: '未開始',     color: '#8c9db0', order: 2 },
  after: { label: '無後續紀錄', color: '#7fb2e6', order: 3 },
}

// ── 一張桌子（SVG）─────────────────────────────────────────────────────────────
export function Desk({ color, mode, open }: { color: string; mode: WMode; open: boolean }) {
  return (
    <svg viewBox="0 -12 150 124" width={150} height={124} className={`swb-desk swb-${mode}`} aria-hidden="true">
      <ellipse cx="75" cy="106" rx="62" ry="5" fill="rgba(0,0,0,0.28)" />
      {/* 椅子 */}
      <rect x="55" y="66" width="40" height="8" rx="3" fill="#2b4058" />
      <rect x="70" y="74" width="10" height="24" fill="#2b4058" />
      {/* 人 */}
      <g className="swb-person">
        <circle className="swb-ring" cx="75" cy="20" r="14" fill="none" stroke={color} strokeWidth="2" />
        <g className="swb-head">
          <circle cx="75" cy="20" r="10" fill={color} />
          <circle cx="71" cy="18" r="1.4" fill="#0d1e30" /><circle cx="79" cy="18" r="1.4" fill="#0d1e30" />
        </g>
        <path className="swb-body" d="M60 56 Q60 32 75 32 Q90 32 90 56 Z" fill={color} opacity={0.85} />
        <rect className="swb-arm swb-arm-l" x="56" y="52" width="14" height="5" rx="2.5" fill={color} />
        <rect className="swb-arm swb-arm-r" x="80" y="52" width="14" height="5" rx="2.5" fill={color} />
        <text className="swb-q" x="94" y="10" fontSize="14" fontWeight="700" fill="#FFB547">?</text>
        {open && mode === 'work' && <circle className="swb-open" cx="89" cy="9" r="4.5" fill="#ff4d4f" />}
      </g>
      {/* 桌子＋螢幕 */}
      <rect x="18" y="58" width="114" height="10" rx="3" fill="#3a5470" />
      <rect x="22" y="68" width="6" height="34" fill="#3a5470" /><rect x="122" y="68" width="6" height="34" fill="#3a5470" />
      <rect className="swb-glow" x="40" y="24" width="34" height="30" rx="4" fill="#5BE49B" />
      <rect x="42" y="28" width="30" height="22" rx="2" fill="#4d6680" />
      <rect className="swb-screen" x="44" y="30" width="26" height="18" rx="1" />
      <g className="swb-code">
        <rect x="47" y="34" width="14" height="2" rx="1" fill="#5BE49B" />
        <rect x="47" y="38" width="19" height="2" rx="1" fill="#5BE49B" />
        <rect x="47" y="42" width="10" height="2" rx="1" fill="#5BE49B" />
      </g>
      <rect x="55" y="50" width="4" height="8" fill="#4d6680" />
      <rect x="96" y="52" width="14" height="6" rx="1" fill="#4d6680" />
    </svg>
  )
}


// ── 說明 Drawer 用：樣式清單與判斷順序（須與後端 work_journal_path._pose_of 一致）──
export const POSE_RULES: { id: string; group: string; rule: string; example: string }[] = [
  { id: 'P01', group: '通用',           rule: '預設：判斷不出工作類型',                         example: '其他未分類工作' },
  { id: 'P02', group: '巡檢',           rule: '來源＝整棟巡檢（機房／地下室）',                 example: 'B2F 巡檢、冷卻水塔' },
  { id: 'P03', group: '巡檢',           rule: '來源＝商場工務巡檢、飯店每日巡檢',               example: '商場 1F 設施巡檢' },
  { id: 'P04', group: '巡檢',           rule: '來源＝每日數值登錄表',                           example: '水電錶抄表' },
  { id: 'P05', group: '保養',           rule: '來源＝飯店／商場／全棟例行維護',                 example: '空調箱月保養、消防泵浦保養' },
  { id: 'P06', group: '保養',           rule: '來源＝IHG客房保養',                              example: '客房深度保養' },
  { id: 'P07', group: '報修',           rule: '報修，類型對不到 P08～P12',                      example: '消防、停車、專櫃…' },
  { id: 'P08', group: '報修',           rule: '報修類型＝空調',                                 example: '615 客反映空調太冷' },
  { id: 'P09', group: '報修',           rule: '報修類型＝衛廁、給排水',                         example: '701 浴缸開關閥蓋鬆掉、3F 男廁堵塞' },
  { id: 'P10', group: '報修',           rule: '報修類型＝機電、照明',                           example: '燈具不亮、配電' },
  { id: 'P11', group: '報修',           rule: '報修類型＝內裝、建築',                           example: '611 門擋片掉了、木皮脫落' },
  { id: 'P12', group: '報修',           rule: '內容含門鎖／房卡／讀卡／電子鎖，或類型＝弱電、監控', example: '628 更換門鎖電池' },
  { id: 'P13', group: '主管交辦／其他', rule: '主管交辦，屬性＝緊急事件',                       example: '漏水、跳電、受困電梯' },
  { id: 'P14', group: '主管交辦／其他', rule: '工作內容含 訓練／上課／會議／講習',             example: '新人訓練上課' },
  { id: 'P15', group: '主管交辦／其他', rule: '主管交辦，屬性＝上級交辦',                       example: '安排飯店保養工作表' },
]

export const RULE_ORDER: [string, string][] = [
  ['主管交辦，屬性＝緊急事件', 'P13'],
  ['工作內容含 訓練／上課／會議／講習（任何來源）', 'P14'],
  ['來源＝整棟巡檢', 'P02'],
  ['來源＝商場工務巡檢、飯店每日巡檢', 'P03'],
  ['來源＝每日數值登錄表', 'P04'],
  ['來源＝飯店／商場／全棟例行維護', 'P05'],
  ['來源＝IHG客房保養', 'P06'],
  ['報修：內容含 門鎖／房卡／讀卡／電子鎖', 'P12'],
  ['報修：類型＝空調', 'P08'],
  ['報修：類型＝衛廁、給排水', 'P09'],
  ['報修：類型＝機電、照明', 'P10'],
  ['報修：類型＝內裝、建築', 'P11'],
  ['報修：類型＝弱電、監控', 'P12'],
  ['報修：其他類型', 'P07'],
  ['主管交辦（上級交辦）', 'P15'],
  ['以上都不符合', 'P01'],
]
