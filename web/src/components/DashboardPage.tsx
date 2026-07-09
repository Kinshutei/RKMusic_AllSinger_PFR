import { useState, useRef, useEffect } from 'react'
import Plot from 'react-plotly.js'
import { DashboardSummary, SingerRankItem, VideoRankItem, VideoType, VideoFlags } from '../types'
import { buildDashboardData, buildStatsData, buildDailyViewsByTalent, buildDashboardDailyViewsBreakdown, DailyViewsEntry } from '../utils/data'
import { niceScale, fmtDiff, diffColor } from '../utils/chartUtils'

interface Props {
  summary: DashboardSummary
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

function DualAxisChart({ statsPoints, incrementPoints, yKey, title }: {
  statsPoints: StatsPoint[]
  incrementPoints: StatsPoint[]
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

  const dates = incrementPoints.map(p => p.date)
  const barValues = incrementPoints.map(p => p[yKey])
  const lineValues = statsPoints.slice(1).map(p => p[yKey])

  const PADDING = { top: 20, right: 72, bottom: 60, left: 72 }
  const plotH = 260
  const minBarSlot = 40
  const naturalW = PADDING.left + PADDING.right + dates.length * minBarSlot
  const svgW = Math.max(containerW, naturalW)
  const plotW = svgW - PADDING.left - PADDING.right
  const barSlot = plotW / (dates.length || 1)
  const barW = Math.min(barSlot - 4, 40)
  const svgH = PADDING.top + plotH + PADDING.bottom

  const { ticks: ticksL, niceMin: niceMinL, niceMax: niceMaxL } = niceScale(Math.min(0, ...barValues), Math.max(...barValues), 5)
  const displayRangeL = niceMaxL - niceMinL || 1
  const syL = (v: number) => PADDING.top + plotH - ((v - niceMinL) / displayRangeL) * plotH
  const zeroY = syL(0)

  const { ticks: ticksR, niceMin: niceMinR, niceMax: niceMaxR } = niceScale(Math.min(...lineValues), Math.max(...lineValues), 5)
  const displayRangeR = niceMaxR - niceMinR || 1
  const syR = (v: number) => PADDING.top + plotH - ((v - niceMinR) / displayRangeR) * plotH

  const linePath = lineValues.map((v, i) => {
    const x = PADDING.left + barSlot * i + barSlot / 2
    return `${i === 0 ? 'M' : 'L'} ${x} ${syR(v)}`
  }).join(' ')

  return (
    <div style={{ marginBottom: 32 }}>
      <div className="col-label">{title}</div>
      <div ref={wrapperRef} style={{ overflowX: 'auto', marginTop: 8 }}>
        <svg width={svgW} height={svgH} style={{ fontFamily: 'inherit', display: 'block' }}>
          {ticksL.map((tick) => {
            const y = syL(tick)
            return (
              <g key={tick}>
                <line x1={PADDING.left} y1={y} x2={PADDING.left + plotW} y2={y}
                      stroke={tick === 0 ? '#888' : '#e0e3f5'} strokeWidth={1} />
                <text x={PADDING.left - 6} y={y + 4} textAnchor="end" fontSize={10} fill="#6677cc">
                  {fmtY(tick)}
                </text>
              </g>
            )
          })}
          {ticksR.map((tick) => (
            <text key={tick} x={PADDING.left + plotW + 6} y={syR(tick) + 4}
                  textAnchor="start" fontSize={10} fill="#cc4455">
              {fmtY(tick)}
            </text>
          ))}
          {dates.map((date, i) => {
            const v = barValues[i]
            const bTop = Math.min(syL(v), zeroY)
            const bH = Math.max(Math.abs(syL(v) - zeroY), 1)
            const x = PADDING.left + barSlot * i + (barSlot - barW) / 2
            const showLabel = true
            return (
              <g key={date}>
                <rect x={x} y={bTop} width={barW} height={bH} fill="rgba(102,119,204,0.7)" rx={2}>
                  <title>{date} 増加: {v.toLocaleString()}</title>
                </rect>
                {showLabel && v !== 0 && (
                  <text x={x + barW / 2} y={bTop - 3}
                        textAnchor="middle" fontSize={9} fill="#6677cc">
                    {fmtY(v)}
                  </text>
                )}
                {showLabel && (
                  <text x={x + barW / 2} y={PADDING.top + plotH + 10}
                        textAnchor="end" fontSize={9} fill="#888"
                        transform={`rotate(-45, ${x + barW / 2}, ${PADDING.top + plotH + 10})`}>
                    {date.slice(5)}
                  </text>
                )}
              </g>
            )
          })}
          <path d={linePath} fill="none" stroke="#cc4455" strokeWidth={2} />
          {lineValues.map((v, i) => (
            <circle key={i} cx={PADDING.left + barSlot * i + barSlot / 2} cy={syR(v)} r={2} fill="#cc4455">
              <title>{dates[i]} 累計: {v.toLocaleString()}</title>
            </circle>
          ))}
          <line x1={PADDING.left} y1={PADDING.top} x2={PADDING.left} y2={PADDING.top + plotH}
                stroke="#6677cc" strokeWidth={1.5} />
          <line x1={PADDING.left + plotW} y1={PADDING.top} x2={PADDING.left + plotW} y2={PADDING.top + plotH}
                stroke="#cc4455" strokeWidth={1.5} />
          <text x={12} y={PADDING.top + plotH / 2} textAnchor="middle" fontSize={10} fill="#6677cc"
                transform={`rotate(-90, 12, ${PADDING.top + plotH / 2})`}>増加分</text>
          <text x={svgW - 10} y={PADDING.top + plotH / 2} textAnchor="middle" fontSize={10} fill="#cc4455"
                transform={`rotate(90, ${svgW - 10}, ${PADDING.top + plotH / 2})`}>累計</text>
        </svg>
      </div>
    </div>
  )
}

const PIE_COLORS = { Movie: '#6677cc', Short: '#cc4455', LiveArchive: '#44aa77' }
const PIE_LABELS = { Movie: '動画', Short: 'ショート', LiveArchive: 'ライブ' }

function DashboardDailyViewsChart({ data, title }: { data: DailyViewsEntry[]; title: string }) {
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

  const types = ['Movie', 'Short', 'LiveArchive'] as const
  const maxTotal = Math.max(...data.map(d => d.Movie + d.Short + d.LiveArchive), 1)

  const PAD = { top: 20, right: 16, bottom: 60, left: 72 }
  const PLOT_H = 260
  const minBarSlot = 40
  const naturalW = PAD.left + PAD.right + data.length * minBarSlot
  const svgW = Math.max(containerW, naturalW)
  const barSlot = (svgW - PAD.left - PAD.right) / (data.length || 1)
  const barW = Math.min(barSlot - 4, 40)
  const svgH = PAD.top + PLOT_H + PAD.bottom

  const { ticks } = niceScale(0, maxTotal, 5)
  const yScale = PLOT_H / maxTotal

  return (
    <div style={{ marginBottom: 32 }}>
      <div className="col-label">{title}</div>
      <div ref={wrapperRef} style={{ overflowX: 'auto', marginTop: 8 }}>
        <svg width={svgW} height={svgH} style={{ fontFamily: 'inherit', display: 'block' }}>
          {ticks.map(tick => {
            const y = PAD.top + PLOT_H - tick * yScale
            return (
              <g key={tick}>
                <line x1={PAD.left} y1={y} x2={PAD.left + data.length * barSlot} y2={y}
                      stroke={tick === 0 ? '#888' : '#e0e3f5'} strokeWidth={1} />
                <text x={PAD.left - 6} y={y + 4} textAnchor="end" fontSize={10} fill="#888">
                  {fmtY(tick)}
                </text>
              </g>
            )
          })}
          {data.map((entry, i) => {
            const x = PAD.left + barSlot * i + (barSlot - barW) / 2
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
                    <rect key={t} x={x} y={yBase} width={barW} height={h}
                          fill={PIE_COLORS[t]} rx={1}>
                      <title>{entry.date} {PIE_LABELS[t]}: {count.toLocaleString()}</title>
                    </rect>
                  )
                })}
                {total > 0 && (
                  <text x={x + barW / 2} y={PAD.top + PLOT_H - total * yScale - 3}
                        textAnchor="middle" fontSize={9} fill="#555">
                    {fmtY(total)}
                  </text>
                )}
                <text x={x + barW / 2} y={PAD.top + PLOT_H + 10}
                      textAnchor="end" fontSize={9} fill="#888"
                      transform={`rotate(-45, ${x + barW / 2}, ${PAD.top + PLOT_H + 10})`}>
                  {entry.date.slice(5)}
                </text>
              </g>
            )
          })}
        </svg>
        <div style={{ display: 'flex', gap: 16, marginTop: 4, fontSize: 12, color: '#666' }}>
          {types.map(t => (
            <span key={t} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              <span style={{ width: 12, height: 12, borderRadius: 2, backgroundColor: PIE_COLORS[t], display: 'inline-block' }} />
              {PIE_LABELS[t]}
            </span>
          ))}
        </div>
      </div>
    </div>
  )
}

const GROUP_DEFS = [
  { label: 'LIVE UNION', members: ['焔魔るり', 'HACHI', '瀬戸乃とと', '水瀬凪'],     color: '#2a305c' },
  { label: 'KMN LABEL',  members: ['KMNZ', 'HONK THE HORN'],                          color: '#363d74' },
  { label: 'VB+NJ',      members: ['VESPERBELL', 'NUROJUNK'],                          color: '#3a4580' },
  { label: 'Fused',      members: ['CULUA', 'CONA', '妃玖', 'Diα'],                   color: '#4455aa' },
  { label: 'GRAY MYTH',  members: ['MEMESIA', 'LEWNE', '羽緒', 'Cil', '深影'],        color: '#6677cc' },
  { label: 'その他',     members: ['NEUN', 'MEDA', 'IMI', 'XIDEN', 'ヨノ', 'wouca'],  color: '#8899c0' },
]
function GroupTreemap({ talentViews, date }: {
  talentViews: Record<string, number>
  date: string
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

  const ids: string[] = []
  const labels: string[] = []
  const parents: string[] = []
  const values: number[] = []
  const markerColors: string[] = []

  const grandTotal = GROUP_DEFS.reduce((s, g) =>
    s + g.members.reduce((s2, m) => s2 + (talentViews[m] ?? 0), 0), 0)
  if (grandTotal === 0) return null

  const groupTotals = GROUP_DEFS.map(g =>
    g.members.reduce((s, m) => s + (talentViews[m] ?? 0), 0))
  const maxT = Math.max(...groupTotals)
  const minT = Math.min(...groupTotals.filter(t => t > 0))
  const navyShade = (total: number) => {
    const ratio = maxT > minT ? (total - minT) / (maxT - minT) : 1
    const r = Math.round(0x88 + (0x2a - 0x88) * ratio)
    const g = Math.round(0x99 + (0x30 - 0x99) * ratio)
    const b = Math.round(0xc0 + (0x5c - 0xc0) * ratio)
    return `#${r.toString(16).padStart(2,'0')}${g.toString(16).padStart(2,'0')}${b.toString(16).padStart(2,'0')}`
  }

  GROUP_DEFS.forEach((g, gi) => {
    const groupTotal = groupTotals[gi]
    const groupPct = (groupTotal / grandTotal * 100).toFixed(1)
    const color = navyShade(groupTotal)
    ids.push(g.label)
    labels.push(`${g.label} ${groupPct}%`)
    parents.push('')
    values.push(groupTotal)
    markerColors.push(color)
    g.members.forEach(m => {
      const mv = talentViews[m] ?? 0
      ids.push(m)
      labels.push(m)
      parents.push(g.label)
      values.push(mv)
      markerColors.push(color + '99')
    })
  })

  const plotH = Math.round(Math.max(300, Math.min(700, containerW * 0.65)))

  return (
    <div style={{ marginBottom: 32 }}>
      <div className="col-label">当日増加再生数のグループ内訳（{date}）</div>
      <div ref={wrapperRef}>
        <Plot
          data={[{
            type: 'treemap',
            ids,
            labels,
            parents,
            values,
            branchvalues: 'total',
            marker: { colors: markerColors },
            textinfo: 'label+percent root',
            textfont: { color: '#ffffff' },
            hovertemplate: '%{label}: %{value:,}<extra></extra>',
          } as any]}
          layout={{
            width: containerW,
            height: plotH,
            margin: { t: 0, b: 0, l: 0, r: 0 },
          }}
          config={{ displayModeBar: false }}
        />
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

export default function DashboardPage({ summary, flags }: Props) {
  const [view, setView] = useState<'ranking' | 'stats'>('ranking')
  const data = buildDashboardData(summary, flags)
  const statsPoints = buildStatsData(summary)
  const dailyViewsByTalent = buildDailyViewsByTalent(summary)

  const incrementPoints: StatsPoint[] = statsPoints.slice(1).map((p, i) => ({
    date: p.date,
    subs:  p.subs  - statsPoints[i].subs,
    views: p.views - statsPoints[i].views,
  }))

  const allDailyViews = buildDashboardDailyViewsBreakdown(summary)

  const availableMonths = [...new Set(incrementPoints.map(p => p.date.slice(0, 7)))].sort()
  const [selectedMonth, setSelectedMonth] = useState<string>(availableMonths.at(-1) ?? '')

  const monthStartIdx = incrementPoints.findIndex(p => p.date.startsWith(selectedMonth))
  const monthEndIdx   = [...incrementPoints].reverse().findIndex(p => p.date.startsWith(selectedMonth))
  const monthEnd      = monthEndIdx === -1 ? -1 : incrementPoints.length - 1 - monthEndIdx
  const filteredIncrements = monthStartIdx !== -1 ? incrementPoints.slice(monthStartIdx, monthEnd + 1) : incrementPoints
  // statsPointsはincrementPointsより1つ先行するため、月頭の前日累計値も含めてスライス
  const filteredStats = monthStartIdx !== -1 ? statsPoints.slice(monthStartIdx, monthEnd + 2) : statsPoints

  const filteredDailyViews = allDailyViews.filter(d => d.date.startsWith(selectedMonth))

  return (
    <div>
      <div className="tabs">
        <button className={`type-tab-btn${view === 'ranking' ? ' active' : ''}`} onClick={() => setView('ranking')}>ランキング</button>
        <button className={`type-tab-btn${view === 'stats'   ? ' active' : ''}`} onClick={() => setView('stats')}>Statistics</button>
      </div>

      {view === 'stats' ? (
        <div style={{ marginTop: 16 }}>
          <div style={{ marginBottom: 16 }}>
            <select
              value={selectedMonth}
              onChange={e => setSelectedMonth(e.target.value)}
              style={{ padding: '4px 8px', fontSize: 13, borderRadius: 4, border: '1px solid #ccc' }}
            >
              {availableMonths.map(m => {
                const [y, mo] = m.split('-')
                return <option key={m} value={m}>{y}年{parseInt(mo)}月</option>
              })}
            </select>
          </div>
          <DualAxisChart statsPoints={filteredStats} incrementPoints={filteredIncrements} yKey="subs" title="登録者数" />
          <DashboardDailyViewsChart data={filteredDailyViews} title="総再生数（種別内訳）" />
          {dailyViewsByTalent && <GroupTreemap talentViews={dailyViewsByTalent.views} date={dailyViewsByTalent.date} />}
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
