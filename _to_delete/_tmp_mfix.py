import sys, os
p=os.path.join(sys.argv[1],'pages/Mobile/StockIssue.tsx'); s=open(p,encoding='utf-8').read()
def rep(a,b):
    global s
    if s.count(a)!=1: raise SystemExit(f"anchor {s.count(a)}: {a[:60]!r}")
    s=s.replace(a,b)
rep("""  const [avail, setAvail] = useState<AvailableItem[]>([])
""","""  const [avail, setAvail] = useState<AvailableItem[]>([])
  const [availFor, setAvailFor] = useState<number | undefined>()   // avail 是哪個倉的（避免用到還沒載入的清單）
""")
rep("""    if (!code || !whId) { setAvail([]); setTemplates([]); return }""","""    setAvailFor(undefined)
    if (!code || !whId) { setAvail([]); setTemplates([]); return }""")
rep("""    fetchAvailable(code, whId).then((r) => setAvail(r.data)).catch((e) => message.error(errMsg(e, '讀取料號失敗')))
      .finally(() => setLoadingAvail(false))""","""    fetchAvailable(code, whId).then((r) => { setAvail(r.data); setAvailFor(whId) })
      .catch((e) => message.error(errMsg(e, '讀取料號失敗')))
      .finally(() => setLoadingAvail(false))""")
rep("""    if (!ic || loadingAvail || !whId || !meta) return""","""    if (!ic || !whId || !meta || availFor !== whId) return""")
rep("""  }, [avail, loadingAvail, whId, meta, navigate])""","""  }, [avail, availFor, whId, meta, navigate])""")
open(p,'w',encoding='utf-8').write(s); print('ok')
s=open(p,encoding='utf-8').read()
a="      message.success(`已送出 ${r.data.doc_no}，等倉管發料`)"
assert s.count(a)==1
s=s.replace(a,"      message.success(`已送出 ${r.data.doc_no}，${r.data.status === 'pending_approval' ? '等主管核准' : '等倉管發料'}`)")
open(p,'w',encoding='utf-8').write(s); print('ok2')
