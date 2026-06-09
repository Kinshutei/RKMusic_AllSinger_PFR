import {
  AllHistory, ChannelStats, VideoType, VideoFlags,
  SingerRankItem, VideoRankItem, VideoCard,
  AllComments, ChannelComments,
} from '../types'

export const TALENT_ORDER = [
  'Dashboard',
  '焔魔るり', 'HACHI', '瀬戸乃とと', '水瀬凪',
  'KMNZ', 'VESPERBELL', 'CULUA', 'NEUN', 'MEDA', 'CONA',
  'IMI', 'XIDEN', 'ヨノ', 'MEMESIA', 'LEWNE', '羽緒', 'Cil', '深影', 'wouca',
  'Diα', '妃玖', 'HONK THE HORN', 'NUROJUNK',
]

const HISTORY_BASE_URL =
  import.meta.env.VITE_HISTORY_BASE_URL ??
  'https://raw.githubusercontent.com/Kinshutei/RKMusic_AllSinger_PFR/main'

const FLAGS_URL = 'https://raw.githubusercontent.com/Kinshutei/RKMusic_AllSinger_PFR/main/video_flags.json'

export async function loadHistory(): Promise<AllHistory> {
  const talents = TALENT_ORDER.filter(t => t !== 'Dashboard')
  const results = await Promise.all(
    talents.map(async talent => {
      try {
        const res = await fetch(`${HISTORY_BASE_URL}/history_${encodeURIComponent(talent)}.json`)
        if (!res.ok) return {}
        return res.json() as Promise<AllHistory>
      } catch {
        return {}
      }
    })
  )
  return Object.assign({}, ...results)
}

export async function loadVideoFlags(): Promise<VideoFlags> {
  try {
    const res = await fetch(FLAGS_URL)
    if (!res.ok) return {}
    return res.json()
  } catch {
    return {}
  }
}

export async function loadComments(): Promise<AllComments> {
  const talents = TALENT_ORDER.filter(t => t !== 'Dashboard')
  const results = await Promise.all(
    talents.map(async talent => {
      try {
        const res = await fetch(`${HISTORY_BASE_URL}/comments_${encodeURIComponent(talent)}.json`)
        if (!res.ok) return {}
        const data = await res.json() as ChannelComments
        return { [talent]: data }
      } catch {
        return {}
      }
    })
  )
  return Object.assign({}, ...results)
}

export function getAvailableTalents(history: AllHistory): string[] {
  const existing = new Set(Object.keys(history))
  const ordered = TALENT_ORDER.filter(t => t === 'Dashboard' || existing.has(t))
  const extras = Object.keys(history).filter(t => !TALENT_ORDER.includes(t)).sort()
  return [...ordered, ...extras]
}

// ----------------------------------------------------------------
// コラボ検出
// ----------------------------------------------------------------

const COLLAB_PATTERNS: [RegExp, string][] = [
  [/feat\.?\s+/i,  'feat.'],
  [/ft\.?\s+/i,    'feat.'],
  [/×/,            '×コラボ'],
  [/\bw\/\s*/i,    'w/コラボ'],
  [/コラボ/,        'コラボ'],
]

export function detectCollabTags(title: string): string[] {
  const tags: string[] = []
  for (const [pattern, label] of COLLAB_PATTERNS) {
    if (pattern.test(title)) {
      if (!tags.includes(label)) tags.push(label)
    }
  }
  return tags
}

// ----------------------------------------------------------------
// 共通ユーティリティ
// ----------------------------------------------------------------

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

// ----------------------------------------------------------------
// ダッシュボード
// ----------------------------------------------------------------

export function buildDashboardData(history: AllHistory, flags: VideoFlags = {}) {
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

    let comments_n = 0, comments_p = 0, has_p = false
    let content_movie = 0, content_short = 0, content_live = 0
    let content_n = 0, content_p = 0, has_content_p = false
    for (const [vid_id, raw] of Object.entries(history[talent] ?? {})) {
      if (vid_id === '_channel_stats') continue
      const vid = raw as { type?: string; records?: Record<string, { コメント数?: number }> }
      if (!vid.records) continue
      comments_n += vid.records[n_date]?.コメント数 ?? 0
      if (vid.records[p_date] !== undefined) {
        comments_p += vid.records[p_date]?.コメント数 ?? 0
        has_p = true
      }
      const vtype = (flags[talent]?.[vid_id] ?? vid.type ?? 'Movie') as VideoType
      if (vtype === 'Movie')       content_movie++
      else if (vtype === 'Short')  content_short++
      else if (vtype === 'LiveArchive') content_live++
      if (vid.records[n_date] !== undefined) content_n++
      if (vid.records[p_date] !== undefined) { content_p++; has_content_p = true }
    }
    const comments_diff = has_p ? comments_n - comments_p : null
    const content_diff = has_content_p ? content_n - content_p : null

    singerData.push({
      talent, subs_n, views_n,
      subs_diff,  subs_rate:  rate(subs_n,  subs_diff),
      views_diff, views_rate: rate(views_n, views_diff),
      comments_n, comments_diff, comments_rate: rate(comments_n, comments_diff),
      content_total: content_movie + content_short + content_live,
      content_movie, content_short, content_live,
      content_diff, content_rate: rate(content_n, content_diff),
    })
  }

  const videoData: Record<VideoType, VideoRankItem[]> = { Movie: [], Short: [], LiveArchive: [] }
  for (const talent of talents) {
    for (const [vid_id, raw] of Object.entries(history[talent] ?? {})) {
      if (vid_id === '_channel_stats') continue
      const vid = raw as { タイトル?: string; type?: string; records?: Record<string, { 再生数?: number; 高評価数?: number; コメント数?: number }> }
      if (!vid.records) continue
      const vtype = (flags[talent]?.[vid_id] ?? vid.type ?? 'Movie') as VideoType
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

export function buildStatsData(history: AllHistory): { date: string; subs: number; views: number }[] {
  const talents = TALENT_ORDER.filter(t => t !== 'Dashboard' && t in history)
  const dateMap = new Map<string, { subs: number; views: number }>()

  for (const talent of talents) {
    const cs = history[talent]?._channel_stats as Record<string, ChannelStats> | undefined
    if (!cs) continue
    for (const [date, stats] of Object.entries(cs)) {
      const cur = dateMap.get(date) ?? { subs: 0, views: 0 }
      cur.subs  += stats.登録者数 ?? 0
      cur.views += stats.総再生数 ?? 0
      dateMap.set(date, cur)
    }
  }

  return Array.from(dateMap.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([date, v]) => ({ date, ...v }))
}

export function buildViewsTypeBreakdown(
  history: AllHistory, flags: VideoFlags = {}
): { Movie: number; Short: number; LiveArchive: number; date: string } | null {
  const talents = TALENT_ORDER.filter(t => t !== 'Dashboard' && t in history)

  const allDates = new Set<string>()
  for (const t of talents) {
    const cs = history[t]?._channel_stats
    if (cs) Object.keys(cs).forEach(d => allDates.add(d))
  }
  if (allDates.size === 0) return null

  const n_date = Array.from(allDates).sort().at(-1)!
  const p_date = prevDate(n_date)

  const result = { Movie: 0, Short: 0, LiveArchive: 0, date: n_date }

  for (const talent of talents) {
    for (const [vid_id, raw] of Object.entries(history[talent] ?? {})) {
      if (vid_id === '_channel_stats') continue
      const vid = raw as { type?: string; records?: Record<string, { 再生数?: number }> }
      if (!vid.records) continue
      const nr = vid.records[n_date]
      const pr = vid.records[p_date]
      if (!nr || !pr) continue
      const diff = (nr.再生数 ?? 0) - (pr.再生数 ?? 0)
      if (diff <= 0) continue
      const vtype = (flags[talent]?.[vid_id] ?? vid.type ?? 'Movie') as VideoType
      result[vtype] += diff
    }
  }

  return result
}

export function buildDailyViewsByTalent(
  history: AllHistory
): { views: Record<string, number>; date: string } | null {
  const talents = TALENT_ORDER.filter(t => t !== 'Dashboard' && t in history)

  const allDates = new Set<string>()
  for (const t of talents) {
    const cs = history[t]?._channel_stats
    if (cs) Object.keys(cs).forEach(d => allDates.add(d))
  }
  if (allDates.size === 0) return null

  const n_date = Array.from(allDates).sort().at(-1)!
  const p_date = prevDate(n_date)

  const views: Record<string, number> = {}
  for (const talent of talents) {
    let total = 0
    for (const [vid_id, raw] of Object.entries(history[talent] ?? {})) {
      if (vid_id === '_channel_stats') continue
      const vid = raw as { records?: Record<string, { 再生数?: number }> }
      if (!vid.records) continue
      const nr = vid.records[n_date]
      const pr = vid.records[p_date]
      if (!nr || !pr) continue
      const diff = (nr.再生数 ?? 0) - (pr.再生数 ?? 0)
      if (diff > 0) total += diff
    }
    views[talent] = total
  }

  return { views, date: n_date }
}

// ----------------------------------------------------------------
// タレント個別
// ----------------------------------------------------------------

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

export function buildTalentVideoList(history: AllHistory, talentName: string, flags: VideoFlags = {}): VideoCard[] {
  const talentHist = history[talentName]
  if (!talentHist) return []

  const result: VideoCard[] = []
  for (const [vid_id, raw] of Object.entries(talentHist)) {
    if (vid_id === '_channel_stats') continue
    const vid = raw as {
      タイトル?: string
      公開日?: string
      type?: string
      records?: Record<string, { 再生数?: number; 高評価数?: number; コメント数?: number }>
    }
    if (!vid.records) continue

    const sorted = Object.keys(vid.records).sort()
    const last = vid.records[sorted.at(-1) ?? ''] ?? {}
    const current_views    = last.再生数   ?? 0
    const current_likes    = last.高評価数 ?? 0
    const current_comments = last.コメント数 ?? 0

    const daily_views:    (number | null)[] = []
    const daily_likes:    (number | null)[] = []
    const daily_comments: (number | null)[] = []
    for (let i = 1; i <= 15; i++) {
      if (sorted.length > i) {
        const curr = vid.records[sorted[sorted.length - i]]     ?? {}
        const prev = vid.records[sorted[sorted.length - i - 1]] ?? {}
        daily_views.push((curr.再生数   ?? 0) - (prev.再生数   ?? 0))
        daily_likes.push((curr.高評価数 ?? 0) - (prev.高評価数 ?? 0))
        daily_comments.push((curr.コメント数 ?? 0) - (prev.コメント数 ?? 0))
      } else {
        daily_views.push(null)
        daily_likes.push(null)
        daily_comments.push(null)
      }
    }

    const title = vid.タイトル ?? vid_id
    result.push({
      id: vid_id,
      タイトル: title,
      type: (flags[talentName]?.[vid_id] ?? vid.type ?? 'Movie') as VideoType,
      公開日: vid.公開日 ?? '',
      再生数: current_views,
      再生数15d増加: daily_views.reduce<number>((a, v) => a + (v ?? 0), 0),
      高評価数: current_likes,
      高評価15d増加: daily_likes.reduce<number>((a, v) => a + (v ?? 0), 0),
      コメント数: current_comments,
      再生数daily: daily_views,
      高評価daily: daily_likes,
      コメント数daily: daily_comments,
      collab_tags: detectCollabTags(title),
    })
  }
  return result
}

// ----------------------------------------------------------------
// 直近N日の日別再生数内訳（種別×日付）
// ----------------------------------------------------------------

export interface DailyViewsEntry {
  date: string
  Movie: number
  Short: number
  LiveArchive: number
}

export function buildDailyViewsBreakdown(
  history: AllHistory,
  talentName: string,
  flags: VideoFlags = {},
  days = 15
): DailyViewsEntry[] {
  const talentHist = history[talentName]
  if (!talentHist) return []

  const cs = talentHist._channel_stats as Record<string, ChannelStats> | undefined
  if (!cs) return []

  const allDates = Object.keys(cs).sort()
  if (allDates.length < 2) return []

  const recentDates = allDates.slice(-(days + 1))

  const result: DailyViewsEntry[] = []
  for (let i = 1; i < recentDates.length; i++) {
    const date = recentDates[i]
    const prev = recentDates[i - 1]
    const entry: DailyViewsEntry = { date, Movie: 0, Short: 0, LiveArchive: 0 }

    for (const [vid_id, raw] of Object.entries(talentHist)) {
      if (vid_id === '_channel_stats') continue
      const vid = raw as { type?: string; records?: Record<string, { 再生数?: number }> }
      if (!vid.records) continue
      const nr = vid.records[date]
      const pr = vid.records[prev]
      if (!nr || !pr) continue
      const diff = (nr.再生数 ?? 0) - (pr.再生数 ?? 0)
      if (diff <= 0) continue
      const vtype = (flags[talentName]?.[vid_id] ?? vid.type ?? 'Movie') as VideoType
      entry[vtype] += diff
    }
    result.push(entry)
  }
  return result
}

// ----------------------------------------------------------------
// 投稿カレンダー（供給ペース）
// ----------------------------------------------------------------

export interface PostingCalendarEntry {
  month: string       // "2026-01"
  Movie: number
  Short: number
  LiveArchive: number
}

export function buildPostingCalendar(
  history: AllHistory,
  talentName: string,
  flags: VideoFlags = {}
): PostingCalendarEntry[] {
  const talentHist = history[talentName]
  if (!talentHist) return []

  const monthMap = new Map<string, PostingCalendarEntry>()

  for (const [vid_id, raw] of Object.entries(talentHist)) {
    if (vid_id === '_channel_stats') continue
    const vid = raw as { 公開日?: string; type?: string }
    if (!vid.公開日) continue

    const month = vid.公開日.slice(0, 7)
    const vtype = (flags[talentName]?.[vid_id] ?? vid.type ?? 'Movie') as VideoType

    if (!monthMap.has(month)) {
      monthMap.set(month, { month, Movie: 0, Short: 0, LiveArchive: 0 })
    }
    monthMap.get(month)![vtype]++
  }

  return Array.from(monthMap.values()).sort((a, b) => a.month.localeCompare(b.month))
}

// ----------------------------------------------------------------
// Dashboard用：全タレント合計の日別再生数内訳（種別×日付）
// ----------------------------------------------------------------

export function buildDashboardDailyViewsBreakdown(
  history: AllHistory,
  flags: VideoFlags = {}
): DailyViewsEntry[] {
  const talents = TALENT_ORDER.filter(t => t !== 'Dashboard' && t in history)

  const allDates = new Set<string>()
  for (const t of talents) {
    const cs = history[t]?._channel_stats as Record<string, ChannelStats> | undefined
    if (cs) Object.keys(cs).forEach(d => allDates.add(d))
  }
  if (allDates.size < 2) return []

  const sortedDates = Array.from(allDates).sort()

  const result: DailyViewsEntry[] = []
  for (let i = 1; i < sortedDates.length; i++) {
    const date = sortedDates[i]
    const prev = sortedDates[i - 1]
    const entry: DailyViewsEntry = { date, Movie: 0, Short: 0, LiveArchive: 0 }

    for (const talent of talents) {
      for (const [vid_id, raw] of Object.entries(history[talent] ?? {})) {
        if (vid_id === '_channel_stats') continue
        const vid = raw as { type?: string; records?: Record<string, { 再生数?: number }> }
        if (!vid.records) continue
        const nr = vid.records[date]
        const pr = vid.records[prev]
        if (!nr || !pr) continue
        const diff = (nr.再生数 ?? 0) - (pr.再生数 ?? 0)
        if (diff <= 0) continue
        const vtype = (flags[talent]?.[vid_id] ?? vid.type ?? 'Movie') as VideoType
        entry[vtype] += diff
      }
    }
    result.push(entry)
  }
  return result
}

// ----------------------------------------------------------------
// 月別再生数内訳
// ----------------------------------------------------------------

export interface MonthlyViewsEntry {
  month: string       // "2026-01"
  Movie: number
  Short: number
  LiveArchive: number
}

export function buildMonthlyViewsBreakdown(
  history: AllHistory,
  talentName: string,
  flags: VideoFlags = {}
): MonthlyViewsEntry[] {
  const talentHist = history[talentName]
  if (!talentHist) return []

  const monthSet = new Set<string>()
  for (const [vid_id, raw] of Object.entries(talentHist)) {
    if (vid_id === '_channel_stats') continue
    const vid = raw as { records?: Record<string, unknown> }
    if (!vid.records) continue
    for (const d of Object.keys(vid.records)) monthSet.add(d.slice(0, 7))
  }

  const months = Array.from(monthSet).sort()
  if (months.length === 0) return []

  const result: MonthlyViewsEntry[] = []

  for (const month of months) {
    const entry: MonthlyViewsEntry = { month, Movie: 0, Short: 0, LiveArchive: 0 }

    for (const [vid_id, raw] of Object.entries(talentHist)) {
      if (vid_id === '_channel_stats') continue
      const vid = raw as { type?: string; records?: Record<string, { 再生数?: number }> }
      if (!vid.records) continue

      const recordDates = Object.keys(vid.records).sort()

      // その月内の最後の記録日
      const lastInMonth = recordDates.filter(d => d.startsWith(month)).at(-1)
      if (!lastInMonth) continue

      // その月開始前の最後の記録日
      const prevBeforeMonth = recordDates.filter(d => d < `${month}-01`).at(-1)

      const curr = vid.records[lastInMonth]?.再生数 ?? 0
      const prev = prevBeforeMonth ? (vid.records[prevBeforeMonth]?.再生数 ?? 0) : 0
      const diff = curr - prev
      if (diff <= 0) continue

      const vtype = (flags[talentName]?.[vid_id] ?? vid.type ?? 'Movie') as VideoType
      entry[vtype] += diff
    }
    result.push(entry)
  }

  // 2026-02はデータ収集開始月のため除外（月途中からのスナップショットで不正確）
  return result.filter(e => e.month >= '2026-03')
}

// ----------------------------------------------------------------
// 初速カーブ（公開日からの再生推移）
// ----------------------------------------------------------------

export interface VelocityCurvePoint {
  day: number     // 公開からの経過日数
  views: number   // その日の累計再生数
}

export interface VelocityCurveItem {
  vid_id: string
  title: string
  公開日: string
  curve: VelocityCurvePoint[]
}

export function buildVelocityCurveData(
  history: AllHistory,
  talentName: string,
  flags: VideoFlags = {},
  maxVideos = 10,
  maxDays = 60
): VelocityCurveItem[] {
  const talentHist = history[talentName]
  if (!talentHist) return []

  const items: VelocityCurveItem[] = []

  for (const [vid_id, raw] of Object.entries(talentHist)) {
    if (vid_id === '_channel_stats') continue
    const vid = raw as {
      タイトル?: string
      公開日?: string
      type?: string
      records?: Record<string, { 再生数?: number }>
    }
    if (!vid.records || !vid.公開日) continue

    // Movieのみ対象（Short/Liveは初速の性質が異なる）
    const vtype = (flags[talentName]?.[vid_id] ?? vid.type ?? 'Movie') as VideoType
    if (vtype !== 'Movie') continue

    const pubDate = new Date(vid.公開日)
    const recordDates = Object.keys(vid.records).sort()

    const curve: VelocityCurvePoint[] = []
    for (const dateStr of recordDates) {
      const elapsed = Math.round(
        (new Date(dateStr).getTime() - pubDate.getTime()) / 86400000
      )
      if (elapsed < 0 || elapsed > maxDays) continue
      curve.push({ day: elapsed, views: vid.records[dateStr]?.再生数 ?? 0 })
    }

    if (curve.length < 2) continue
    items.push({ vid_id, title: vid.タイトル ?? vid_id, 公開日: vid.公開日, curve })
  }

  // 最新公開順で上位N本
  return items
    .sort((a, b) => b.公開日.localeCompare(a.公開日))
    .slice(0, maxVideos)
}
