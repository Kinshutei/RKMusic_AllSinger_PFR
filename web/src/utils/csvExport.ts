import JSZip from 'jszip'
import Encoding from 'encoding-japanese'
import { AllHistory } from '../types'
import { TALENT_ORDER } from './data'

function rowsToSjis(rows: (string | number)[][]): Uint8Array {
  const text = rows.map(row =>
    row.map(v => {
      const s = String(v)
      return s.includes(',') ? `"${s}"` : s
    }).join(',')
  ).join('\r\n')
  const unicode = Encoding.stringToCode(text)
  const sjis = Encoding.convert(unicode, { to: 'SJIS', from: 'UNICODE' })
  return new Uint8Array(sjis)
}

export async function buildAndDownloadCsv(history: AllHistory): Promise<void> {
  const talents = TALENT_ORDER.filter(t => t !== 'Dashboard' && t in history)

  const allDates = new Set<string>()
  for (const t of talents) {
    const cs = history[t]?._channel_stats
    if (cs) Object.keys(cs).forEach(d => allDates.add(d))
  }
  if (allDates.size === 0) throw new Error('履歴データが見つかりません')

  const n_date = Array.from(allDates).sort().at(-1)!
  const nDates: string[] = []
  for (let i = 1; i <= 5; i++) {
    const d = new Date(n_date)
    d.setDate(d.getDate() - i)
    nDates.push(d.toISOString().slice(0, 10))
  }

  // チャンネル統計 CSV
  const chHeader = [
    'タレント', '登録者数(N)',
    ...Array.from({ length: 5 }, (_, i) => `登録者増(${i + 1}D前)`),
    '総再生数(N)',
    ...Array.from({ length: 5 }, (_, i) => `総再生増(${i + 1}D前)`),
    '動画数(N)',
  ]
  const chRows: (string | number)[][] = [chHeader]

  for (const talent of talents) {
    const hc = (history[talent]?._channel_stats ?? {}) as Record<string, { 登録者数?: number; 総再生数?: number; 動画数?: number }>
    const nr = hc[n_date] ?? {}
    const subsDiffs:  (number | string)[] = []
    const viewsDiffs: (number | string)[] = []
    let prev = n_date
    for (const d of nDates) {
      const p = hc[prev], c = hc[d]
      subsDiffs.push(p && c  ? (p.登録者数 ?? 0) - (c.登録者数 ?? 0) : '')
      viewsDiffs.push(p && c ? (p.総再生数 ?? 0) - (c.総再生数 ?? 0) : '')
      prev = d
    }
    chRows.push([talent, nr.登録者数 ?? 0, ...subsDiffs, nr.総再生数 ?? 0, ...viewsDiffs, nr.動画数 ?? 0])
  }

  // 動画統計 CSV
  const vidHeader = [
    'タレント', '動画ID', 'タイトル', 'type', '再生数(N)',
    ...Array.from({ length: 5 }, (_, i) => `再生増(${i + 1}D前)`),
    '高評価数(N)',
    ...Array.from({ length: 5 }, (_, i) => `高評価増(${i + 1}D前)`),
  ]
  const vidRows: (string | number)[][] = [vidHeader]

  for (const talent of talents) {
    for (const [vid_id, raw] of Object.entries(history[talent] ?? {})) {
      if (vid_id === '_channel_stats') continue
      const vid = raw as { タイトル?: string; type?: string; records?: Record<string, { 再生数?: number; 高評価数?: number }> }
      if (!vid.records) continue
      const nr = vid.records[n_date] ?? {}
      const viewsDiffs: (number | string)[] = []
      const likesDiffs: (number | string)[] = []
      let prev = n_date
      for (const d of nDates) {
        const p = vid.records[prev], c = vid.records[d]
        viewsDiffs.push(p && c ? (p.再生数   ?? 0) - (c.再生数   ?? 0) : '')
        likesDiffs.push(p && c ? (p.高評価数 ?? 0) - (c.高評価数 ?? 0) : '')
        prev = d
      }
      vidRows.push([
        talent, vid_id, vid.タイトル ?? vid_id, vid.type ?? '',
        nr.再生数 ?? 0, ...viewsDiffs,
        nr.高評価数 ?? 0, ...likesDiffs,
      ])
    }
  }

  const chBytes  = rowsToSjis(chRows)
  const vidBytes = rowsToSjis(vidRows)

  const today = new Date().toISOString().slice(0, 10).replace(/-/g, '')
  const zip = new JSZip()
  zip.file(`channel_stats_${today}.csv`,  chBytes)
  zip.file(`video_stats_${today}.csv`, vidBytes)

  const blob = await zip.generateAsync({ type: 'blob' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `rkmusic_stats_${today}.zip`
  a.click()
  URL.revokeObjectURL(url)
}
