import sys, os
p=os.path.join(sys.argv[1],'pages/Stock/Issues/QrLabels.tsx'); s=open(p,encoding='utf-8').read()
def rep(a,b):
    global s
    if s.count(a)!=1: raise SystemExit(f"anchor {s.count(a)}: {a[:60]!r}")
    s=s.replace(a,b)
rep("""  const [base, setBase] = useState(readBase)
  const [printing, setPrinting] = useState(false)
""","""  const [base, setBase] = useState(readBase)
""")
rep("""    try { localStorage.setItem(BASE_KEY, base) } catch { /* ignore */ }
    setPrinting(true)
    // 等標籤 DOM（含 QR）畫出來再叫列印
    setTimeout(() => { window.print(); setPrinting(false) }, 300)
  }""","""    try { localStorage.setItem(BASE_KEY, base) } catch { /* ignore */ }
    // 標籤在視窗開著時就已畫好（螢幕上隱藏、只在列印時顯示），不依賴 window.print 是否同步（Safari 為非同步）
    window.print()
  }""")
rep("""          {printing && whId && (""","""          {whId && !badBase && (""")
open(p,'w',encoding='utf-8').write(s); print('ok qr')
