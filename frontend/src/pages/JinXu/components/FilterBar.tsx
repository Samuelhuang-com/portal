/**
 * 金旭分析 — 共用日期區間工具列
 */
import { Button, DatePicker, Space, Tag } from 'antd'
import { ReloadOutlined } from '@ant-design/icons'
import dayjs, { Dayjs } from 'dayjs'

const { RangePicker } = DatePicker

interface Props {
  range: [Dayjs | null, Dayjs | null] | null
  onChange: (r: [Dayjs | null, Dayjs | null] | null) => void
  onReload?: () => void
  periodLabel?: string
  extra?: React.ReactNode
}

export default function FilterBar({ range, onChange, onReload, periodLabel, extra }: Props) {
  return (
    <Space wrap style={{ marginBottom: 16 }}>
      <RangePicker
        value={range as never}
        onChange={(v) => onChange(v as never)}
        allowEmpty={[true, true]}
        presets={[
          { label: '本月', value: [dayjs().startOf('month'), dayjs()] },
          { label: '上月', value: [dayjs().subtract(1, 'month').startOf('month'), dayjs().subtract(1, 'month').endOf('month')] },
          { label: '今年', value: [dayjs().startOf('year'), dayjs()] },
          { label: '全部', value: [null as never, null as never] },
        ]}
      />
      {periodLabel && <Tag color="blue">{periodLabel}</Tag>}
      {extra}
      {onReload && <Button icon={<ReloadOutlined />} onClick={onReload}>重新整理</Button>}
    </Space>
  )
}

export const toIso = (d: Dayjs | null | undefined): string =>
  d ? d.format('YYYY-MM-DD') : ''
