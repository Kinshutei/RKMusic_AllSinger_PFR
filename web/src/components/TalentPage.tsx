import { useState, useRef, useEffect } from 'react'
import { AllHistory, VideoCard, VideoHistoryEntry, VideoType } from '../types'
import { getLatestChannelStats, buildTalentVideoList } from '../utils/data'

interface Props {
  history: AllHistory
  talentName: string
}

type SortKey = '再生数' | '高評価数' | '再生数15d増加' | '高評価15d増加'
type TabType = VideoType | 'Statistics'
type StatsMetric = '再生数' | '高評価数'

const SORT_OPTIONS: { key: SortKey; label: string }[] = [
  { key: '再生数',       label: '📊 再生数TOP' },
  { key: '高評価数',     label: '👍 高評価TOP' },
  { key: '再生数15d増加', label: '📈 再生15日増加' },
  { key: '高評価15d増加', label: '💹 高評価15日増加' },
]

const ALL_TABS: { type: TabType; label: string }[] = [
  { type: 'Movie',       label: '動画' },
  { type: 'Short',       label: 'ショート' },
  { type: 'LiveArchive', label: 'ライブ' },
  { type: 'Statistics',  label: 'Statistics' },
]

function fmtDiff(v: number | null): string {
  if (v === null) return '—'
  return v >= 0 ? `+${v.toLocaleString()}` : v.toLocaleString()
}

function diffColor(v: number | null): string {
  if (v === null) return '#aaa'
  return v > 0 ? '#2e7d5a' : v < 0 ? '#c0392b' : '#888'
}

// ── SVG棒グラフ ───────────────────────────────────────────────────────────────
function BarChart({ dates, values, metric }: { dates: string[]; values: number[]; metric: string }) {
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

  const PADDING = { top: 20, right: 20, bottom: 60, left: 72 }
  const plotH = 260
  // バーが多い場合はスクロール、少ない場合はコンテナ幅いっぱいに広げる
  const minBarSlot = 20
  const naturalW = PADDING.left + PADDING.right + dates.length * minBarSlot
  const svgW = Math.max(containerW, naturalW)
  const plotW = svgW - PADDING.left - PADDING.right
  const barSlot = plotW / (dates.length || 1)
  const barW = Math.min(barSlot - 4, 40)
  const svgH = PADDING.top + plotH + PADDING.bottom

  const maxVal = Math.max(...values, 1)
  const yTickCount = 5
  const yTicks = Array.from({ length: yTickCount + 1 }, (_, i) => Math.round(maxVal * i / yTickCount))
  const labelStep = Math.ceil(dates.length / 30)

  return (
    <div ref={wrapperRef} style={{ overflowX: 'auto', marginTop: 8 }}>
      <svg width={svgW} height={svgH} style={{ fontFamily: 'inherit', display: 'block' }}>
        {/* グリッド線 + Y軸ラベル */}
        {yTicks.map((tick, i) => {
          const y = PADDING.top + plotH - (plotH * i / yTickCount)
          return (
            <g key={tick}>
              <line x1={PADDING.left} y1={y} x2={PADDING.left + plotW} y2={y}
                    stroke={i === 0 ? '#888' : '#e0d8d0'} strokeWidth={1} />
              <text x={PADDING.left - 6} y={y + 4} textAnchor="end" fontSize={10} fill="#888">
                {tick.toLocaleString()}
              </text>
            </g>
          )
        })}

        {/* バー */}
        {dates.map((date, i) => {
          const barH = Math.max((values[i] / maxVal) * plotH, 0)
          const x = PADDING.left + barSlot * i + (barSlot - barW) / 2
          const y = PADDING.top + plotH - barH
          const showLabel = dates.length <= 30 || i % labelStep === 0
          return (
            <g key={date}>
              <rect x={x} y={y} width={barW} height={barH} fill="#acd0d1" rx={2}>
                <title>{date}: {values[i].toLocaleString()}</title>
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

        {/* Y軸 */}
        <line x1={PADDING.left} y1={PADDING.top} x2={PADDING.left} y2={PADDING.top + plotH}
              stroke="#888" strokeWidth={1} />

        {/* Y軸ラベル */}
        <text
          x={14} y={PADDING.top + plotH / 2}
          textAnchor="middle" fontSize={10} fill="#5a8a8b"
          transform={`rotate(-90, 14, ${PADDING.top + plotH / 2})`}
        >
          {metric}
        </text>
      </svg>
    </div>
  )
}

// ── キリ番計算ユーティリティ ─────────────────────────────────────────────────
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

// ── Statisticsタブ ────────────────────────────────────────────────────────────
function StatisticsTab({ history, talentName, allVideos, preselect }: {
  history: AllHistory
  talentName: string
  allVideos: VideoCard[]
  preselect?: string | null
}) {
  const [searchText, setSearchText] = useState('')
  const [selectedId, setSelectedId] = useState<string | null>(preselect ?? null)

  useEffect(() => {
    if (preselect) setSelectedId(preselect)
  }, [preselect])
  const [metric, setMetric] = useState<StatsMetric>('再生数')

  const query = searchText.trim().toLowerCase()
  const matches = query
    ? allVideos.filter(v => v.タイトル.toLowerCase().includes(query)).slice(0, 10)
    : []

  const talentHist = history[talentName] ?? {}
  const selectedVid = selectedId
    ? (talentHist[selectedId] as VideoHistoryEntry | undefined)
    : null

  const records = selectedVid?.records ?? {}
  const dates = Object.keys(records).sort()
  const values = dates.map(d => records[d]?.[metric] ?? 0)

  return (
    <div>
      {/* 検索フォーム */}
      <input
        className="stats-search-input"
        type="text"
        placeholder="タイトルを入力してください..."
        value={searchText}
        onChange={e => setSearchText(e.target.value)}
      />

      {/* アコーディオン */}
      {matches.length > 0 && (
        <div className="stats-dropdown">
          {matches.map(v => (
            <button
              key={v.id}
              className="stats-dropdown-item"
              onClick={() => { setSelectedId(v.id); setSearchText('') }}
            >
              <span className="stats-type-badge">[{v.type}]</span>{v.タイトル}
            </button>
          ))}
        </div>
      )}
      {query && matches.length === 0 && (
        <p className="muted" style={{ fontSize: 12, margin: '4px 0' }}>一致する動画が見つかりません</p>
      )}

      {/* 選択中コンテンツ */}
      {selectedId && selectedVid ? (
        <>
          <div className="stats-video-title">
            <a href={`https://www.youtube.com/watch?v=${selectedId}`} target="_blank" rel="noopener noreferrer">
              {selectedVid.タイトル}
            </a>
          </div>

          <div className="stats-metric-btns">
            <button
              className={`sort-btn${metric === '再生数' ? ' active' : ''}`}
              onClick={() => setMetric('再生数')}
            >再生数</button>
            <button
              className={`sort-btn${metric === '高評価数' ? ' active' : ''}`}
              onClick={() => setMetric('高評価数')}
            >高評価数</button>
          </div>

          {dates.length > 0 ? (
            <>
              <BarChart dates={dates} values={values} metric={metric} />

              {/* 統計テーブル */}
              {(() => {
                const n = dates.length
                const latestVal = values[n - 1]
                const latestDate = dates[n - 1]

                // 全期間平均
                const overallAvg = n >= 2
                  ? (values[n - 1] - values[0]) / (n - 1)
                  : null

                // 直近N日の1日平均
                const calcRecentAvg = (days: number): number | null => {
                  if (n < 2) return null
                  const start = Math.max(0, n - days)
                  const diffs: number[] = []
                  for (let i = start + 1; i < n; i++) diffs.push(values[i] - values[i - 1])
                  return diffs.length > 0 ? diffs.reduce((a, b) => a + b, 0) / diffs.length : null
                }

                const recent90Avg = calcRecentAvg(90)
                const recent30Avg = calcRecentAvg(30)
                const recent7Avg  = calcRecentAvg(7)

                const milestone = getNextMilestone(latestVal)
                const fmtAvg = (v: number | null) =>
                  v !== null ? `${v >= 0 ? '+' : ''}${v.toFixed(1)}` : '—'

                return (
                  <div className="stats-table-wrap">
                    <table className="stats-info-table">
                      <thead>
                        <tr>
                          <th />
                          <th>全期間</th>
                          <th>直近3ヶ月</th>
                          <th>直近1ヶ月</th>
                          <th>直近7日</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr>
                          <td>1日当たり増加数</td>
                          <td>{fmtAvg(overallAvg)}</td>
                          <td>{fmtAvg(recent90Avg)}</td>
                          <td>{fmtAvg(recent30Avg)}</td>
                          <td>{fmtAvg(recent7Avg)}</td>
                        </tr>
                        <tr>
                          <td>直近キリ番 <strong>{milestone.toLocaleString()}</strong> 到達予測日</td>
                          <td>{estimateDate(latestDate, latestVal, milestone, overallAvg)}</td>
                          <td>{estimateDate(latestDate, latestVal, milestone, recent90Avg)}</td>
                          <td>{estimateDate(latestDate, latestVal, milestone, recent30Avg)}</td>
                          <td>{estimateDate(latestDate, latestVal, milestone, recent7Avg)}</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                )
              })()}
            </>
          ) : (
            <p className="muted">グラフ表示には1日以上の履歴データが必要です</p>
          )}
        </>
      ) : !selectedId && (
        <p className="muted" style={{ marginTop: 32, textAlign: 'center' }}>
          ↑ 上の検索フォームから動画を選択してください
        </p>
      )}

      {/* キリ番アラート */}
      {(() => {
        const alerts: { id: string; title: string; type: string; currentVal: number; milestone: number; daysLeft: number }[] = []

        for (const [vid_id, raw] of Object.entries(talentHist)) {
          if (vid_id === '_channel_stats') continue
          const vid = raw as VideoHistoryEntry
          if (!vid.records) continue

          const sortedDates = Object.keys(vid.records).sort()
          const n = sortedDates.length
          if (n < 2) continue

          const latestVal = vid.records[sortedDates[n - 1]]?.再生数 ?? 0

          const start = Math.max(0, n - 7)
          const diffs: number[] = []
          for (let i = start + 1; i < n; i++) {
            diffs.push((vid.records[sortedDates[i]]?.再生数 ?? 0) - (vid.records[sortedDates[i - 1]]?.再生数 ?? 0))
          }
          if (diffs.length === 0) continue
          const avg = diffs.reduce((a, b) => a + b, 0) / diffs.length
          if (avg <= 0) continue

          const milestone = getNextMilestone(latestVal)
          const daysLeft = (milestone - latestVal) / avg
          if (daysLeft <= 2) {
            alerts.push({ id: vid_id, title: vid.タイトル ?? vid_id, type: vid.type ?? 'Movie', currentVal: latestVal, milestone, daysLeft })
          }
        }

        alerts.sort((a, b) => a.daysLeft - b.daysLeft)
        if (alerts.length === 0) return null

        return (
          <div className="milestone-alert-wrap">
            <div className="milestone-alert-header">🎯 キリ番まで2日以内（直近7日平均）</div>
            {alerts.map(a => (
              <div key={a.id} className="milestone-alert-item">
                <span className="stats-type-badge">[{a.type}]</span>
                <a href={`https://www.youtube.com/watch?v=${a.id}`} target="_blank" rel="noopener noreferrer"
                   className="milestone-alert-title">
                  {a.title}
                </a>
                <span className="milestone-alert-nums">
                  {a.currentVal.toLocaleString()} → <strong>{a.milestone.toLocaleString()}</strong>
                  <span className="milestone-alert-days">約{a.daysLeft.toFixed(1)}日</span>
                </span>
              </div>
            ))}
          </div>
        )
      })()}
    </div>
  )
}

// ── 動画カード ────────────────────────────────────────────────────────────────
function VideoCardItem({ video, onStatsClick }: { video: VideoCard; onStatsClick: () => void }) {
  const v1d = video.再生数daily[0]
  const l1d = video.高評価daily[0]
  const url = `https://www.youtube.com/watch?v=${video.id}`

  const days = []
  for (let i = 1; i < 15; i++) {
    const v = video.再生数daily[i]
    const l = video.高評価daily[i]
    if (v === null) break
    days.push({ label: `${i + 1}D`, v, l })
  }

  return (
    <div className="video-card">
      <div className="video-title">
        <a href={url} target="_blank" rel="noopener noreferrer">{video.タイトル}</a>
        <button className="stats-jump-btn" onClick={onStatsClick} title="Statisticsで見る">📊</button>
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
      </div>
      {days.length > 0 && (
        <table className="day-table">
          <tbody>
            <tr>
              <td className="day-label" />
              {days.map(d => <td key={d.label} className="day-head">{d.label}</td>)}
            </tr>
            <tr>
              <td className="day-label">再生</td>
              {days.map(d => (
                <td key={d.label} className="day-val" style={{ color: diffColor(d.v) }}>
                  {fmtDiff(d.v)}
                </td>
              ))}
            </tr>
            <tr>
              <td className="day-label">高評価</td>
              {days.map(d => (
                <td key={d.label} className="day-val" style={{ color: diffColor(d.l) }}>
                  {fmtDiff(d.l)}
                </td>
              ))}
            </tr>
          </tbody>
        </table>
      )}
    </div>
  )
}

export default function TalentPage({ history, talentName }: Props) {
  const { stats, diff } = getLatestChannelStats(history, talentName)
  const allVideos = buildTalentVideoList(history, talentName)

  const videoByType: Record<VideoType, VideoCard[]> = { Movie: [], Short: [], LiveArchive: [] }
  for (const v of allVideos) {
    if (v.type in videoByType) videoByType[v.type].push(v)
  }

  const activeTabs = ALL_TABS.filter(t =>
    t.type === 'Statistics'
      ? allVideos.length > 0
      : videoByType[t.type as VideoType].length > 0
  )
  const [activeType, setActiveType] = useState<TabType>(activeTabs[0]?.type ?? 'Movie')
  const [sortKey, setSortKey] = useState<SortKey>('再生数')
  const [statsPreselect, setStatsPreselect] = useState<string | null>(null)

  function fmtStatDiff(v: number | null) {
    if (v === null) return null
    const sign = v >= 0 ? '+' : ''
    return <span style={{ fontSize: 13, color: diffColor(v), marginLeft: 6 }}>({sign}{v.toLocaleString()})</span>
  }

  const sorted = activeType !== 'Statistics'
    ? [...videoByType[activeType as VideoType]].sort((a, b) => b[sortKey] - a[sortKey])
    : []

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
                onClick={() => { setActiveType(t.type); if (t.type !== 'Statistics') setSortKey('再生数') }}
              >
                {t.label}
                {t.type !== 'Statistics' && (
                  <span className="tab-count">({videoByType[t.type as VideoType].length})</span>
                )}
              </button>
            ))}
          </div>

          {activeType === 'Statistics' ? (
            <StatisticsTab history={history} talentName={talentName} allVideos={allVideos} preselect={statsPreselect} />
          ) : (
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
                  <VideoCardItem
                    key={v.id}
                    video={v}
                    onStatsClick={() => { setStatsPreselect(v.id); setActiveType('Statistics') }}
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
