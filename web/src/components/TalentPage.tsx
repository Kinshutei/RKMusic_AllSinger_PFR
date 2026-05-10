import { useState } from 'react'
import { VideoCard, VideoType, VideoFlags, AllHistory } from '../types'
import { getLatestChannelStats, buildTalentVideoList } from '../utils/data'

interface Props {
  history: AllHistory
  talentName: string
  flags: VideoFlags
}

type SortKey = '再生数' | '高評価数' | 'コメント数' | '再生数15d増加' | '高評価15d増加' | 'キリ番到達日'
type TabType = VideoType

const SORT_OPTIONS: { key: SortKey; label: string }[] = [
  { key: '再生数',       label: '📊 再生数TOP' },
  { key: '高評価数',     label: '👍 高評価TOP' },
  { key: 'コメント数',   label: '💬 コメント数TOP' },
  { key: '再生数15d増加', label: '📈 再生15日増加' },
  { key: '高評価15d増加', label: '💹 高評価15日増加' },
  { key: 'キリ番到達日',   label: '📅 キリ番到達順' },
]

const ALL_TABS: { type: TabType; label: string }[] = [
  { type: 'Movie',       label: '動画' },
  { type: 'Short',       label: 'ショート' },
  { type: 'LiveArchive', label: 'ライブ' },
]

function fmtDiff(v: number | null): string {
  if (v === null) return '—'
  return v >= 0 ? `+${v.toLocaleString()}` : v.toLocaleString()
}

function diffColor(v: number | null): string {
  if (v === null) return '#aaa'
  return v > 0 ? '#2e7d5a' : v < 0 ? '#c0392b' : '#888'
}


function niceScale(dataMin: number, dataMax: number, targetTicks = 4) {
  const minV = Math.min(dataMin, 0)
  const maxV = Math.max(dataMax, 0)
  if (minV === maxV) return { ticks: [0, maxV || 1], niceMin: 0, niceMax: maxV || 1 }
  const range = maxV - minV
  const rawStep = range / (targetTicks - 1)
  const mag = Math.pow(10, Math.floor(Math.log10(rawStep)))
  const norm = rawStep / mag
  const step = norm <= 1 ? mag : norm <= 2 ? 2 * mag : norm <= 5 ? 5 * mag : 10 * mag
  const niceMin = Math.floor(minV / step) * step
  const niceMax = Math.ceil(maxV / step) * step
  const ticks: number[] = []
  for (let v = niceMin; v <= niceMax + step * 0.01; v += step) {
    ticks.push(Math.round(v * 1e10) / 1e10)
  }
  return { ticks, niceMin, niceMax }
}

function fmtBarLabel(v: number): string {
  const sign = v >= 0 ? '+' : '-'
  const abs = Math.abs(v)
  if (abs >= 10000) return `${sign}${Math.round(abs / 1000)}K`
  if (abs >= 1000)  return `${sign}${(abs / 1000).toFixed(1)}K`
  return `${sign}${abs}`
}

function MiniBarChart({ daily, title }: {
  daily: (number | null)[]
  title: string
}) {
  const n = daily.findIndex(v => v === null)
  const count = n === -1 ? daily.length : n
  if (count < 2) return null

  const vals = daily.slice(0, count) as number[]
  const labels = vals.map((_, i) => `${i + 2}D`)

  const BAR_SLOT = 36
  const BAR_W = 30
  const PAD = { top: 22, right: 8, bottom: 22, left: 4 }
  const PLOT_H = 72

  const svgW = PAD.left + PAD.right + count * BAR_SLOT
  const svgH = PAD.top + PLOT_H + PAD.bottom

  const { ticks, niceMin, niceMax } = niceScale(Math.min(...vals), Math.max(...vals))
  const displayRange = niceMax - niceMin || 1
  const sy = (v: number) => PAD.top + PLOT_H - ((v - niceMin) / displayRange) * PLOT_H
  const zeroY = sy(0)

  const avg = Math.round(vals.reduce((a, b) => a + b, 0) / vals.length)

  return (
    <div style={{ marginBottom: 6 }}>
      <div style={{ fontSize: 12, color: '#888', marginBottom: 2 }}>
        {title}
        <span style={{ marginLeft: 8, color: '#2a305c' }}>
          （{vals.length}日間平均：{fmtBarLabel(avg)}）
        </span>
      </div>
      <svg width={svgW} height={svgH} style={{ fontFamily: 'inherit', display: 'block' }}>
        {ticks.map(tick => {
          const y = sy(tick)
          return (
            <line key={tick} x1={PAD.left} y1={y} x2={PAD.left + count * BAR_SLOT} y2={y}
              stroke={tick === 0 ? '#3a4580' : '#e0e3f5'} strokeWidth={tick === 0 ? 1 : 0.5} />
          )
        })}
        {vals.map((v, i) => {
          const bTop = Math.min(sy(v), zeroY)
          const bH = Math.max(Math.abs(sy(v) - zeroY), 1)
          const x = PAD.left + BAR_SLOT * i + (BAR_SLOT - BAR_W) / 2
          const cx = x + BAR_W / 2
          const labelY = v >= 0 ? bTop - 3 : bTop + bH + 10
          return (
            <g key={i}>
              <rect x={x} y={bTop} width={BAR_W} height={bH}
                fill={v >= 0 ? '#3a4580' : '#e88899'} rx={2}>
                <title>{labels[i]}: {v >= 0 ? '+' : ''}{v.toLocaleString()}</title>
              </rect>
              <text x={cx} y={labelY} textAnchor="middle" fontSize={10}
                fill={v >= 0 ? '#2a305c' : '#aa2233'}>
                {fmtBarLabel(v)}
              </text>
              <text x={cx} y={PAD.top + PLOT_H + 15}
                textAnchor="middle" fontSize={11} fill="#b0b6d8">
                {labels[i]}
              </text>
            </g>
          )
        })}
      </svg>
    </div>
  )
}

function getNextMilestone(val: number): number {
  let unit: number
  if (val < 10000)       unit = 1000
  else if (val < 100000) unit = 10000
  else                   unit = 100000
  return Math.floor(val / unit + 1) * unit
}

function estimateDate(latestDate: string, latestVal: number, milestone: number, avgPerDay: number | null): string {
  if (!avgPerDay || avgPerDay <= 0) return '—'
  const days = (milestone - latestVal) / avgPerDay
  const d = new Date(latestDate)
  d.setDate(d.getDate() + Math.ceil(days))
  return d.toISOString().slice(0, 10)
}

// ── 動画カード ────────────────────────────────────────────────────────────────
function viewMilestoneDays(再生数: number, daily: (number | null)[]): number {
  const vals = daily.filter((v): v is number => v !== null)
  if (vals.length === 0) return Infinity
  const avg = vals.reduce((a, b) => a + b, 0) / vals.length
  if (avg <= 0) return Infinity
  const milestone = getNextMilestone(再生数)
  const days = (milestone - 再生数) / avg
  return days > 0 ? days : Infinity
}

function viewMilestoneLabel(再生数: number, daily: (number | null)[]): string | null {
  const vals = daily.filter((v): v is number => v !== null)
  if (vals.length === 0) return null
  const avg = vals.reduce((a, b) => a + b, 0) / vals.length
  if (avg <= 0) return null
  const milestone = getNextMilestone(再生数)
  const today = new Date().toISOString().slice(0, 10)
  const dateStr = estimateDate(today, 再生数, milestone, avg)
  if (dateStr === '—') return null
  const [, m, d] = dateStr.split('-')
  const daysLeft = Math.ceil((new Date(dateStr).getTime() - new Date(today).getTime()) / 86400000)
  return `次のキリ番 ${milestone.toLocaleString()} / ${parseInt(m)}月${parseInt(d)}日頃（${daysLeft}日後）`
}

function VideoCardItem({ video }: { video: VideoCard }) {
  const v1d = video.再生数daily[0]
  const l1d = video.高評価daily[0]
  const c1d = video.コメント数daily[0]
  const url = `https://www.youtube.com/watch?v=${video.id}`
  const commentLabel = viewMilestoneLabel(video.再生数, video.再生数daily)

  return (
    <div className="video-card">
      <div className="video-title">
        <a href={url} target="_blank" rel="noopener noreferrer">{video.タイトル}</a>
      </div>
      <div className="video-stats">
        <span>
          再生数：<strong>{video.再生数.toLocaleString()}</strong>
          {v1d !== null && (
            <span className="stat-diff" style={{ color: diffColor(v1d) }}>
              {' '}({fmtDiff(v1d)})
            </span>
          )}
        </span>
        <span>
          高評価：<strong>{video.高評価数.toLocaleString()}</strong>
          {l1d !== null && (
            <span className="stat-diff" style={{ color: diffColor(l1d) }}>
              {' '}({fmtDiff(l1d)})
            </span>
          )}
        </span>
        <span>
          コメント：<strong>{video.コメント数.toLocaleString()}</strong>
          {c1d !== null && (
            <span className="stat-diff" style={{ color: diffColor(c1d) }}>
              {' '}({fmtDiff(c1d)})
            </span>
          )}
        </span>
      </div>
      {commentLabel && (
        <div style={{ fontSize: 12, color: '#3a4580', marginTop: 2, marginBottom: 12 }}>
          {commentLabel}
        </div>
      )}
      <MiniBarChart daily={video.再生数daily.slice(1)} title="再生数 日別増加" />
      <MiniBarChart daily={video.高評価daily.slice(1)} title="高評価数 日別増加" />
    </div>
  )
}

export default function TalentPage({ history, talentName, flags }: Props) {
  const { stats, diff } = getLatestChannelStats(history, talentName)
  const allVideos = buildTalentVideoList(history, talentName, flags)

  const videoByType: Record<VideoType, VideoCard[]> = { Movie: [], Short: [], LiveArchive: [] }
  for (const v of allVideos) {
    if (v.type in videoByType) videoByType[v.type].push(v)
  }

  const activeTabs = ALL_TABS.filter(t => videoByType[t.type].length > 0)
  const [activeType, setActiveType] = useState<TabType>(activeTabs[0]?.type ?? 'Movie')
  const [sortKey, setSortKey] = useState<SortKey>('再生数')

  function fmtStatDiff(v: number | null) {
    if (v === null) return null
    const sign = v >= 0 ? '+' : ''
    return <span style={{ fontSize: 13, color: diffColor(v), marginLeft: 6 }}>({sign}{v.toLocaleString()})</span>
  }

  const sorted = [...videoByType[activeType]].sort((a, b) => {
    if (sortKey === 'キリ番到達日') {
      return viewMilestoneDays(a.再生数, a.再生数daily) - viewMilestoneDays(b.再生数, b.再生数daily)
    }
    return (b[sortKey] as number) - (a[sortKey] as number)
  })

  return (
    <div>
      {/* チャンネル統計 */}
      <div className="channel-header">
        <h2 className="talent-name">{talentName}</h2>
        {stats && (
          <div className="channel-stats">
            <span>登録者数：<strong>{stats.登録者数.toLocaleString()}</strong>{fmtStatDiff(diff?.登録者数 ?? null)}</span>
            <span>総再生数：<strong>{stats.総再生数.toLocaleString()}</strong>{fmtStatDiff(diff?.総再生数 ?? null)}</span>
            <span>動画数：<strong>{stats.動画数.toLocaleString()}</strong>{fmtStatDiff(diff?.動画数 ?? null)}</span>
          </div>
        )}
      </div>

      <div className="divider" />

      {activeTabs.length === 0 ? (
        <p className="muted">動画データを蓄積中です。</p>
      ) : (
        <>
          {/* タイプタブ */}
          <div className="type-tabs">
            {activeTabs.map(t => (
              <button
                key={t.type}
                className={`type-tab-btn${activeType === t.type ? ' active' : ''}`}
                onClick={() => { setActiveType(t.type); setSortKey('再生数') }}
              >
                {t.label}
                <span className="tab-count">({videoByType[t.type].length})</span>
              </button>
            ))}
          </div>

          <>
            {/* ソートボタン */}
            <div className="sort-btns">
              {SORT_OPTIONS.map(o => (
                <button
                  key={o.key}
                  className={`sort-btn${sortKey === o.key ? ' active' : ''}`}
                  onClick={() => setSortKey(o.key)}
                >
                  {o.label}
                </button>
              ))}
            </div>

            {/* 動画カード */}
            <div className="video-list">
              {sorted.map(v => (
                <VideoCardItem key={v.id} video={v} />
              ))}
            </div>
          </>
        </>
      )}
    </div>
  )
}
