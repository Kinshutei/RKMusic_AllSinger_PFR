import { useState } from 'react'
import { AllHistory, VideoCard, VideoType } from '../types'
import { getLatestChannelStats, buildTalentVideoList } from '../utils/data'

interface Props {
  history: AllHistory
  talentName: string
}

type SortKey = '再生数' | '高評価数' | '再生数5d増加' | '高評価5d増加'

const SORT_OPTIONS: { key: SortKey; label: string }[] = [
  { key: '再生数',       label: '📊 再生数TOP' },
  { key: '高評価数',     label: '👍 高評価TOP' },
  { key: '再生数5d増加', label: '📈 再生5日増加' },
  { key: '高評価5d増加', label: '💹 高評価5日増加' },
]

const TYPE_TABS: { type: VideoType; label: string }[] = [
  { type: 'Movie',       label: '📹 Movie' },
  { type: 'Short',       label: '🎬 Short' },
  { type: 'LiveArchive', label: '🔴 LiveArchive' },
]

function fmtDiff(v: number | null): string {
  if (v === null) return '—'
  return v >= 0 ? `+${v.toLocaleString()}` : v.toLocaleString()
}

function diffColor(v: number | null): string {
  if (v === null) return '#aaa'
  return v > 0 ? '#2e7d5a' : v < 0 ? '#c0392b' : '#888'
}

function VideoCardItem({ video }: { video: VideoCard }) {
  const v1d = video.再生数daily[0]
  const l1d = video.高評価daily[0]
  const url = `https://www.youtube.com/watch?v=${video.id}`

  const days = []
  for (let i = 1; i < 5; i++) {
    const v = video.再生数daily[i]
    const l = video.高評価daily[i]
    if (v === null) break
    days.push({ label: `${i + 1}D`, v, l })
  }

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

  const activeTabs = TYPE_TABS.filter(t => videoByType[t.type].length > 0)
  const [activeType, setActiveType] = useState<VideoType>(activeTabs[0]?.type ?? 'Movie')
  const [sortKey, setSortKey] = useState<SortKey>('再生数')

  function fmtStatDiff(v: number | null) {
    if (v === null) return null
    const sign = v >= 0 ? '+' : ''
    return <span style={{ fontSize: 13, color: diffColor(v), marginLeft: 6 }}>({sign}{v.toLocaleString()})</span>
  }

  const sorted = [...videoByType[activeType]].sort((a, b) => b[sortKey] - a[sortKey])

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
            {sorted.map(v => <VideoCardItem key={v.id} video={v} />)}
          </div>
        </>
      )}
    </div>
  )
}
