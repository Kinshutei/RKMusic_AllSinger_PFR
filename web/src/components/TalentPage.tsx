import { useState, useRef, useEffect } from 'react'
import { VideoCard, VideoType, VideoFlags, AllHistory, AllComments, VideoCommentData } from '../types'
import {
  getLatestChannelStats, buildTalentVideoList,
  buildPostingCalendar, buildVelocityCurveData, buildDailyViewsBreakdown,
  buildMonthlyViewsBreakdown,
  PostingCalendarEntry, VelocityCurveItem, DailyViewsEntry, MonthlyViewsEntry,
} from '../utils/data'
import { niceScale, fmtDiff, diffColor } from '../utils/chartUtils'

interface Props {
  history: AllHistory
  talentName: string
  flags: VideoFlags
  comments: AllComments
}

type SortKey = '再生数' | '高評価数' | 'コメント数' | '再生数15d増加' | '高評価15d増加' | 'キリ番到達日'
type TabType = VideoType | '分析'

const SORT_OPTIONS: { key: SortKey; label: string }[] = [
  { key: '再生数',        label: '📊 再生数TOP' },
  { key: '高評価数',      label: '👍 高評価TOP' },
  { key: 'コメント数',    label: '💬 コメント数TOP' },
  { key: '再生数15d増加', label: '📈 再生15日増加' },
  { key: '高評価15d増加', label: '💹 高評価15日増加' },
  { key: 'キリ番到達日',  label: '📅 キリ番到達順' },
]

const VIDEO_TABS: { type: VideoType; label: string }[] = [
  { type: 'Movie',       label: '動画' },
  { type: 'Short',       label: 'ショート' },
  { type: 'LiveArchive', label: 'ライブ' },
]

// ----------------------------------------------------------------
// ミニバーチャート（既存）
// ----------------------------------------------------------------

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
  const wrapperRef = useRef<HTMLDivElement>(null)
  const [containerW, setContainerW] = useState(500)

  useEffect(() => {
    const el = wrapperRef.current
    if (!el) return
    const update = () => setContainerW(el.clientWidth)
    update()
    const ro = new ResizeObserver(update)
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  const n = daily.findIndex(v => v === null)
  const count = n === -1 ? daily.length : n
  if (count < 2) return null

  const vals = daily.slice(0, count) as number[]
  const labels = vals.map((_, i) => `${i + 2}D`)

  const PAD = { top: 22, right: 8, bottom: 22, left: 4 }
  const PLOT_H = 72

  const availableW = containerW - PAD.left - PAD.right
  const BAR_SLOT = count > 0 ? Math.min(36, Math.floor(availableW / count)) : 36
  const BAR_W = Math.min(30, BAR_SLOT - 4)

  const svgW = PAD.left + PAD.right + count * BAR_SLOT
  const svgH = PAD.top + PLOT_H + PAD.bottom

  const { ticks, niceMin, niceMax } = niceScale(Math.min(...vals), Math.max(...vals))
  const displayRange = niceMax - niceMin || 1
  const sy = (v: number) => PAD.top + PLOT_H - ((v - niceMin) / displayRange) * PLOT_H
  const zeroY = sy(0)

  const avg = Math.round(vals.reduce((a, b) => a + b, 0) / vals.length)

  return (
    <div ref={wrapperRef} style={{ marginBottom: 6 }}>
      <div style={{ fontSize: 12, color: '#888', marginBottom: 2 }}>
        {title}
        <span style={{ marginLeft: 8, color: '#2a305c' }}>
          （{vals.length}日間平均：{fmtBarLabel(avg)}）
        </span>
      </div>
      <div>
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
    </div>
  )
}

// ----------------------------------------------------------------
// キリ番予測
// ----------------------------------------------------------------

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

// ----------------------------------------------------------------
// 経過日数
// ----------------------------------------------------------------

function elapsedDaysLabel(公開日: string): string {
  if (!公開日) return ''
  const diff = Math.floor((Date.now() - new Date(公開日).getTime()) / 86400000)
  if (diff < 0) return ''
  if (diff === 0) return '公開当日'
  return `公開${diff}日`
}

// ----------------------------------------------------------------
// 感情サマリー
// ----------------------------------------------------------------

const SENTIMENT_COLORS = {
  positive: '#4ca86b',
  neutral:  '#8899c0',
  negative: '#cc4455',
}
const SENTIMENT_LABELS = {
  positive: 'ポジ',
  neutral:  'ニュートラル',
  negative: 'ネガ',
}

function SentimentBar({ sentiment }: { sentiment: VideoCommentData['sentiment'] }) {
  const total = sentiment.positive + sentiment.neutral + sentiment.negative
  if (total === 0) return null
  const types = ['positive', 'neutral', 'negative'] as const
  return (
    <div style={{ marginTop: 6 }}>
      <div style={{ fontSize: 11, color: '#888', marginBottom: 3 }}>
        コメント感情（{total}件）
      </div>
      <div style={{ display: 'flex', height: 8, borderRadius: 4, overflow: 'hidden', gap: 1 }}>
        {types.map(t => {
          const w = (sentiment[t] / total) * 100
          if (w === 0) return null
          return (
            <div key={t} style={{ width: `${w}%`, backgroundColor: SENTIMENT_COLORS[t] }}
                 title={`${SENTIMENT_LABELS[t]}: ${sentiment[t]}件 (${w.toFixed(0)}%)`} />
          )
        })}
      </div>
      <div style={{ display: 'flex', gap: 10, marginTop: 3, fontSize: 10, color: '#888' }}>
        {types.map(t => (
          <span key={t}>
            <span style={{ color: SENTIMENT_COLORS[t] }}>●</span>
            {` ${SENTIMENT_LABELS[t]} ${((sentiment[t] / total) * 100).toFixed(0)}%`}
          </span>
        ))}
      </div>
    </div>
  )
}

function TopComments({ commentData }: { commentData: VideoCommentData }) {
  const [open, setOpen] = useState(false)
  const top = commentData.display_comments.slice(0, 5)
  if (top.length === 0) return null
  return (
    <div style={{ marginTop: 6 }}>
      <button
        style={{ fontSize: 11, color: '#6677cc', background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}
        onClick={() => setOpen(o => !o)}
      >
        {open ? '▲ コメントを閉じる' : `▼ トップコメントを見る（${top.length}件）`}
      </button>
      {open && (
        <div style={{ marginTop: 6, display: 'flex', flexDirection: 'column', gap: 6 }}>
          {top.map((c, i) => (
            <div key={i} style={{
              fontSize: 12, padding: '6px 8px', borderRadius: 4,
              backgroundColor: '#f4f5fb', borderLeft: `3px solid ${SENTIMENT_COLORS[c.sentiment]}`,
            }}>
              <div style={{ color: '#333', lineHeight: 1.5 }}>{c.text}</div>
              <div style={{ color: '#888', marginTop: 2 }}>
                👍 {c.likes.toLocaleString()}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ----------------------------------------------------------------
// 動画カード
// ----------------------------------------------------------------

function VideoCardItem({ video, commentData }: {
  video: VideoCard
  commentData: VideoCommentData | undefined
}) {
  const v1d = video.再生数daily[0]
  const l1d = video.高評価daily[0]
  const c1d = video.コメント数daily[0]
  const url = `https://www.youtube.com/watch?v=${video.id}`
  const commentLabel = viewMilestoneLabel(video.再生数, video.再生数daily)

  return (
    <div className="video-card">
      {/* コラボタグ */}
      {video.collab_tags.length > 0 && (
        <div style={{ marginBottom: 4, display: 'flex', gap: 4, flexWrap: 'wrap' }}>
          {video.collab_tags.map(tag => (
            <span key={tag} style={{
              fontSize: 10, padding: '1px 6px', borderRadius: 10,
              backgroundColor: '#e8eaf6', color: '#3a4580', fontWeight: 600,
            }}>
              {tag}
            </span>
          ))}
        </div>
      )}

      <div className="video-title">
        <a href={url} target="_blank" rel="noopener noreferrer">{video.タイトル}</a>
      </div>

      {/* 公開日＋経過日数 */}
      {video.公開日 && (
        <div style={{ fontSize: 11, color: '#888', marginBottom: 4 }}>
          {video.公開日} &nbsp;·&nbsp; {elapsedDaysLabel(video.公開日)}
        </div>
      )}

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

      {/* コメント感情 */}
      {commentData && (
        <>
          <SentimentBar sentiment={commentData.sentiment} />
          <TopComments commentData={commentData} />
        </>
      )}
    </div>
  )
}

// ----------------------------------------------------------------
// 投稿カレンダーチャート
// ----------------------------------------------------------------

const TYPE_COLORS: Record<VideoType, string> = {
  Movie:       '#6677cc',
  Short:       '#cc4455',
  LiveArchive: '#44aa77',
}
const TYPE_LABELS: Record<VideoType, string> = {
  Movie:       '動画',
  Short:       'ショート',
  LiveArchive: 'ライブ',
}

function PostingCalendarChart({ data }: { data: PostingCalendarEntry[] }) {
  const wrapperRef = useRef<HTMLDivElement>(null)
  const [containerW, setContainerW] = useState(600)

  useEffect(() => {
    const el = wrapperRef.current
    if (!el) return
    const update = () => setContainerW(el.clientWidth)
    update()
    const ro = new ResizeObserver(update)
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  if (data.length === 0) return <p className="muted">投稿データがありません</p>

  const types: VideoType[] = ['Movie', 'Short', 'LiveArchive']
  const maxTotal = Math.max(...data.map(d => d.Movie + d.Short + d.LiveArchive))

  const PAD = { top: 16, right: 16, bottom: 48, left: 36 }
  const PLOT_H = 200
  const BAR_SLOT = Math.max(32, Math.floor((containerW - PAD.left - PAD.right) / data.length))
  const BAR_W = Math.min(28, BAR_SLOT - 4)
  const svgW = Math.max(containerW, PAD.left + PAD.right + data.length * BAR_SLOT)
  const svgH = PAD.top + PLOT_H + PAD.bottom

  const yScale = maxTotal > 0 ? PLOT_H / maxTotal : 1
  const yTicks = [0, Math.ceil(maxTotal / 4), Math.ceil(maxTotal / 2), Math.ceil(maxTotal * 3 / 4), maxTotal].filter((v, i, a) => a.indexOf(v) === i)

  return (
    <div ref={wrapperRef} style={{ overflowX: 'auto' }}>
      <svg width={svgW} height={svgH} style={{ fontFamily: 'inherit', display: 'block' }}>
        {yTicks.map(tick => {
          const y = PAD.top + PLOT_H - tick * yScale
          return (
            <g key={tick}>
              <line x1={PAD.left} y1={y} x2={PAD.left + data.length * BAR_SLOT} y2={y}
                    stroke={tick === 0 ? '#555' : '#e0e3f5'} strokeWidth={1} />
              <text x={PAD.left - 4} y={y + 4} textAnchor="end" fontSize={10} fill="#888">
                {tick}
              </text>
            </g>
          )
        })}

        {data.map((entry, i) => {
          const x = PAD.left + i * BAR_SLOT + (BAR_SLOT - BAR_W) / 2
          let yBase = PAD.top + PLOT_H
          return (
            <g key={entry.month}>
              {types.map(t => {
                const count = entry[t]
                if (count === 0) return null
                const h = count * yScale
                yBase -= h
                return (
                  <rect key={t} x={x} y={yBase} width={BAR_W} height={h}
                        fill={TYPE_COLORS[t]} rx={1}>
                    <title>{entry.month} {TYPE_LABELS[t]}: {count}本</title>
                  </rect>
                )
              })}
              <text x={x + BAR_W / 2} y={PAD.top + PLOT_H + 14}
                    textAnchor="end" fontSize={9} fill="#888"
                    transform={`rotate(-45, ${x + BAR_W / 2}, ${PAD.top + PLOT_H + 14})`}>
                {entry.month.slice(5)}月
              </text>
            </g>
          )
        })}
      </svg>

      {/* 凡例 */}
      <div style={{ display: 'flex', gap: 16, marginTop: 4, fontSize: 12, color: '#666' }}>
        {types.map(t => (
          <span key={t} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <span style={{ width: 12, height: 12, borderRadius: 2, backgroundColor: TYPE_COLORS[t], display: 'inline-block' }} />
            {TYPE_LABELS[t]}
          </span>
        ))}
      </div>
    </div>
  )
}

// ----------------------------------------------------------------
// 初速カーブチャート
// ----------------------------------------------------------------

const CURVE_COLORS = [
  '#6677cc', '#cc4455', '#44aa77', '#e89944', '#9944cc',
  '#44aacc', '#cc9944', '#88aa44', '#cc4499', '#4499cc',
]

function fmtViews(v: number): string {
  if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`
  if (v >= 1_000)     return `${Math.round(v / 1_000)}K`
  return String(v)
}

function VelocityCurveChart({ items }: { items: VelocityCurveItem[] }) {
  const wrapperRef = useRef<HTMLDivElement>(null)
  const [containerW, setContainerW] = useState(600)

  useEffect(() => {
    const el = wrapperRef.current
    if (!el) return
    const update = () => setContainerW(el.clientWidth)
    update()
    const ro = new ResizeObserver(update)
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  if (items.length === 0) return <p className="muted">初速データのある動画がありません（公開日以降のデータが必要です）</p>

  const allDays  = items.flatMap(it => it.curve.map(p => p.day))
  const allViews = items.flatMap(it => it.curve.map(p => p.views))
  const maxDay   = Math.max(...allDays, 1)
  const maxViews = Math.max(...allViews, 1)

  const PAD = { top: 16, right: 16, bottom: 36, left: 56 }
  const PLOT_H = 220
  const svgW = containerW
  const PLOT_W = svgW - PAD.left - PAD.right
  const svgH = PAD.top + PLOT_H + PAD.bottom

  const sx = (day: number) => PAD.left + (day / maxDay) * PLOT_W
  const sy = (views: number) => PAD.top + PLOT_H - (views / maxViews) * PLOT_H

  const { ticks: yTicks } = niceScale(0, maxViews, 5)

  return (
    <div ref={wrapperRef} style={{ overflowX: 'auto' }}>
      <svg width={svgW} height={svgH} style={{ fontFamily: 'inherit', display: 'block' }}>
        {yTicks.map(tick => {
          const y = sy(tick)
          return (
            <g key={tick}>
              <line x1={PAD.left} y1={y} x2={PAD.left + PLOT_W} y2={y}
                    stroke={tick === 0 ? '#555' : '#e0e3f5'} strokeWidth={1} />
              <text x={PAD.left - 4} y={y + 4} textAnchor="end" fontSize={10} fill="#888">
                {fmtViews(tick)}
              </text>
            </g>
          )
        })}

        {/* X軸 目盛 */}
        {[0, 7, 14, 30, 60].filter(d => d <= maxDay).map(d => (
          <g key={d}>
            <line x1={sx(d)} y1={PAD.top} x2={sx(d)} y2={PAD.top + PLOT_H}
                  stroke="#e0e3f5" strokeWidth={1} strokeDasharray="3,3" />
            <text x={sx(d)} y={PAD.top + PLOT_H + 14}
                  textAnchor="middle" fontSize={10} fill="#888">
              {d}日
            </text>
          </g>
        ))}

        {items.map((item, idx) => {
          const color = CURVE_COLORS[idx % CURVE_COLORS.length]
          const pts = item.curve
          const path = pts.map((p, i) =>
            `${i === 0 ? 'M' : 'L'} ${sx(p.day)} ${sy(p.views)}`
          ).join(' ')
          const last = pts.at(-1)!
          return (
            <g key={item.vid_id}>
              <path d={path} fill="none" stroke={color} strokeWidth={2} opacity={0.85} />
              <circle cx={sx(last.day)} cy={sy(last.views)} r={3} fill={color} />
            </g>
          )
        })}
      </svg>

      {/* 凡例 */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 4, marginTop: 8 }}>
        {items.map((item, idx) => (
          <div key={item.vid_id} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11 }}>
            <span style={{ width: 20, height: 3, backgroundColor: CURVE_COLORS[idx % CURVE_COLORS.length], display: 'inline-block', borderRadius: 2 }} />
            <span style={{ color: '#555' }}>{item.公開日}</span>
            <span style={{ color: '#333' }}>{item.title.length > 30 ? item.title.slice(0, 30) + '…' : item.title}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

// ----------------------------------------------------------------
// 直近N日 日別再生数内訳チャート
// ----------------------------------------------------------------

function DailyViewsChart({ data }: { data: DailyViewsEntry[] }) {
  const wrapperRef = useRef<HTMLDivElement>(null)
  const [containerW, setContainerW] = useState(600)

  useEffect(() => {
    const el = wrapperRef.current
    if (!el) return
    const update = () => setContainerW(el.clientWidth)
    update()
    const ro = new ResizeObserver(update)
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  if (data.length === 0) return <p className="muted">再生数データがありません</p>

  const types: VideoType[] = ['Movie', 'Short', 'LiveArchive']
  const maxTotal = Math.max(...data.map(d => d.Movie + d.Short + d.LiveArchive), 1)

  const PAD = { top: 24, right: 16, bottom: 48, left: 56 }
  const PLOT_H = 180
  const BAR_SLOT = Math.max(32, Math.floor((containerW - PAD.left - PAD.right) / data.length))
  const BAR_W = Math.min(28, BAR_SLOT - 4)
  const svgW = Math.max(containerW, PAD.left + PAD.right + data.length * BAR_SLOT)
  const svgH = PAD.top + PLOT_H + PAD.bottom

  const { ticks } = niceScale(0, maxTotal, 5)
  const yScale = PLOT_H / maxTotal

  return (
    <div ref={wrapperRef} style={{ overflowX: 'auto' }}>
      <svg width={svgW} height={svgH} style={{ fontFamily: 'inherit', display: 'block' }}>
        {ticks.map(tick => {
          const y = PAD.top + PLOT_H - tick * yScale
          return (
            <g key={tick}>
              <line x1={PAD.left} y1={y} x2={PAD.left + data.length * BAR_SLOT} y2={y}
                    stroke={tick === 0 ? '#555' : '#e0e3f5'} strokeWidth={1} />
              <text x={PAD.left - 4} y={y + 4} textAnchor="end" fontSize={10} fill="#888">
                {fmtViews(tick)}
              </text>
            </g>
          )
        })}

        {data.map((entry, i) => {
          const x = PAD.left + i * BAR_SLOT + (BAR_SLOT - BAR_W) / 2
          let yBase = PAD.top + PLOT_H
          const total = entry.Movie + entry.Short + entry.LiveArchive
          return (
            <g key={entry.date}>
              {types.map(t => {
                const count = entry[t]
                if (count === 0) return null
                const h = count * yScale
                yBase -= h
                return (
                  <rect key={t} x={x} y={yBase} width={BAR_W} height={h}
                        fill={TYPE_COLORS[t]} rx={1}>
                    <title>{entry.date} {TYPE_LABELS[t]}: {count.toLocaleString()}</title>
                  </rect>
                )
              })}
              {total > 0 && (
                <text x={x + BAR_W / 2} y={PAD.top + PLOT_H - total * yScale - 3}
                      textAnchor="middle" fontSize={9} fill="#555">
                  {fmtViews(total)}
                </text>
              )}
              <text x={x + BAR_W / 2} y={PAD.top + PLOT_H + 14}
                    textAnchor="end" fontSize={9} fill="#888"
                    transform={`rotate(-45, ${x + BAR_W / 2}, ${PAD.top + PLOT_H + 14})`}>
                {entry.date.slice(5)}
              </text>
            </g>
          )
        })}
      </svg>

      <div style={{ display: 'flex', gap: 16, marginTop: 4, fontSize: 12, color: '#666' }}>
        {types.map(t => (
          <span key={t} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <span style={{ width: 12, height: 12, borderRadius: 2, backgroundColor: TYPE_COLORS[t], display: 'inline-block' }} />
            {TYPE_LABELS[t]}
          </span>
        ))}
      </div>
    </div>
  )
}

// ----------------------------------------------------------------
// 月別再生数内訳チャート
// ----------------------------------------------------------------

function MonthlyViewsChart({ data }: { data: MonthlyViewsEntry[] }) {
  const wrapperRef = useRef<HTMLDivElement>(null)
  const [containerW, setContainerW] = useState(600)

  useEffect(() => {
    const el = wrapperRef.current
    if (!el) return
    const update = () => setContainerW(el.clientWidth)
    update()
    const ro = new ResizeObserver(update)
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  if (data.length === 0) return <p className="muted">月別再生数データがありません</p>

  const types: VideoType[] = ['Movie', 'Short', 'LiveArchive']
  const maxTotal = Math.max(...data.map(d => d.Movie + d.Short + d.LiveArchive), 1)

  const PAD = { top: 24, right: 16, bottom: 48, left: 56 }
  const PLOT_H = 180
  const BAR_SLOT = Math.max(32, Math.floor((containerW - PAD.left - PAD.right) / data.length))
  const BAR_W = Math.min(28, BAR_SLOT - 4)
  const svgW = Math.max(containerW, PAD.left + PAD.right + data.length * BAR_SLOT)
  const svgH = PAD.top + PLOT_H + PAD.bottom

  const { ticks } = niceScale(0, maxTotal, 5)
  const yScale = PLOT_H / maxTotal

  return (
    <div ref={wrapperRef} style={{ overflowX: 'auto' }}>
      <svg width={svgW} height={svgH} style={{ fontFamily: 'inherit', display: 'block' }}>
        {ticks.map(tick => {
          const y = PAD.top + PLOT_H - tick * yScale
          return (
            <g key={tick}>
              <line x1={PAD.left} y1={y} x2={PAD.left + data.length * BAR_SLOT} y2={y}
                    stroke={tick === 0 ? '#555' : '#e0e3f5'} strokeWidth={1} />
              <text x={PAD.left - 4} y={y + 4} textAnchor="end" fontSize={10} fill="#888">
                {fmtViews(tick)}
              </text>
            </g>
          )
        })}

        {data.map((entry, i) => {
          const x = PAD.left + i * BAR_SLOT + (BAR_SLOT - BAR_W) / 2
          let yBase = PAD.top + PLOT_H
          const total = entry.Movie + entry.Short + entry.LiveArchive
          return (
            <g key={entry.month}>
              {types.map(t => {
                const count = entry[t]
                if (count === 0) return null
                const h = count * yScale
                yBase -= h
                return (
                  <rect key={t} x={x} y={yBase} width={BAR_W} height={h}
                        fill={TYPE_COLORS[t]} rx={1}>
                    <title>{entry.month} {TYPE_LABELS[t]}: {count.toLocaleString()}</title>
                  </rect>
                )
              })}
              {total > 0 && (
                <text x={x + BAR_W / 2} y={PAD.top + PLOT_H - total * yScale - 3}
                      textAnchor="middle" fontSize={9} fill="#555">
                  {fmtViews(total)}
                </text>
              )}
              <text x={x + BAR_W / 2} y={PAD.top + PLOT_H + 14}
                    textAnchor="end" fontSize={9} fill="#888"
                    transform={`rotate(-45, ${x + BAR_W / 2}, ${PAD.top + PLOT_H + 14})`}>
                {entry.month.slice(5)}月
              </text>
            </g>
          )
        })}
      </svg>

      <div style={{ display: 'flex', gap: 16, marginTop: 4, fontSize: 12, color: '#666' }}>
        {types.map(t => (
          <span key={t} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <span style={{ width: 12, height: 12, borderRadius: 2, backgroundColor: TYPE_COLORS[t], display: 'inline-block' }} />
            {TYPE_LABELS[t]}
          </span>
        ))}
      </div>
    </div>
  )
}

// ----------------------------------------------------------------
// 分析タブ
// ----------------------------------------------------------------

function AnalysisTab({ history, talentName, flags }: {
  history: AllHistory
  talentName: string
  flags: VideoFlags
}) {
  const calendarData      = buildPostingCalendar(history, talentName, flags)
  const velocityItems     = buildVelocityCurveData(history, talentName, flags)
  const dailyViewsData    = buildDailyViewsBreakdown(history, talentName, flags, 15)
  const monthlyViewsData  = buildMonthlyViewsBreakdown(history, talentName, flags)

  const years = [...new Set(calendarData.map(d => d.month.slice(0, 4)))].sort()
  const [selectedYear, setSelectedYear] = useState<string>(years.at(-1) ?? '')
  const filteredCalendar = selectedYear
    ? calendarData.filter(d => d.month.startsWith(selectedYear))
    : calendarData

  const monthlyYears = [...new Set(monthlyViewsData.map(d => d.month.slice(0, 4)))].sort()
  const [selectedMonthlyYear, setSelectedMonthlyYear] = useState<string>(monthlyYears.at(-1) ?? '')
  const filteredMonthlyViews = selectedMonthlyYear
    ? monthlyViewsData.filter(d => d.month.startsWith(selectedMonthlyYear))
    : monthlyViewsData

  return (
    <div style={{ marginTop: 16 }}>
      <h3 style={{ marginBottom: 8 }}>直近15日の再生数内訳（種別×日付）</h3>
      <DailyViewsChart data={dailyViewsData} />

      <h3 style={{ marginTop: 32, marginBottom: 8 }}>月別再生数内訳（種別×月）</h3>
      {monthlyYears.length > 1 && (
        <select
          value={selectedMonthlyYear}
          onChange={e => setSelectedMonthlyYear(e.target.value)}
          style={{ marginBottom: 12, padding: '4px 8px', fontSize: 13, borderRadius: 4, border: '1px solid #ccc' }}
        >
          {monthlyYears.map(y => <option key={y} value={y}>{y}年</option>)}
        </select>
      )}
      <MonthlyViewsChart data={filteredMonthlyViews} />

      <h3 style={{ marginTop: 32, marginBottom: 8 }}>投稿ペース（種別×月別）</h3>
      {years.length > 1 && (
        <select
          value={selectedYear}
          onChange={e => setSelectedYear(e.target.value)}
          style={{ marginBottom: 12, padding: '4px 8px', fontSize: 13, borderRadius: 4, border: '1px solid #ccc' }}
        >
          {years.map(y => <option key={y} value={y}>{y}年</option>)}
        </select>
      )}
      <PostingCalendarChart data={filteredCalendar} />

      <h3 style={{ marginTop: 32, marginBottom: 8 }}>初速カーブ（直近Movie 最大10本）</h3>
      <p style={{ fontSize: 12, color: '#888', marginBottom: 8 }}>
        公開日を0日として、その後の再生数の伸びを比較します。
      </p>
      <VelocityCurveChart items={velocityItems} />
    </div>
  )
}

// ----------------------------------------------------------------
// メインコンポーネント
// ----------------------------------------------------------------

export default function TalentPage({ history, talentName, flags, comments }: Props) {
  const { stats, diff } = getLatestChannelStats(history, talentName)
  const allVideos = buildTalentVideoList(history, talentName, flags)

  const videoByType: Record<VideoType, VideoCard[]> = { Movie: [], Short: [], LiveArchive: [] }
  for (const v of allVideos) {
    if (v.type in videoByType) videoByType[v.type].push(v)
  }

  const activeTabs: { type: TabType; label: string }[] = [
    ...VIDEO_TABS.filter(t => videoByType[t.type].length > 0),
    { type: '分析', label: '分析' },
  ]

  const [activeType, setActiveType] = useState<TabType>(activeTabs[0]?.type ?? 'Movie')
  const [sortKey, setSortKey] = useState<SortKey>('再生数')
  const [collabOnly, setCollabOnly] = useState(false)

  const talentComments = comments[talentName] ?? {}

  function fmtStatDiff(v: number | null) {
    if (v === null) return null
    const sign = v >= 0 ? '+' : ''
    return <span style={{ fontSize: 13, color: diffColor(v), marginLeft: 6 }}>({sign}{v.toLocaleString()})</span>
  }

  const currentVideos = activeType !== '分析' ? videoByType[activeType as VideoType] : []
  const filtered = collabOnly ? currentVideos.filter(v => v.collab_tags.length > 0) : currentVideos

  const sorted = [...filtered].sort((a, b) => {
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
                onClick={() => { setActiveType(t.type); setSortKey('再生数'); setCollabOnly(false) }}
              >
                {t.label}
                {t.type !== '分析' && (
                  <span className="tab-count">({videoByType[t.type as VideoType].length})</span>
                )}
              </button>
            ))}
          </div>

          {activeType === '分析' ? (
            <AnalysisTab history={history} talentName={talentName} flags={flags} />
          ) : (
            <>
              {/* ソート＋コラボフィルター */}
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, alignItems: 'center', margin: '8px 0' }}>
                <div className="sort-btns" style={{ margin: 0 }}>
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
                <button
                  className={`sort-btn${collabOnly ? ' active' : ''}`}
                  onClick={() => setCollabOnly(o => !o)}
                >
                  🤝 コラボのみ
                </button>
              </div>

              {/* 動画カード */}
              <div className="video-list">
                {sorted.map(v => (
                  <VideoCardItem
                    key={v.id}
                    video={v}
                    commentData={talentComments[v.id]}
                  />
                ))}
              </div>
            </>
          )}
        </>
      )}
    </div>
  )
}
