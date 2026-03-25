import { useState } from 'react'
import { AllHistory, SingerRankItem, VideoRankItem, VideoType } from '../types'
import { buildDashboardData } from '../utils/data'
import { buildAndDownloadCsv } from '../utils/csvExport'

interface Props {
  history: AllHistory
}

function fmtDiff(diff: number | null, rate?: number | null): string {
  if (diff === null) return '—'
  const sign = diff >= 0 ? '+' : ''
  const r = rate != null ? ` (${diff >= 0 ? '+' : ''}${rate}%)` : ''
  return `${sign}${diff.toLocaleString()}${r}`
}

function diffColor(diff: number | null): string {
  if (diff === null) return '#aaa'
  return diff > 0 ? '#2e7d5a' : diff < 0 ? '#c0392b' : '#888'
}

function SingerTable({ rows, valKey, diffKey, rateKey }: {
  rows: SingerRankItem[]
  valKey: 'subs_n' | 'views_n'
  diffKey: 'subs_diff' | 'views_diff'
  rateKey: 'subs_rate' | 'views_rate'
}) {
  const sorted = [...rows].sort((a, b) => (b[diffKey] ?? -999999) - (a[diffKey] ?? -999999))
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

const VIDEO_SECTIONS: { type: VideoType; label: string }[] = [
  { type: 'Movie',       label: '🎬 Movie部門' },
  { type: 'Short',       label: '📱 Short部門' },
  { type: 'LiveArchive', label: '🔴 LiveArchive部門' },
]

export default function DashboardPage({ history }: Props) {
  const [csvLoading, setCsvLoading] = useState(false)
  const [csvError, setCsvError] = useState<string | null>(null)

  const data = buildDashboardData(history)

  const handleCsv = async () => {
    setCsvLoading(true)
    setCsvError(null)
    try {
      await buildAndDownloadCsv(history)
    } catch (e) {
      setCsvError(String(e))
    } finally {
      setCsvLoading(false)
    }
  }

  return (
    <div>
      {/* CSV エクスポート */}
      <div className="section-box">
        <div className="section-title">📥 CSVエクスポート</div>
        <p className="section-desc">チャンネル統計・動画統計の2ファイルをZIP（Shift-JIS）でダウンロード</p>
        <button className="btn-primary" onClick={handleCsv} disabled={csvLoading}>
          {csvLoading ? '生成中...' : 'CSVをダウンロード'}
        </button>
        {csvError && <p className="error-text">{csvError}</p>}
      </div>

      {!data ? (
        <p className="muted">データがありません</p>
      ) : (
        <>
          <p className="date-label">集計基準日: {data.n_date}（前日比）</p>

          {/* Singer部門 */}
          <h3>🎤 Singer部門</h3>
          <div className="two-col">
            <div>
              <div className="col-label">登録者数</div>
              <SingerTable rows={data.singerData} valKey="subs_n" diffKey="subs_diff" rateKey="subs_rate" />
            </div>
            <div>
              <div className="col-label">総再生数</div>
              <SingerTable rows={data.singerData} valKey="views_n" diffKey="views_diff" rateKey="views_rate" />
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
