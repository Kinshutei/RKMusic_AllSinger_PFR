import { useState, useRef, useEffect } from 'react'
import { AllHistory, SingerRankItem, VideoRankItem, VideoType, VideoFlags } from '../types'
import { buildDashboardData, buildStatsData } from '../utils/data'
import { niceScale, fmtDiff, diffColor } from '../utils/chartUtils'

interface Props {
  history: AllHistory
  flags: VideoFlags
}

function SingerTable({ rows, valKey, diffKey, rateKey }: {
  rows: SingerRankItem[]
  valKey: 'subs_n' | 'views_n' | 'comments_n'
  diffKey: 'subs_diff' | 'views_diff' | 'comments_diff'
  rateKey: 'subs_rate' | 'views_rate' | 'comments_rate'
}) {
  const sorted = [...rows].sort((a, b) => (b[diffKey] ?? -999999) - (a[diffKey] ?? -999999))
  const totalVal = sorted.reduce((sum, r) => sum + r[valKey], 0)
  const totalDiff = sorted.every(r => r[diffKey] === null)
    ? null
    : sorted.reduce((sum, r) => sum + (r[diffKey] ?? 0), 0)
  const totalRate = totalDiff !== null && totalVal - totalDiff > 0
    ? Math.round(totalDiff / (totalVal - totalDiff) * 1000) / 10
    : null
  return (
    <table className="rank-table">
      <tbody>
        {sorted.map((r, i) => (
          <tr key={r.talent} className={i % 2 === 0 ? 'row-even' : ''}>
            <td className="rank-no">{i + 1}.</td>
            <td className="rank-name">{r.talent}</td>
            <td className="rank-val">{r[valKey].toLocaleString()}</td>
            <td className="rank-diff" style={{ color: diffColor(r[diffKey]) }}>
              {fmtDiff(r[diffKey], r[rateKey])}
            </td>
          </tr>
        ))}
        <tr style={{ borderTop: '2px solid #555', fontWeight: 'bold' }}>
          <td className="rank-no"></td>
          <td className="rank-name">合計</td>
          <td className="rank-val">{totalVal.toLocaleString()}</td>
          <td className="rank-diff" style={{ color: diffColor(totalDiff) }}>
            {fmtDiff(totalDiff, totalRate)}
          </td>
        </tr>
      </tbody>
    </table>
  )
}

function VideoTable({ rows, valKey, diffKey, rateKey, top = 20 }: {
  rows: VideoRankItem[]
  valKey: 'views_n' | 'likes_n' | 'comments_n'
  diffKey: 'views_diff' | 'likes_diff' | 'comments_diff'
  rateKey?: 'views_rate'
  top?: number
}) {
  const sorted = [...rows]
    .sort((a, b) => (b[diffKey] ?? -999999) - (a[diffKey] ?? -999999))
    .slice(0, top)
  return (
    <table className="rank-table">
      <tbody>
        {sorted.map((r, i) => (
          <tr key={r.vid_id} className={i % 2 === 0 ? 'row-even' : ''}>
            <td className="rank-no">{i + 1}.</td>
            <td className="rank-name">
              <span className="rank-talent">{r.talent}</span>
              <a
                href={`https://www.youtube.com/watch?v=${r.vid_id}`}
                target="_blank" rel="noopener noreferrer"
                title={r.title}
              >
                {r.title.length > 22 ? r.title.slice(0, 22) + '…' : r.title}
              </a>
            </td>
            <td className="rank-val">{r[valKey].toLocaleString()}</td>
            <td className="rank-diff" style={{ color: diffColor(r[diffKey]) }}>
              {fmtDiff(r[diffKey], rateKey ? r[rateKey] : undefined)}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

type StatsPoint = { date: string; subs: number; views: number }

function fmtY(v: number): string {
  if (v === 0) return '0'
  const abs = Math.abs(v)
  const sign = v < 0 ? '-' : ''
  if (abs >= 1_000_000_000) return `${sign}${(abs / 1_000_000_000).toFixed(1)}B`
  if (abs >= 1_000_000)     return `${sign}${(abs / 1_000_000).toFixed(1)}M`
  if (abs >= 1_000)         return `${sign}${Math.round(abs / 1_000)}K`
  return String(v)
}

function TotalBarChart({ points, yKey, title }: {
  points: StatsPoint[]
  yKey: 'subs' | 'views'
  title: string
}) {
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

  const dates = points.map(p => p.date)
  const values = points.map(p => p[yKey])

  const PADDING = { top: 20, right: 20, bottom: 60, left: 72 }
  const plotH = 260
  const minBarSlot = 20
  const naturalW = PADDING.left + PADDING.right + dates.length * minBarSlot
  const svgW = Math.max(containerW, naturalW)
  const plotW = svgW - PADDING.left - PADDING.right
  const barSlot = plotW / (dates.length || 1)
  const barW = Math.min(barSlot - 4, 40)
  const svgH = PADDING.top + plotH + PADDING.bottom

  const { ticks, niceMin, niceMax } = niceScale(Math.min(...values), Math.max(...values), 6)
  const displayRange = niceMax - niceMin || 1
  const sy = (v: number) => PADDING.top + plotH - ((v - niceMin) / displayRange) * plotH
  const zeroY = sy(0)
  const labelStep = Math.ceil(dates.length / 30)

  return (
    <div style={{ marginBottom: 32 }}>
      <div className="col-label">{title}</div>
      <div ref={wrapperRef} style={{ overflowX: 'auto', marginTop: 8 }}>
        <svg width={svgW} height={svgH} style={{ fontFamily: 'inherit', display: 'block' }}>
          {ticks.map((tick) => {
            const y = sy(tick)
            return (
              <g key={tick}>
                <line x1={PADDING.left} y1={y} x2={PADDING.left + plotW} y2={y}
                      stroke={tick === 0 ? '#888' : '#e0e3f5'} strokeWidth={1} />
                <text x={PADDING.left - 6} y={y + 4} textAnchor="end" fontSize={10} fill="#888">
                  {fmtY(tick)}
                </text>
              </g>
            )
          })}
          {dates.map((date, i) => {
            const v = values[i]
            const bTop = Math.min(sy(v), zeroY)
            const bH = Math.max(Math.abs(sy(v) - zeroY), 1)
            const x = PADDING.left + barSlot * i + (barSlot - barW) / 2
            const showLabel = dates.length <= 30 || i % labelStep === 0
            return (
              <g key={date}>
                <rect x={x} y={bTop} width={barW} height={bH} fill="#6677cc" rx={2}>
                  <title>{date}: {v.toLocaleString()}</title>
                </rect>
                {showLabel && (
                  <text
                    x={x + barW / 2} y={PADDING.top + plotH + 10}
                    textAnchor="end" fontSize={9} fill="#888"
                    transform={`rotate(-45, ${x + barW / 2}, ${PADDING.top + plotH + 10})`}
                  >
                    {date.slice(5)}
                  </text>
                )}
              </g>
            )
          })}
          <line x1={PADDING.left} y1={PADDING.top} x2={PADDING.left} y2={PADDING.top + plotH}
                stroke="#888" strokeWidth={1} />
          <text
            x={14} y={PADDING.top + plotH / 2}
            textAnchor="middle" fontSize={10} fill="#3a4580"
            transform={`rotate(-90, 14, ${PADDING.top + plotH / 2})`}
          >
            {title}
          </text>
        </svg>
      </div>
    </div>
  )
}

function ContentTable({ rows }: { rows: SingerRankItem[] }) {
  const sorted = [...rows].sort((a, b) => b.content_total - a.content_total)
  const total = sorted.reduce((s, r) => s + r.content_total, 0)
  const totalDiff = sorted.every(r => r.content_diff === null)
    ? null
    : sorted.reduce((s, r) => s + (r.content_diff ?? 0), 0)
  const totalRate = totalDiff !== null && total - totalDiff > 0
    ? Math.round(totalDiff / (total - totalDiff) * 1000) / 10
    : null
  return (
    <table className="rank-table">
      <tbody>
        {sorted.map((r, i) => (
          <tr key={r.talent} className={i % 2 === 0 ? 'row-even' : ''}>
            <td className="rank-no">{i + 1}.</td>
            <td className="rank-name">{r.talent}</td>
            <td className="rank-val">{r.content_total.toLocaleString()}</td>
            <td className="rank-diff" style={{ color: diffColor(r.content_diff) }}>
              {fmtDiff(r.content_diff, r.content_rate)}
            </td>
          </tr>
        ))}
        <tr style={{ borderTop: '2px solid #555', fontWeight: 'bold' }}>
          <td className="rank-no"></td>
          <td className="rank-name">合計</td>
          <td className="rank-val">{total.toLocaleString()}</td>
          <td className="rank-diff" style={{ color: diffColor(totalDiff) }}>
            {fmtDiff(totalDiff, totalRate)}
          </td>
        </tr>
      </tbody>
    </table>
  )
}

const VIDEO_SECTIONS: { type: VideoType; label: string }[] = [
  { type: 'Movie',       label: '動画部門' },
  { type: 'Short',       label: 'ショート部門' },
  { type: 'LiveArchive', label: 'ライブ部門' },
]

export default function DashboardPage({ history, flags }: Props) {
  const [view, setView] = useState<'ranking' | 'stats'>('ranking')
  const [statsMode, setStatsMode] = useState<'cumulative' | 'increment'>('cumulative')
  const data = buildDashboardData(history, flags)
  const statsPoints = buildStatsData(history)

  const incrementPoints: StatsPoint[] = statsPoints.slice(1).map((p, i) => ({
    date: p.date,
    subs:  p.subs  - statsPoints[i].subs,
    views: p.views - statsPoints[i].views,
  }))
  const chartPoints = statsMode === 'cumulative' ? statsPoints : incrementPoints

  return (
    <div>
      <div className="tabs">
        <button className={`type-tab-btn${view === 'ranking' ? ' active' : ''}`} onClick={() => setView('ranking')}>ランキング</button>
        <button className={`type-tab-btn${view === 'stats'   ? ' active' : ''}`} onClick={() => setView('stats')}>Statistics</button>
      </div>

      {view === 'stats' ? (
        <div style={{ marginTop: 16 }}>
          <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
            <button className={`sort-btn${statsMode === 'cumulative' ? ' active' : ''}`} onClick={() => setStatsMode('cumulative')}>累計</button>
            <button className={`sort-btn${statsMode === 'increment'  ? ' active' : ''}`} onClick={() => setStatsMode('increment')}>増加分</button>
          </div>
          <TotalBarChart points={chartPoints} yKey="subs"  title={statsMode === 'cumulative' ? '登録者数（累計）' : '登録者数（日次増加）'} />
          <TotalBarChart points={chartPoints} yKey="views" title={statsMode === 'cumulative' ? '総再生数（累計）' : '総再生数（日次増加）'} />
        </div>
      ) : !data ? (
        <p className="muted">データがありません</p>
      ) : (
        <>
          <p className="date-label">集計基準日: {data.n_date}（前日比）</p>

          {/* Singer別 */}
          <h3>Singer別</h3>
          <div className="four-col">
            <div>
              <div className="col-label">登録者数</div>
              <SingerTable rows={data.singerData} valKey="subs_n" diffKey="subs_diff" rateKey="subs_rate" />
            </div>
            <div>
              <div className="col-label">総再生数</div>
              <SingerTable rows={data.singerData} valKey="views_n" diffKey="views_diff" rateKey="views_rate" />
            </div>
            <div>
              <div className="col-label">総コメント数</div>
              <SingerTable rows={data.singerData} valKey="comments_n" diffKey="comments_diff" rateKey="comments_rate" />
            </div>
            <div>
              <div className="col-label">総コンテンツ数</div>
              <ContentTable rows={data.singerData} />
            </div>
          </div>

          {/* 動画部門 */}
          {VIDEO_SECTIONS.map(({ type, label }) => {
            const rows = data.videoData[type]
            if (!rows.length) return null
            return (
              <div key={type}>
                <h3>{label}</h3>
                <div className="three-col">
                  <div>
                    <div className="col-label">再生数</div>
                    <VideoTable rows={rows} valKey="views_n" diffKey="views_diff" rateKey="views_rate" />
                  </div>
                  <div>
                    <div className="col-label">高評価数</div>
                    <VideoTable rows={rows} valKey="likes_n" diffKey="likes_diff" />
                  </div>
                  <div>
                    <div className="col-label">コメント数</div>
                    <VideoTable rows={rows} valKey="comments_n" diffKey="comments_diff" />
                  </div>
                </div>
              </div>
            )
          })}
        </>
      )}
    </div>
  )
}
