import {
  AllHistory, ChannelStats, VideoType,
  SingerRankItem, VideoRankItem, VideoCard,
} from '../types'

export const TALENT_ORDER = [
  'Dashboard',
  '焔魔るり', 'HACHI', '瀬戸乃とと', '水瀬凪',
  'KMNZ', 'VESPERBELL', 'CULUA', 'NEUN', 'MEDA', 'CONA',
  'IMI', 'XIDEN', 'ヨノ', 'LEWNE', '羽緒', 'Cil', '深影', 'wouca',
  'Diα', '妃玖',
]

const HISTORY_URL =
  import.meta.env.VITE_HISTORY_URL ??
  `https://raw.githubusercontent.com/Kinshutei/RKMusic_AllSinger_PFR/main/all_history_${new Date().getFullYear()}.json`

export async function loadHistory(): Promise<AllHistory> {
  const res = await fetch(HISTORY_URL)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export function getAvailableTalents(history: AllHistory): string[] {
  const existing = new Set(Object.keys(history))
  const ordered = TALENT_ORDER.filter(t => t === 'Dashboard' || existing.has(t))
  const extras = Object.keys(history).filter(t => !TALENT_ORDER.includes(t)).sort()
  return [...ordered, ...extras]
}

function prevDate(dateStr: string): string {
  const d = new Date(dateStr)
  d.setDate(d.getDate() - 1)
  return d.toISOString().slice(0, 10)
}

function rate(val: number, diff: number | null): number | null {
  if (diff === null) return null
  const base = val - diff
  return base > 0 ? Math.round(diff / base * 1000) / 10 : null
}

export function buildDashboardData(history: AllHistory) {
  const talents = TALENT_ORDER.filter(t => t !== 'Dashboard' && t in history)

  const allDates = new Set<string>()
  for (const t of talents) {
    const cs = history[t]?._channel_stats
    if (cs) Object.keys(cs).forEach(d => allDates.add(d))
  }
  if (allDates.size === 0) return null

  const n_date = Array.from(allDates).sort().at(-1)!
  const p_date = prevDate(n_date)

  const singerData: SingerRankItem[] = []
  for (const talent of talents) {
    const cs = history[talent]?._channel_stats as Record<string, ChannelStats> | undefined
    if (!cs) continue
    const n = cs[n_date], p = cs[p_date]
    const subs_n  = n?.登録者数 ?? 0
    const views_n = n?.総再生数 ?? 0
    const subs_diff  = (n && p) ? subs_n  - (p.登録者数 ?? 0) : null
    const views_diff = (n && p) ? views_n - (p.総再生数 ?? 0) : null
    singerData.push({
      talent, subs_n, views_n,
      subs_diff,  subs_rate:  rate(subs_n,  subs_diff),
      views_diff, views_rate: rate(views_n, views_diff),
    })
  }

  const videoData: Record<VideoType, VideoRankItem[]> = { Movie: [], Short: [], LiveArchive: [] }
  for (const talent of talents) {
    for (const [vid_id, raw] of Object.entries(history[talent] ?? {})) {
      if (vid_id === '_channel_stats') continue
      const vid = raw as { タイトル?: string; type?: string; records?: Record<string, { 再生数?: number; 高評価数?: number; コメント数?: number }> }
      if (!vid.records) continue
      const vtype = (vid.type ?? 'Movie') as VideoType
      if (!(vtype in videoData)) continue
      const nr = vid.records[n_date], pr = vid.records[p_date]
      const views_n    = nr?.再生数    ?? 0
      const likes_n    = nr?.高評価数  ?? 0
      const comments_n = nr?.コメント数 ?? 0
      const views_diff    = (nr && pr) ? views_n    - (pr.再生数    ?? 0) : null
      const likes_diff    = (nr && pr) ? likes_n    - (pr.高評価数  ?? 0) : null
      const comments_diff = (nr && pr) ? comments_n - (pr.コメント数 ?? 0) : null
      videoData[vtype].push({
        talent, vid_id, title: vid.タイトル ?? vid_id,
        views_n, views_diff, views_rate: rate(views_n, views_diff),
        likes_n, likes_diff,
        comments_n, comments_diff,
      })
    }
  }

  return { singerData, videoData, n_date }
}

export function getLatestChannelStats(history: AllHistory, talentName: string) {
  const cs = history[talentName]?._channel_stats as Record<string, ChannelStats> | undefined
  if (!cs) return { stats: null, diff: null, n_date: null }
  const sorted = Object.keys(cs).sort()
  if (sorted.length === 0) return { stats: null, diff: null, n_date: null }
  const n_date = sorted.at(-1)!
  const n = cs[n_date]
  const p = cs[prevDate(n_date)]
  const diff = p ? {
    登録者数: n.登録者数 - p.登録者数,
    総再生数: n.総再生数 - p.総再生数,
    動画数:   n.動画数   - p.動画数,
  } : null
  return { stats: n, diff, n_date }
}

export function buildTalentVideoList(history: AllHistory, talentName: string): VideoCard[] {
  const talentHist = history[talentName]
  if (!talentHist) return []

  const result: VideoCard[] = []
  for (const [vid_id, raw] of Object.entries(talentHist)) {
    if (vid_id === '_channel_stats') continue
    const vid = raw as { タイトル?: string; type?: string; records?: Record<string, { 再生数?: number; 高評価数?: number }> }
    if (!vid.records) continue

    const sorted = Object.keys(vid.records).sort()
    const last = vid.records[sorted.at(-1) ?? ''] ?? {}
    const current_views = last.再生数   ?? 0
    const current_likes = last.高評価数 ?? 0

    const daily_views: (number | null)[] = []
    const daily_likes: (number | null)[] = []
    for (let i = 1; i <= 5; i++) {
      if (sorted.length > i) {
        const curr = vid.records[sorted[sorted.length - i]]   ?? {}
        const prev = vid.records[sorted[sorted.length - i - 1]] ?? {}
        daily_views.push((curr.再生数   ?? 0) - (prev.再生数   ?? 0))
        daily_likes.push((curr.高評価数 ?? 0) - (prev.高評価数 ?? 0))
      } else {
        daily_views.push(null)
        daily_likes.push(null)
      }
    }

    result.push({
      id: vid_id,
      タイトル: vid.タイトル ?? vid_id,
      type: (vid.type ?? 'Movie') as VideoType,
      再生数: current_views,
      再生数5d増加: daily_views.reduce<number>((a, v) => a + (v ?? 0), 0),
      高評価数: current_likes,
      高評価5d増加: daily_likes.reduce<number>((a, v) => a + (v ?? 0), 0),
      再生数daily: daily_views,
      高評価daily: daily_likes,
    })
  }
  return result
}
