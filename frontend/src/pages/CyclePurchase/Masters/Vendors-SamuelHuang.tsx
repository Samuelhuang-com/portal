/**
 * 週期採購 — 供應商主檔維護
 *
 * 2026-07-10 決策：週期採購自建獨立供應商主檔，不與合約模組的 Vendors 共用。
 * 2026-08-10 修訂：改為「單向鏡像同步」——合約模組的廠商主檔是唯一真實來源
 * （其上游是 Ragic 廠商資料表），本頁只是它在 cycle-purchase.db 的副本。
 *
 * 因此本頁的列分兩種：
 *   - 同步（source_vendor_id 非空）：代碼／名稱／統編／聯絡人／電話唯讀，
 *     要改請到「合約管理 → 廠商主檔」或 Ragic 改；付款條件／備註／啟用狀態
 *     仍屬週採自維護，可以編輯。
 *   - 本地自建（source_vendor_id 為 null）：全部欄位可編，同步不會覆蓋。
 *
 * 唯讀限制後端也有擋（cycle_purchase_service.update_vendor），這裡的 disabled
 * 只是提示用途。
 *
 * 2026-09-20 新增「對照合約廠商」欄位（見 CHANGELOG [2.10.41]）：
 * 週採 204 家供應商裡有 32 家是當初匯入料號時直接用**簡稱**建的孤兒
 * （CPV-NNNN、source_vendor_id 空、統編也空）。拋轉 Ragic 時主表「廠商(一)」
 * 是**連結到廠商資料表的 Link 欄位、只認全名**——Portal 送「北金」，
 * Ragic 只認「北金文具印刷有限公司」，對不上就**靜默丟掉還回 SUCCESS**，
 * 單子上的廠商欄是空的。
 *
 * ⚠️ 光按「自合約模組同步」解決不了：它的比對是
 * source_vendor_id → 統一編號 → 名稱完全相同，這 32 家三層全部落空，
 * 同步會**另外新增**一筆全名的供應商，而料號對照仍指著舊的簡稱那筆
 * ——變成兩個「北金」。所以要先在這一欄把既有的那筆接上去，再按同步。
 */
import { useEffect, useMemo, useState } from 'react'
import {
  Alert, Button, Card, Checkbox, Form, Input, Modal, Popconfirm, Select, Space, Switch,
  Table, Tag, Tooltip, Typography, message,
} from 'antd'
import { PlusOutlined, EditOutlined, StopOutlined, CheckCircleOutlined, SyncOutlined, CloudDownloadOutlined, MergeCellsOutlined } from '@ant-design/icons'
import {
  createVendor, getContractVendors, getVendors, linkVendorToContract, mergeVendor,
  syncVendorsFromContract, updateVendor,
} from '@/api/cyclePurchase'
import type { CpContractVendor, CpVendor, CpVendorMergeResult } from '@/types/cyclePurchase'

const { Title } = Typography

/** 是否為「鏡像自合約模組」的供應商 */
const isSynced = (v: CpVendor | null): boolean => !!v?.source_vendor_id

export default function CpVendorsPage() {
  const [vendors, setVendors] = useState<CpVendor[]>([])
  const [loading, setLoading] = useState(false)
  const [syncing, setSyncing] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<CpVendor | null>(null)
  const [form] = Form.useForm()
  // 2026-09-20：對照合約廠商用
  const [contractVendors, setContractVendors] = useState<CpContractVendor[]>([])
  const [unlinkedOnly, setUnlinkedOnly] = useState(false)
  const [linkingId, setLinkingId] = useState<number | null>(null)

  const load = () => {
    setLoading(true)
    getVendors({ unlinked_only: unlinkedOnly || undefined })
      .then((r) => setVendors(r.data))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [unlinkedOnly])
  useEffect(() => { getContractVendors().then((r) => setContractVendors(r.data)) }, [])

  const contractOptions = useMemo(
    () => contractVendors.map((v) => ({
      label: v.tax_id ? `${v.vendor_name}（${v.tax_id}）` : v.vendor_name,
      value: v.vendor_id,
    })),
    [contractVendors],
  )

  // ── 合併供應商（2026-09-20）────────────────────────────────────────────
  // 32 家孤兒裡有 15 家與正本重複（「北金」vs「北金文具印刷有限公司」），
  // 「對照」解不了（目標已被正本佔走會 409），要把參照搬過去再停用孤兒。
  const [mergeSource, setMergeSource] = useState<CpVendor | null>(null)
  const [mergeTarget, setMergeTarget] = useState<number | undefined>()
  const [mergePreview, setMergePreview] = useState<CpVendorMergeResult | null>(null)
  const [merging, setMerging] = useState(false)

  // 合併目標只列「已對照合約主檔」的供應商 —— 併到另一個孤兒身上沒有意義，
  // 問題（Ragic 認不得的名稱）不會消失。
  const mergeTargetOptions = useMemo(
    () => vendors
      .filter((v) => v.source_vendor_id && v.id !== mergeSource?.id)
      .map((v) => ({ label: v.vendor_name, value: v.id })),
    [vendors, mergeSource],
  )

  const openMerge = (v: CpVendor) => {
    setMergeSource(v)
    setMergeTarget(undefined)
    setMergePreview(null)
  }

  // 先試算：這支會動到歷史資料（料號對照、既有彙整列），不該按了才知道搬了什麼
  const previewMerge = async (targetId: number) => {
    if (!mergeSource) return
    setMergeTarget(targetId)
    setMergePreview(null)
    try {
      const r = await mergeVendor(mergeSource.id, targetId, true)
      setMergePreview(r.data)
    } catch (err: any) {
      message.error(err?.response?.data?.detail || '試算失敗')
    }
  }

  const doMerge = async () => {
    if (!mergeSource || !mergeTarget) return
    setMerging(true)
    try {
      const r = await mergeVendor(mergeSource.id, mergeTarget, false)
      message.success(`已把「${r.data.source_name}」併入「${r.data.target_name}」，搬動 ${r.data.total_moved} 筆參照`)
      setMergeSource(null)
      load()
    } catch (err: any) {
      message.error(err?.response?.data?.detail || '合併失敗')
    } finally {
      setMerging(false)
    }
  }

  const handleLink = async (v: CpVendor, sourceVendorId: string | null) => {
    setLinkingId(v.id)
    try {
      await linkVendorToContract(v.id, sourceVendorId)
      message.success(sourceVendorId
        ? '已對照。請按「自合約模組同步」，名稱才會更新成合約主檔的全名'
        : '已解除對照')
      load()
    } catch (err: any) {
      message.error(err?.response?.data?.detail || '對照失敗')
    } finally {
      setLinkingId(null)
    }
  }

  const toggleActive = async (v: CpVendor) => {
    try {
      await updateVendor(v.id, { is_active: !v.is_active })
      message.success(v.is_active ? '已停用' : '已啟用')
      load()
    } catch (err: any) {
      message.error(err?.response?.data?.detail || '操作失敗')
    }
  }

  /**
   * 自合約模組把廠商主檔同步過來。同步等待（不是背景執行），完成後直接把
   * 這次的異動統計顯示出來——使用者按下去就知道到底同步了什麼，
   * 不用再跑到「設定 → Ragic 連線」看紀錄。
   */
  const handleSync = async () => {
    setSyncing(true)
    try {
      const { data } = await syncVendorsFromContract()
      message.success(
        `同步完成：合約模組共 ${data.fetched} 家，新增 ${data.created} 家、`
        + `更新 ${data.updated} 家、無異動 ${data.unchanged} 家`,
      )
      if (data.skipped > 0) {
        Modal.warning({
          title: `有 ${data.skipped} 家廠商被略過`,
          width: 560,
          content: (
            <div>
              {data.warnings.map((w, i) => <p key={i} style={{ marginBottom: 8 }}>{w}</p>)}
            </div>
          ),
        })
      }
      load()
    } catch (err: any) {
      message.error(err?.response?.data?.detail || '同步失敗')
    } finally {
      setSyncing(false)
    }
  }

  const openCreate = () => {
    setEditing(null)
    form.resetFields()
    form.setFieldsValue({ is_active: true })
    setModalOpen(true)
  }

  const openEdit = (v: CpVendor) => {
    setEditing(v)
    // 先清空再填，避免上一次開啟殘留的欄位值被誤送出
    form.resetFields()
    form.setFieldsValue(v)
    setModalOpen(true)
  }

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields()
      // validateFields() 會回傳整個 form store，而 openEdit 的 setFieldsValue(v)
      // 連 id / created_at / source_vendor_id 都塞了進去。用白名單只挑表單欄位
      // 送出（後端 VendorUpdate 目前會忽略多餘欄位，但不該依賴這件事）。
      const payload = {
        vendor_code: values.vendor_code,
        vendor_name: values.vendor_name,
        tax_id: values.tax_id,
        contact_name: values.contact_name,
        contact_phone: values.contact_phone,
        payment_terms: values.payment_terms,
        notes: values.notes,
        is_active: values.is_active,
      }
      if (editing) {
        await updateVendor(editing.id, payload)
        message.success('更新成功')
      } else {
        await createVendor(payload)
        message.success('新增成功')
      }
      setModalOpen(false)
      load()
    } catch (err: any) {
      const detail = err?.response?.data?.detail
      if (detail) message.error(detail)
    }
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>週期採購 — 供應商主檔</Title>
        <Space>
          <Checkbox
            checked={unlinkedOnly}
            onChange={(e) => setUnlinkedOnly(e.target.checked)}
          >
            只看未對照
            {!unlinkedOnly && `（${vendors.filter((v) => !v.source_vendor_id).length}）`}
          </Checkbox>
          <Button
            icon={<CloudDownloadOutlined />}
            loading={syncing}
            onClick={handleSync}
          >
            自合約模組同步
          </Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新增供應商</Button>
        </Space>
      </div>

      <Alert
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
        message="廠商資料來源：合約管理 → 廠商主檔（上游為 Ragic 廠商資料表）"
        description={(
          <>
            標示「同步」的供應商，其代碼／名稱／統編／聯絡人／電話由來源端維護，在此為唯讀；付款條件、備註、啟用狀態則屬週期採購自行維護，可直接編輯。要新增或修改廠商基本資料，請到合約管理或 Ragic 操作後，回到這裡按「自合約模組同步」。
            <br />
            <strong>⚠️ 標示「本地自建」的供應商，拋轉 Ragic 時廠商欄會是空的。</strong>
            Ragic 請購單的「廠商(一)」是連結到廠商資料表的欄位、<strong>只認全名</strong>（例：Ragic 只認「北金文具印刷有限公司」，不認「北金」），對不上就會被 Ragic 靜默丟掉而且照樣回成功。請用右邊的「對應合約廠商」把它接到合約主檔，<strong>接好後按一次「自合約模組同步」</strong>，名稱才會換成全名。
          </>
        )}
      />

      <Card>
        <Table
          dataSource={vendors}
          rowKey="id"
          loading={loading}
          size="small"
          pagination={false}
          columns={[
            {
              title: '來源',
              key: 'source',
              width: 90,
              render: (_: unknown, r: CpVendor) => (isSynced(r)
                ? <Tag icon={<SyncOutlined />} color="blue">同步</Tag>
                : (
                  <Tooltip title="尚未對照到合約廠商：拋轉 Ragic 時「廠商(一)」會是空的">
                    <Tag color="orange">未對照</Tag>
                  </Tooltip>
                )),
            },
            { title: '代碼', dataIndex: 'vendor_code', width: 100 },
            { title: '供應商名稱', dataIndex: 'vendor_name' },
            { title: '統編', dataIndex: 'tax_id', width: 110 },
            { title: '聯絡人', dataIndex: 'contact_name', width: 100 },
            { title: '聯絡電話', dataIndex: 'contact_phone', width: 120 },
            { title: '付款條件', dataIndex: 'payment_terms', width: 120 },
            {
              // 2026-09-20：拋轉 Ragic 的廠商欄靠這個對照才填得進去（見檔頭說明）
              title: '對應合約廠商',
              key: 'source',
              width: 300,
              render: (_: unknown, r: CpVendor) => (
                <Select
                  style={{ width: '100%' }}
                  size="small"
                  allowClear
                  showSearch
                  optionFilterProp="label"
                  placeholder="未對照 — 拋轉時廠商會是空的"
                  status={r.source_vendor_id ? undefined : 'warning'}
                  loading={linkingId === r.id}
                  disabled={linkingId === r.id}
                  value={r.source_vendor_id ?? undefined}
                  options={contractOptions}
                  onChange={(v) => handleLink(r, v ?? null)}
                />
              ),
            },
            {
              title: '狀態',
              dataIndex: 'is_active',
              width: 80,
              render: (v: boolean) => (v ? <Tag color="green">啟用</Tag> : <Tag color="default">停用</Tag>),
            },
            {
              title: '操作',
              key: 'actions',
              width: 160,
              render: (_: unknown, r: CpVendor) => (
                <Space>
                  <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(r)}>編輯</Button>
                  {!r.source_vendor_id && (
                    <Tooltip title="這筆與某個已對照的供應商重複時，把參照搬過去並停用這筆">
                      <Button size="small" icon={<MergeCellsOutlined />} onClick={() => openMerge(r)}>合併</Button>
                    </Tooltip>
                  )}
                  <Popconfirm
                    title={r.is_active ? '確定停用此供應商？' : '確定啟用此供應商？'}
                    onConfirm={() => toggleActive(r)}
                    okText="確定"
                    cancelText="取消"
                  >
                    <Button size="small" danger={r.is_active} icon={r.is_active ? <StopOutlined /> : <CheckCircleOutlined />}>
                      {r.is_active ? '停用' : '啟用'}
                    </Button>
                  </Popconfirm>
                </Space>
              ),
            },
          ]}
        />
      </Card>

      <Modal
        title={editing ? '編輯供應商' : '新增供應商'}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={() => setModalOpen(false)}
        okText="儲存"
        cancelText="取消"
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          {isSynced(editing) && (
            <Alert
              type="warning"
              showIcon
              style={{ marginBottom: 16 }}
              message={`此供應商鏡像自合約模組（${editing?.source_vendor_id}）`}
              description="上方欄位由來源端維護，在此修改無效（下次同步會被覆蓋）。僅付款條件、備註、啟用狀態可在週期採購維護。"
            />
          )}
          <Form.Item name="vendor_code" label="供應商代碼" rules={[{ required: true }]}>
            <Input disabled={!!editing} />
          </Form.Item>
          <Form.Item name="vendor_name" label="供應商名稱" rules={[{ required: true }]}>
            <Input disabled={isSynced(editing)} />
          </Form.Item>
          <Form.Item name="tax_id" label="統一編號">
            <Input disabled={isSynced(editing)} />
          </Form.Item>
          <Form.Item name="contact_name" label="聯絡人">
            <Input disabled={isSynced(editing)} />
          </Form.Item>
          <Form.Item name="contact_phone" label="聯絡電話">
            <Input disabled={isSynced(editing)} />
          </Form.Item>
          <Form.Item name="payment_terms" label="付款條件">
            <Input />
          </Form.Item>
          <Form.Item name="notes" label="備註">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item name="is_active" label="是否啟用" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>

      {/* 合併供應商（2026-09-20）：先試算再執行，因為會改動歷史資料 */}
      <Modal
        title={mergeSource ? `合併供應商 — ${mergeSource.vendor_name}` : '合併供應商'}
        open={!!mergeSource}
        onCancel={() => setMergeSource(null)}
        onOk={doMerge}
        okText={mergePreview ? `確定合併（搬動 ${mergePreview.total_moved} 筆）` : '確定合併'}
        okButtonProps={{ danger: true, disabled: !mergePreview, loading: merging }}
        cancelText="取消"
        width={620}
      >
        <Alert
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
          message="這個動作會改動歷史資料"
          description={(
            <>
              料號對照、既有彙整列、採購單裡指向「{mergeSource?.vendor_name}」的參照，會全部改指到你選的供應商。
              <br />
              來源這筆會被<strong>停用</strong>（不是刪除，可以再啟用）。請先選目標看試算結果再確定。
            </>
          )}
        />
        <div style={{ marginBottom: 8 }}>併入哪一筆？（只列已對照合約主檔的供應商）</div>
        <Select
          style={{ width: '100%' }}
          showSearch
          optionFilterProp="label"
          placeholder="選擇正確的那一筆供應商"
          value={mergeTarget}
          options={mergeTargetOptions}
          onChange={previewMerge}
        />
        {mergePreview && (
          <div style={{ marginTop: 16 }}>
            <div style={{ marginBottom: 8 }}>
              試算：<strong>{mergePreview.source_name}</strong> → <strong>{mergePreview.target_name}</strong>
            </div>
            <Table
              size="small"
              rowKey="k"
              pagination={false}
              dataSource={Object.entries(mergePreview.moved).map(([k, v]) => ({ k, v }))}
              columns={[
                { title: '會搬動的資料', dataIndex: 'k' },
                { title: '筆數', dataIndex: 'v', width: 90, align: 'right' as const },
              ]}
            />
            {mergePreview.total_moved === 0 && (
              <Alert
                type="info"
                showIcon
                style={{ marginTop: 12 }}
                message="這筆供應商沒有任何資料參照它，合併只會把它停用"
              />
            )}
          </div>
        )}
      </Modal>

    </div>
  )
}
