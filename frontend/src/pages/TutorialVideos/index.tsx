/**
 * 影音教學頁面
 * 路由：/tutorial-videos
 *
 * 本地模組（不對接 Ragic）：影片檔案直接存於後端伺服器本機檔案系統。
 * 觀看：所有登入使用者　／　模組與影片的新增、編輯、刪除、排序：需 tutorial_videos_manage 權限
 *
 * 資料結構：TutorialVideoModule（教學模組主檔，如「IHG客房保養」）1 對多 TutorialVideo（單集影片）。
 * 模組順序、模組內集數順序皆可用滑鼠拖曳排序（比照 MenuConfig 頁面的 dnd-kit 用法）。
 */
import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Button, Card, Empty, Form, Input, Modal, Popconfirm, Segmented, Space,
  Tabs, Tag, Typography, Upload, message,
} from 'antd'
import {
  DeleteOutlined, DownloadOutlined, EditOutlined, HolderOutlined,
  PlayCircleOutlined, PlusOutlined, RightOutlined, UploadOutlined, VideoCameraOutlined,
} from '@ant-design/icons'
import type { UploadFile } from 'antd/es/upload/interface'
import {
  DndContext, closestCenter, PointerSensor, useSensor, useSensors,
  type DragEndEvent,
} from '@dnd-kit/core'
import {
  SortableContext, useSortable, verticalListSortingStrategy, arrayMove,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { useAuthStore } from '@/stores/authStore'
import {
  createTutorialVideoModule, deleteTutorialVideoModule, fetchTutorialVideoModules,
  reorderTutorialVideoModules, updateTutorialVideoModule,
} from '@/api/tutorialVideoModules'
import {
  deleteTutorialVideo, fetchTutorialVideos, reorderTutorialVideos,
  tutorialVideoScriptUrl, tutorialVideoStreamUrl, updateTutorialVideo, uploadTutorialVideo,
} from '@/api/tutorialVideos'
import { downloadFile } from '@/api/downloadFile'
import type {
  TutorialVideoCategory, TutorialVideoItem, TutorialVideoModuleItem,
} from '@/types/tutorial_video'

const { Title, Text } = Typography

const CATEGORY_TABS: { key: TutorialVideoCategory; label: string }[] = [
  { key: 'hotel', label: '飯店管理' },
  { key: 'mall',  label: '商場管理' },
  { key: 'group', label: '集團決策' },
]

function formatSize(bytes: number): string {
  if (!bytes) return '—'
  const mb = bytes / (1024 * 1024)
  return mb >= 1 ? `${mb.toFixed(1)} MB` : `${(bytes / 1024).toFixed(0)} KB`
}

/** 從 axios 錯誤中擷取後端實際回傳的訊息，讀不到才用預設文字（避免吞掉真正的失敗原因） */
function extractApiError(err: any, fallback: string): string {
  const detail = err?.response?.data?.detail
  if (typeof detail === 'string' && detail) return detail
  if (err?.code === 'ECONNABORTED') return `${fallback}（連線逾時，可能是檔案過大或網路不穩）`
  if (err?.message === 'Network Error') return `${fallback}（網路連線失敗，請確認伺服器是否正常）`
  return fallback
}

// ── 單集影片列（可拖曳） ──────────────────────────────────────────────────────
interface VideoRowProps {
  item: TutorialVideoItem
  canManage: boolean
  onPlay: (item: TutorialVideoItem) => void
  onEdit: (item: TutorialVideoItem) => void
  onDelete: (item: TutorialVideoItem) => void
}

function VideoRow({ item, canManage, onPlay, onEdit, onDelete }: VideoRowProps) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: item.id })
  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  }
  return (
    <div ref={setNodeRef} style={style}>
      <Card size="small" hoverable style={{ marginBottom: 8 }}>
        <Space align="start" style={{ width: '100%', justifyContent: 'space-between' }}>
          <Space align="start">
            {canManage && (
              <span {...attributes} {...listeners} style={{ cursor: 'grab', color: '#bbb', paddingTop: 3 }} title="拖曳調整順序">
                <HolderOutlined />
              </span>
            )}
            <Space direction="vertical" size={2} style={{ cursor: 'pointer' }} onClick={() => onPlay(item)}>
              <Space>
                {item.episode && <Tag color="geekblue">{item.episode}</Tag>}
                <Text strong>{item.title}</Text>
              </Space>
              {item.description && (
                <Text type="secondary" style={{ fontSize: 12 }}>{item.description}</Text>
              )}
              <Text type="secondary" style={{ fontSize: 12 }}>
                {item.video_orig_name}（{formatSize(item.video_size_bytes)}）· 上傳者：{item.uploaded_by || '—'}
              </Text>
            </Space>
          </Space>
          <Space>
            <Button type="primary" size="small" icon={<PlayCircleOutlined />} onClick={() => onPlay(item)}>
              播放
            </Button>
            {item.script_orig_name && (
              <Button
                size="small"
                icon={<DownloadOutlined />}
                onClick={() => downloadFile(tutorialVideoScriptUrl(item.id), item.script_orig_name)}
              >
                逐字稿
              </Button>
            )}
            {canManage && (
              <>
                <Button size="small" icon={<EditOutlined />} onClick={() => onEdit(item)} />
                <Popconfirm title="確定要刪除這支教學影片嗎？" onConfirm={() => onDelete(item)}>
                  <Button size="small" danger icon={<DeleteOutlined />} />
                </Popconfirm>
              </>
            )}
          </Space>
        </Space>
      </Card>
    </div>
  )
}

// ── 模組區塊（可拖曳，內含集數列表） ──────────────────────────────────────────
interface ModuleBlockProps {
  module: TutorialVideoModuleItem
  videos: TutorialVideoItem[]
  canManage: boolean
  expanded: boolean
  onToggle: () => void
  onEditModule: (m: TutorialVideoModuleItem) => void
  onDeleteModule: (m: TutorialVideoModuleItem) => void
  onUploadToModule: (m: TutorialVideoModuleItem) => void
  onPlay: (item: TutorialVideoItem) => void
  onEditVideo: (item: TutorialVideoItem) => void
  onDeleteVideo: (item: TutorialVideoItem) => void
}

function ModuleBlock({
  module, videos, canManage, expanded, onToggle,
  onEditModule, onDeleteModule, onUploadToModule,
  onPlay, onEditVideo, onDeleteVideo,
}: ModuleBlockProps) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: module.id })
  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.6 : 1,
  }
  const videoIds = videos.map((v) => v.id)

  return (
    <div ref={setNodeRef} style={style}>
      <Card size="small" style={{ marginBottom: 12 }} bodyStyle={{ padding: 12 }}>
        <Space
          style={{ width: '100%', justifyContent: 'space-between', cursor: 'pointer' }}
          onClick={onToggle}
        >
          <Space onClick={(e) => e.stopPropagation()}>
            {canManage && (
              <span {...attributes} {...listeners} style={{ cursor: 'grab', color: '#bbb' }} title="拖曳調整模組順序">
                <HolderOutlined />
              </span>
            )}
            <span onClick={onToggle} style={{ cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: 8 }}>
              <RightOutlined rotate={expanded ? 90 : 0} style={{ fontSize: 11, color: '#999', transition: 'transform 0.2s' }} />
              <Text strong>{module.module_name}</Text>
              <Tag>{module.video_count} 集</Tag>
              {module.module_route && (
                <Text type="secondary" style={{ fontSize: 12 }}>{module.module_route}</Text>
              )}
            </span>
          </Space>
          {canManage && (
            <Space onClick={(e) => e.stopPropagation()}>
              <Button size="small" icon={<PlusOutlined />} onClick={() => onUploadToModule(module)}>
                新增集數
              </Button>
              <Button size="small" icon={<EditOutlined />} onClick={() => onEditModule(module)} />
              <Popconfirm
                title="確定要刪除此模組？"
                description="模組內所有集數與影片檔案將一併刪除，無法復原。"
                onConfirm={() => onDeleteModule(module)}
              >
                <Button size="small" danger icon={<DeleteOutlined />} />
              </Popconfirm>
            </Space>
          )}
        </Space>

        {expanded && (
          <div style={{ marginTop: 12 }}>
            {videos.length === 0 ? (
              <Empty description="此模組尚無影片" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            ) : (
              <SortableContext items={videoIds} strategy={verticalListSortingStrategy}>
                {videos.map((v) => (
                  <VideoRow
                    key={v.id}
                    item={v}
                    canManage={canManage}
                    onPlay={onPlay}
                    onEdit={onEditVideo}
                    onDelete={onDeleteVideo}
                  />
                ))}
              </SortableContext>
            )}
          </div>
        )}
      </Card>
    </div>
  )
}

// ── 主頁面 ────────────────────────────────────────────────────────────────────
export default function TutorialVideosPage() {
  const hasPermission = useAuthStore((s) => s.hasPermission)
  const canManage = hasPermission('tutorial_videos_manage')

  const [activeCategory, setActiveCategory] = useState<TutorialVideoCategory>('hotel')
  const [loading, setLoading] = useState(false)
  const [modules, setModules] = useState<TutorialVideoModuleItem[]>([])
  const [videos, setVideos] = useState<TutorialVideoItem[]>([])
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set())

  const [playOpen, setPlayOpen] = useState(false)
  const [playing, setPlaying] = useState<TutorialVideoItem | null>(null)

  // 上傳／編輯影片 Modal
  const [videoFormOpen, setVideoFormOpen] = useState(false)
  const [editingVideo, setEditingVideo] = useState<TutorialVideoItem | null>(null)
  const [videoSaving, setVideoSaving] = useState(false)
  const [videoFileList, setVideoFileList] = useState<UploadFile[]>([])
  const [scriptFileList, setScriptFileList] = useState<UploadFile[]>([])
  const [videoForm] = Form.useForm()

  // 新增／編輯模組 Modal
  const [moduleFormOpen, setModuleFormOpen] = useState(false)
  const [editingModule, setEditingModule] = useState<TutorialVideoModuleItem | null>(null)
  const [moduleSaving, setModuleSaving] = useState(false)
  const [moduleForm] = Form.useForm()

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
  )

  const load = useCallback(async (category: TutorialVideoCategory) => {
    setLoading(true)
    try {
      const [mods, videoRes] = await Promise.all([
        fetchTutorialVideoModules(category),
        fetchTutorialVideos({ category }),
      ])
      setModules(mods)
      setVideos(videoRes.items)
      setExpandedIds(new Set(mods.map((m) => m.id))) // 預設全部展開
    } catch {
      setModules([])
      setVideos([])
      message.error('影音教學清單載入失敗')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load(activeCategory) }, [activeCategory, load])

  const videosByModule = useMemo(() => {
    const map: Record<string, TutorialVideoItem[]> = {}
    for (const v of videos) {
      if (!map[v.module_id]) map[v.module_id] = []
      map[v.module_id].push(v)
    }
    return map
  }, [videos])

  const totalVideos = videos.length

  const toggleExpand = (moduleId: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev)
      if (next.has(moduleId)) next.delete(moduleId)
      else next.add(moduleId)
      return next
    })
  }

  // ── 播放 ────────────────────────────────────────────────────────────────
  const openPlayer = (item: TutorialVideoItem) => {
    setPlaying(item)
    setPlayOpen(true)
  }

  // ── 模組 CRUD ──────────────────────────────────────────────────────────
  const openCreateModule = () => {
    setEditingModule(null)
    moduleForm.resetFields()
    moduleForm.setFieldsValue({ category: activeCategory })
    setModuleFormOpen(true)
  }

  const openEditModule = (m: TutorialVideoModuleItem) => {
    setEditingModule(m)
    moduleForm.setFieldsValue({
      category: m.category,
      module_name: m.module_name,
      module_route: m.module_route,
    })
    setModuleFormOpen(true)
  }

  const handleModuleSubmit = async () => {
    try {
      const values = await moduleForm.validateFields()
      setModuleSaving(true)
      if (editingModule) {
        await updateTutorialVideoModule(editingModule.id, values)
      } else {
        await createTutorialVideoModule(values)
      }
      message.success(editingModule ? '模組已更新' : '模組已新增')
      setModuleFormOpen(false)
      load(activeCategory)
    } catch (err: any) {
      if (err?.errorFields) return
      message.error(extractApiError(err, '儲存模組失敗'))
    } finally {
      setModuleSaving(false)
    }
  }

  const handleDeleteModule = async (m: TutorialVideoModuleItem) => {
    try {
      await deleteTutorialVideoModule(m.id)
      message.success('模組已刪除')
      load(activeCategory)
    } catch (err: any) {
      message.error(extractApiError(err, '刪除模組失敗'))
    }
  }

  // ── 影片 CRUD ──────────────────────────────────────────────────────────
  const openUploadToModule = (m: TutorialVideoModuleItem) => {
    setEditingVideo(null)
    videoForm.resetFields()
    videoForm.setFieldsValue({ module_id: m.id })
    setVideoFileList([])
    setScriptFileList([])
    setVideoFormOpen(true)
  }

  const openEditVideo = (item: TutorialVideoItem) => {
    setEditingVideo(item)
    videoForm.setFieldsValue({
      module_id: item.module_id,
      episode: item.episode,
      title: item.title,
      description: item.description,
    })
    setVideoFileList([])
    setScriptFileList([])
    setVideoFormOpen(true)
  }

  const handleDeleteVideo = async (item: TutorialVideoItem) => {
    try {
      await deleteTutorialVideo(item.id)
      message.success('已刪除')
      load(activeCategory)
    } catch (err: any) {
      message.error(extractApiError(err, '刪除失敗'))
    }
  }

  const handleVideoSubmit = async () => {
    try {
      const values = await videoForm.validateFields()
      setVideoSaving(true)

      if (editingVideo) {
        await updateTutorialVideo(editingVideo.id, values)
      } else {
        const videoFile = videoFileList[0]?.originFileObj as File | undefined
        if (!videoFile) {
          message.error('請選擇要上傳的 MP4 影片檔')
          setVideoSaving(false)
          return
        }
        const scriptFile = scriptFileList[0]?.originFileObj as File | undefined
        await uploadTutorialVideo({ ...values, video_file: videoFile, script_file: scriptFile })
      }
      message.success(editingVideo ? '已更新' : '已上傳')
      setVideoFormOpen(false)
      load(activeCategory)
    } catch (err: any) {
      if (err?.errorFields) return
      message.error(extractApiError(err, editingVideo ? '更新失敗' : '上傳失敗'))
    } finally {
      setVideoSaving(false)
    }
  }

  // ── 拖曳排序（模組層／集數層共用同一個 DndContext）──────────────────────
  const handleDragEnd = useCallback((event: DragEndEvent) => {
    const { active, over } = event
    if (!over || active.id === over.id) return
    const activeId = active.id as string
    const overId = over.id as string

    // 模組層
    const moduleIds = modules.map((m) => m.id)
    if (moduleIds.includes(activeId) && moduleIds.includes(overId)) {
      const oldIndex = moduleIds.indexOf(activeId)
      const newIndex = moduleIds.indexOf(overId)
      const reordered = arrayMove(modules, oldIndex, newIndex)
      setModules(reordered)
      reorderTutorialVideoModules(activeCategory, reordered.map((m) => m.id)).catch(() => {
        message.error('模組排序儲存失敗，已重新載入')
        load(activeCategory)
      })
      return
    }

    // 集數層（同一模組內）
    for (const moduleId of Object.keys(videosByModule)) {
      const vids = videosByModule[moduleId]
      const vidIds = vids.map((v) => v.id)
      if (vidIds.includes(activeId) && vidIds.includes(overId)) {
        const oldIndex = vidIds.indexOf(activeId)
        const newIndex = vidIds.indexOf(overId)
        const reordered = arrayMove(vids, oldIndex, newIndex)
        setVideos((prev) => {
          const others = prev.filter((v) => v.module_id !== moduleId)
          return [...others, ...reordered]
        })
        reorderTutorialVideos(moduleId, reordered.map((v) => v.id)).catch(() => {
          message.error('集數排序儲存失敗，已重新載入')
          load(activeCategory)
        })
        return
      }
    }
  }, [modules, videosByModule, activeCategory, load])

  return (
    <div style={{ padding: 24 }}>
      <Space align="center" style={{ marginBottom: 16 }} wrap>
        <VideoCameraOutlined style={{ fontSize: 20, color: '#4BA8E8' }} />
        <Title level={4} style={{ margin: 0 }}>影音教學</Title>
        <Tag color="blue">共 {totalVideos} 支</Tag>
      </Space>

      <Tabs
        activeKey={activeCategory}
        onChange={(k) => setActiveCategory(k as TutorialVideoCategory)}
        items={CATEGORY_TABS.map((t) => ({ key: t.key, label: t.label }))}
        tabBarExtraContent={
          canManage ? (
            <Button icon={<PlusOutlined />} onClick={openCreateModule}>
              新增模組
            </Button>
          ) : undefined
        }
      />

      {!loading && modules.length === 0 && (
        <Empty description="此分類目前沒有教學模組" style={{ marginTop: 48 }} />
      )}

      <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
        <SortableContext items={modules.map((m) => m.id)} strategy={verticalListSortingStrategy}>
          {modules.map((m) => (
            <ModuleBlock
              key={m.id}
              module={m}
              videos={videosByModule[m.id] || []}
              canManage={canManage}
              expanded={expandedIds.has(m.id)}
              onToggle={() => toggleExpand(m.id)}
              onEditModule={openEditModule}
              onDeleteModule={handleDeleteModule}
              onUploadToModule={openUploadToModule}
              onPlay={openPlayer}
              onEditVideo={openEditVideo}
              onDeleteVideo={handleDeleteVideo}
            />
          ))}
        </SortableContext>
      </DndContext>

      {/* 播放 Modal */}
      <Modal
        open={playOpen}
        onCancel={() => setPlayOpen(false)}
        footer={null}
        width={800}
        title={playing ? `${playing.episode ? playing.episode + '：' : ''}${playing.title}` : ''}
        destroyOnClose
      >
        {playing && (
          <video
            key={playing.id}
            src={tutorialVideoStreamUrl(playing.id)}
            controls
            autoPlay
            style={{ width: '100%', maxHeight: '60vh', background: '#000' }}
          />
        )}
      </Modal>

      {/* 上傳／編輯影片 Modal */}
      <Modal
        open={videoFormOpen}
        onCancel={() => setVideoFormOpen(false)}
        onOk={handleVideoSubmit}
        confirmLoading={videoSaving}
        title={editingVideo ? '編輯教學影片資訊' : '新增教學集數'}
        width={560}
        destroyOnClose
      >
        <Form form={videoForm} layout="vertical">
          <Form.Item name="module_id" hidden><Input /></Form.Item>
          <Space style={{ width: '100%' }} size={12}>
            <Form.Item name="episode" label="集數" style={{ width: 140 }}>
              <Input placeholder="例：EP01" />
            </Form.Item>
          </Space>
          <Form.Item name="title" label="集標題" rules={[{ required: true, message: '請輸入集標題' }]}>
            <Input placeholder="例：年度矩陣－月份視圖＋季度視圖＋Drawer明細" />
          </Form.Item>
          <Form.Item name="description" label="說明（選填）">
            <Input.TextArea rows={2} />
          </Form.Item>

          {!editingVideo && (
            <>
              <Form.Item label="教學影片（MP4）" required>
                <Upload
                  accept="video/mp4"
                  maxCount={1}
                  beforeUpload={() => false}
                  fileList={videoFileList}
                  onChange={({ fileList: fl }) => setVideoFileList(fl)}
                >
                  <Button icon={<UploadOutlined />}>選擇 MP4 檔案</Button>
                </Upload>
              </Form.Item>
              <Form.Item label="TTS 逐字稿（TXT，選填）">
                <Upload
                  accept=".txt"
                  maxCount={1}
                  beforeUpload={() => false}
                  fileList={scriptFileList}
                  onChange={({ fileList: fl }) => setScriptFileList(fl)}
                >
                  <Button icon={<UploadOutlined />}>選擇 TXT 檔案</Button>
                </Upload>
              </Form.Item>
            </>
          )}
        </Form>
      </Modal>

      {/* 新增／編輯模組 Modal */}
      <Modal
        open={moduleFormOpen}
        onCancel={() => setModuleFormOpen(false)}
        onOk={handleModuleSubmit}
        confirmLoading={moduleSaving}
        title={editingModule ? '編輯教學模組' : '新增教學模組'}
        width={480}
        destroyOnClose
      >
        <Form form={moduleForm} layout="vertical">
          <Form.Item name="category" label="分類" rules={[{ required: true }]}>
            <Segmented options={CATEGORY_TABS.map((t) => ({ value: t.key, label: t.label }))} />
          </Form.Item>
          <Form.Item name="module_name" label="中文模組名稱" rules={[{ required: true, message: '請輸入模組名稱' }]}>
            <Input placeholder="例：IHG客房保養" />
          </Form.Item>
          <Form.Item name="module_route" label="對應 Portal 路由（選填）">
            <Input placeholder="例：/hotel/ihg-room-maintenance" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
