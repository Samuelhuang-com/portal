/**
 * OTA 主題字典維護
 * Route: /ota/topics    Permission: ota_topic_admin
 *
 * 規格書：`docs/SPEC_ota_reviews.md` §7.1
 *
 * 規則式主題分類的關鍵詞字典。改完之後要按「重新分析全部」才會套用到
 * 既有評論 —— 新評論會自動用新字典。
 *
 * ⚠️ 內建詞（`is_builtin`）**只能停用不能刪除**。停用是可逆的，刪除不是。
 *    這個限制在**後端** service 強制，前端 disabled 只是提示。
 */
import React, { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Alert, Button, Card, Col, Form, Input, InputNumber, Modal, Popconfirm, Row,
  Select, Space, Switch, Table, Tag, Tooltip, Typography, message,
} from 'antd'
import {
  BulbOutlined, CheckOutlined, CloseOutlined, PlusOutlined, ReloadOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'

import {
  acceptTopicCandidate, createTopicRule, deleteTopicRule, fetchTopicCandidates,
  fetchTopicRules, fetchTopicStats, rejectTopicCandidate, runAnalyze,
  updateTopicRule,
} from '@/api/ota'
import type { TopicCandidate, TopicRule, TopicStat } from '@/types/ota'

const { Text, Paragraph } = Typography

const POLARITY_META: Record<string, { color: string; label: string }> = {
  negative: { color: 'error', label: '負面' },
  positive: { color: 'success', label: '正面' },
  neutral: { color: 'default', label: '中性' },
}

const OtaTopicRulesPage: React.FC = () => {
  const [rules, setRules] = useState<TopicRule[]>([])
  const [stats, setStats] = useState<TopicStat[]>([])
  const [loading, setLoading] = useState(false)
  const [analyzing, setAnalyzing] = useState(false)
  const [topicFilter, setTopicFilter] = useState('')
  const [modalOpen, setModalOpen] = useState(false)
  const [saving, setSaving] = useState(false)
  const [form] = Form.useForm()

  // ⭐ AI 發現的字典外主題候選
  const [candidates, setCandidates] = useState<TopicCandidate[]>([])
  const [acceptTarget, setAcceptTarget] = useState<TopicCandidate | null>(null)
  const [acceptForm] = Form.useForm()

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [r, s, c] = await Promise.all([
        fetchTopicRules(), fetchTopicStats(), fetchTopicCandidates('pending'),
      ])
      setRules(r)
      setStats(s)
      setCandidates(c)
    } catch {
      message.error('載入主題字典失敗')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const topics = useMemo(
    () => [...new Set(rules.map((r) => r.topic))].sort(),
    [rules],
  )
  const shown = useMemo(
    () => (topicFilter ? rules.filter((r) => r.topic === topicFilter) : rules),
    [rules, topicFilter],
  )
  const statMap = useMemo(
    () => Object.fromEntries(stats.map((s) => [s.topic, s])),
    [stats],
  )

  /**
   * 採納候選 → 進字典。
   *
   * ⚠️ 開 Modal 讓管理員先改主題名與關鍵詞再送出 —— AI 給的名字會直接變成
   *    月度趨勢圖的圖例，事後改名要動到既有評論的 topics_json，成本很高。
   */
  const openAccept = (candidate: TopicCandidate) => {
    setAcceptTarget(candidate)
    acceptForm.setFieldsValue({
      topic: candidate.name,
      keywords: candidate.keywords,
      // 多數候選來自客訴，預設負面比較符合實際
      polarity: candidate.neg_count >= candidate.hit_count / 2 ? 'negative' : 'positive',
    })
  }

  const handleAccept = async () => {
    if (!acceptTarget) return
    try {
      const values = await acceptForm.validateFields()
      setSaving(true)
      const res = await acceptTopicCandidate(acceptTarget.id, values)
      message.success(`已收進字典：${res.topic}（新增 ${res.added} 個關鍵詞）`)
      setAcceptTarget(null)
      load()
    } catch (err) {
      if (err && typeof err === 'object' && 'errorFields' in err) return
      message.error('採納失敗')
    } finally {
      setSaving(false)
    }
  }

  const handleReject = async (candidate: TopicCandidate) => {
    try {
      await rejectTopicCandidate(candidate.id)
      message.success(`已否決「${candidate.name}」，之後不會再提示`)
      load()
    } catch {
      message.error('操作失敗')
    }
  }

  const handleCreate = async () => {
    const values = await form.validateFields()
    setSaving(true)
    try {
      await createTopicRule(values)
      message.success('已新增關鍵詞')
      setModalOpen(false)
      load()
    } catch (err) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      if (detail) message.error(detail)
      else if (!(err as { errorFields?: unknown }).errorFields) message.error('新增失敗')
    } finally {
      setSaving(false)
    }
  }

  const handleToggle = async (rule: TopicRule, enabled: boolean) => {
    try {
      await updateTopicRule(rule.id, { is_enabled: enabled })
      setRules((prev) => prev.map((r) => (r.id === rule.id ? { ...r, is_enabled: enabled } : r)))
    } catch {
      message.error('切換失敗')
    }
  }

  const handleWeight = async (rule: TopicRule, weight: number) => {
    try {
      await updateTopicRule(rule.id, { weight })
      setRules((prev) => prev.map((r) => (r.id === rule.id ? { ...r, weight } : r)))
    } catch {
      message.error('更新權重失敗')
    }
  }

  const handleDelete = async (rule: TopicRule) => {
    try {
      await deleteTopicRule(rule.id)
      message.success('已刪除')
      load()
    } catch (err) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      message.error(detail || '刪除失敗')
    }
  }

  const handleRerun = async () => {
    setAnalyzing(true)
    try {
      const res = await runAnalyze(true)
      message.info(res.message)
      window.setTimeout(() => { load(); setAnalyzing(false) }, 10000)
    } catch (err) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      message.error(detail || '觸發重新分析失敗')
      setAnalyzing(false)
    }
  }

  const columns: ColumnsType<TopicRule> = [
    {
      title: '主題', dataIndex: 'topic', width: 120,
      render: (topic: string) => {
        const s = statMap[topic]
        return (
          <Space size={4}>
            <b>{topic}</b>
            {s && s.negative_count > 0 && (
              <Tooltip title={`目前有 ${s.negative_count} 則負面提及、${s.positive_count} 則正面提及`}>
                <Tag color="error">{s.negative_count}</Tag>
              </Tooltip>
            )}
          </Space>
        )
      },
    },
    { title: '關鍵詞', dataIndex: 'keyword', width: 160 },
    {
      title: '極性', dataIndex: 'polarity', width: 90, align: 'center',
      render: (p: string) => {
        const meta = POLARITY_META[p] || POLARITY_META.neutral
        return <Tag color={meta.color}>{meta.label}</Tag>
      },
    },
    {
      title: '權重', dataIndex: 'weight', width: 90, align: 'center',
      render: (w: number, row) => (
        <InputNumber
          size="small" min={1} max={10} value={w} style={{ width: 64 }}
          onChange={(v) => v && handleWeight(row, v)}
        />
      ),
    },
    {
      title: '來源', dataIndex: 'is_builtin', width: 100, align: 'center',
      render: (builtin: boolean) => (
        builtin
          ? <Tooltip title="內建詞只能停用不能刪除 —— 停用是可逆的，刪除不是">
              <Tag>內建</Tag>
            </Tooltip>
          : <Tag color="blue">自訂</Tag>
      ),
    },
    {
      title: '啟用', dataIndex: 'is_enabled', width: 70, align: 'center',
      render: (enabled: boolean, row) => (
        <Switch size="small" checked={enabled} onChange={(v) => handleToggle(row, v)} />
      ),
    },
    {
      title: '操作', key: 'action', width: 90, align: 'center',
      render: (_, row) => (
        row.is_builtin
          ? <Tooltip title="內建詞不可刪除，請改用左側「啟用」開關停用">
              <Button size="small" danger disabled>刪除</Button>
            </Tooltip>
          : (
            <Popconfirm
              title="刪除這個關鍵詞？" onConfirm={() => handleDelete(row)}
              okText="刪除" cancelText="取消"
            >
              <Button size="small" danger>刪除</Button>
            </Popconfirm>
          )
      ),
    },
  ]

  return (
    <div>
      <Alert
        type="info" showIcon style={{ marginBottom: 16 }}
        message="改完字典要按「重新分析全部」才會套用到既有評論"
        description={
          <span>
            新進來的評論會自動用最新字典；**既有的**評論需要重跑一次才會更新主題標籤。
            重新分析<b>不會</b>覆蓋你在負評警示頁填的處理狀態與備註。
            <br />
            內建詞是系統預設的關鍵詞，<b>只能停用不能刪除</b> ——
            停用是可逆的，刪除不是。
          </span>
        }
      />

      {candidates.length > 0 && (
        <Card
          size="small"
          style={{ marginBottom: 16, borderColor: '#4BA8E8' }}
          title={
            <Space>
              <BulbOutlined style={{ color: '#4BA8E8' }} />
              <span>AI 發現了 {candidates.length} 個字典沒有的主題</span>
            </Space>
          }
        >
          <Paragraph type="secondary" style={{ fontSize: 13, marginBottom: 12 }}>
            這些是客人真的在談、但不在 12 個內建主題裡的議題。
            採納之後<b>規則層就抓得到</b>，同樣的評論下次不必再送 AI 判斷。
            <br />
            否決之後不會再提示（要反悔請找工程人員把狀態改回 pending）。
          </Paragraph>
          <Table<TopicCandidate>
            rowKey="id"
            size="small"
            pagination={false}
            dataSource={candidates}
            columns={[
              {
                title: '主題', dataIndex: 'name', width: 120,
                render: (v: string) => <b>{v}</b>,
              },
              {
                title: '出現次數', dataIndex: 'hit_count', width: 140,
                sorter: (a, b) => a.hit_count - b.hit_count,
                defaultSortOrder: 'descend',
                render: (v: number, row) => (
                  <Space size={4}>
                    <Text>{v} 則</Text>
                    {row.neg_count > 0 && (
                      <Tag color="error">負面 {row.neg_count}</Tag>
                    )}
                  </Space>
                ),
              },
              {
                title: 'AI 建議的關鍵詞', dataIndex: 'keywords',
                render: (v: string[]) => (
                  <Space size={4} wrap>
                    {v.length
                      ? v.map((k) => <Tag key={k}>{k}</Tag>)
                      : <Text type="secondary">—</Text>}
                  </Space>
                ),
              },
              {
                title: '樣本評論', dataIndex: 'sample_review_ids', width: 130,
                render: (v: number[]) => (
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    {v.length ? `#${v.slice(0, 3).join(', #')}` : '—'}
                  </Text>
                ),
              },
              {
                title: '操作', width: 150, align: 'right',
                render: (_, row) => (
                  <Space size={4}>
                    <Button
                      type="primary" size="small" icon={<CheckOutlined />}
                      onClick={() => openAccept(row)}
                    >
                      採納
                    </Button>
                    <Popconfirm
                      title={`否決「${row.name}」？`}
                      description="之後不會再提示這個主題"
                      onConfirm={() => handleReject(row)}
                      okText="否決" cancelText="取消"
                    >
                      <Button size="small" icon={<CloseOutlined />} />
                    </Popconfirm>
                  </Space>
                ),
              },
            ]}
          />
        </Card>
      )}

      <Card
        size="small"
        title={
          <Space>
            <span>主題關鍵字字典</span>
            <Text type="secondary" style={{ fontWeight: 400, fontSize: 13 }}>
              共 {rules.length} 筆／{topics.length} 個主題
            </Text>
          </Space>
        }
        extra={
          <Space>
            <Select
              value={topicFilter} onChange={setTopicFilter} style={{ width: 140 }}
              options={[{ value: '', label: '全部主題' },
                ...topics.map((t) => ({ value: t, label: t }))]}
            />
            <Button icon={<ReloadOutlined />} onClick={load} loading={loading}>重新整理</Button>
            <Tooltip title="用最新字典重跑所有評論（背景執行，可能要幾分鐘）">
              <Button
                icon={<ThunderboltOutlined />} onClick={handleRerun} loading={analyzing}
              >
                重新分析全部
              </Button>
            </Tooltip>
            <Button
              type="primary" icon={<PlusOutlined />}
              onClick={() => {
                form.setFieldsValue({
                  topic: topicFilter || '', keyword: '',
                  polarity: 'negative', weight: 1, is_enabled: true,
                })
                setModalOpen(true)
              }}
            >
              新增關鍵詞
            </Button>
          </Space>
        }
      >
        <Table<TopicRule>
          rowKey="id" size="small" loading={loading}
          columns={columns} dataSource={shown}
          pagination={{ pageSize: 50, showSizeChanger: true, showTotal: (t) => `共 ${t} 筆` }}
        />
      </Card>

      <Modal
        open={modalOpen} title="新增關鍵詞"
        onCancel={() => setModalOpen(false)} onOk={handleCreate}
        confirmLoading={saving} okText="新增" cancelText="取消" destroyOnClose
      >
        <Paragraph type="secondary" style={{ fontSize: 13 }}>
          比對時會忽略標點、空白與全半形差異，所以「隔音差」也能比對到「隔音，差！」。
          不需要為了標點變化多建幾筆。
        </Paragraph>
        <Form form={form} layout="vertical" preserve={false}>
          <Form.Item
            name="topic" label="主題"
            rules={[{ required: true, message: '請輸入或選擇主題' }]}
            extra="沿用既有主題可以讓統計集中；新主題會自動出現在分佈圖上"
          >
            <Select
              showSearch
              options={topics.map((t) => ({ value: t, label: t }))}
              placeholder="例如：清潔"
            />
          </Form.Item>
          <Form.Item
            name="keyword" label="關鍵詞"
            rules={[{ required: true, message: '請輸入關鍵詞' }]}
          >
            <Input placeholder="例如：地毯有汙漬" />
          </Form.Item>
          <Form.Item
            name="polarity" label="極性"
            extra="同一主題正負詞都命中時，以出現在「負評」欄位的為準"
          >
            <Select options={[
              { value: 'negative', label: '負面（客人在抱怨）' },
              { value: 'positive', label: '正面（客人在稱讚）' },
              { value: 'neutral', label: '中性' },
            ]} />
          </Form.Item>
          <Row gutter={12}>
            <Col span={12}>
              <Form.Item name="weight" label="權重">
                <InputNumber min={1} max={10} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="is_enabled" label="啟用" valuePropName="checked">
                <Switch />
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>
      <Modal
        title={`採納主題「${acceptTarget?.name ?? ''}」`}
        open={acceptTarget !== null}
        onCancel={() => setAcceptTarget(null)}
        onOk={handleAccept}
        confirmLoading={saving}
        okText="寫進字典"
        cancelText="取消"
      >
        <Alert
          type="warning" showIcon style={{ marginBottom: 16 }}
          message="主題名稱會出現在月度趨勢圖的圖例上"
          description="事後改名要一併更新既有評論的主題標籤，成本很高。現在就把它改成你想看到的樣子。"
        />
        <Form form={acceptForm} layout="vertical">
          <Form.Item
            name="topic" label="主題名稱"
            rules={[{ required: true, message: '請輸入主題名稱' },
                    { max: 30, message: '最多 30 字' }]}
          >
            <Input placeholder="例如：電梯" />
          </Form.Item>
          <Form.Item
            name="keywords" label="關鍵詞"
            extra="客人實際會寫的詞。系統會自動比對簡體字形與「很／太／超」等程度副詞的變體，不必自己列。"
            rules={[{ required: true, message: '至少要有一個關鍵詞' }]}
          >
            <Select mode="tags" tokenSeparators={[',', '，']} placeholder="輸入後按 Enter" />
          </Form.Item>
          <Form.Item name="polarity" label="極性">
            <Select
              options={[
                { value: 'negative', label: '負面（命中就是抱怨）' },
                { value: 'positive', label: '正面（命中就是稱讚）' },
                { value: 'neutral', label: '中性' },
              ]}
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default OtaTopicRulesPage
