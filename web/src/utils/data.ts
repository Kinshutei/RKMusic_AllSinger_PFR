import {
  AllHistory, TalentHistory, ChannelStats, VideoType, VideoFlags,
  SingerRankItem, VideoRankItem, VideoCard,
  ChannelComments,
  DashboardSummary, DailySnapshot,
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

const FLAGS_URL = `${HISTORY_BASE_URL}/video_flags.json`
const SUMMARY_URL = `${HISTORY_BASE_URL}/dashboard_summary.json`

const FETCH_RETRIES = 3
const FETCH_RETRY_DELAY_MS = 1000

interface FetchResult<T> {
  data: T | null
  failed: boolean // true = リトライしても取得できなかった（404はファイル不在の想定内なのでfalse）
}

async function fetchJsonWithRetry<T>(url: string): Promise<FetchResult<T>> {
  for (let attempt = 0; attempt <= FETCH_RETRIES; attempt++) {
    try {
      const res = await fetch(url)
      if (res.ok) return { data: await res.json() as T, failed: false }
      if (res.status === 404) return { data: null, failed: false }
    } catch {
      // ネットワークエラーはリトライへ
    }
    if (attempt < FETCH_RETRIES) {
      await new Promise(r => setTimeout(r, FETCH_RETRY_DELAY_MS * (attempt + 1)))
    }
  }
  return { data: null, failed: true }
}

// Dashboardは事前集約済みの軽量サマリー1件のみ取得する（全タレントのhistoryを都度取得しない）。
// failed=true はリトライしても取れなかったとき。画面で「準備中」ではなく失敗と出すために返す。
export async function loadDashboardSummary(): Promise<FetchResult<DashboardSummary>> {
  return fetchJsonWithRetry<DashboardSummary>(SUMMARY_URL)
}

export async function loadVideoFlags(): Promise<VideoFlags> {
  return (await fetchJsonWithRetry<VideoFlags>(FLAGS_URL)).data ?? {}
}

// タレント個別ページ表示時にのみ、そのタレント1人分だけ取得する（遅延読み込み）。
export async function loadTalentHistory(talent: string): Promise<{ data: TalentHistory | null; failed: boolean }> {
  const { data, failed } = await fetchJsonWithRetry<AllHistory>(
    `${HISTORY_BASE_URL}/history_${encodeURIComponent(talent)}.json`
  )
  return { data: data?.[talent] ?? null, failed }
}

// 日付指定用の日別ファイル。同じ日を何度も選び直すので取得結果を覚えておく。
// 取れなかった日は、次に選び直した時に取り直せるよう覚えない。
const dailyCache = new Map<string, Promise<FetchResult<DailySnapshot>>>()
export function loadDaily(date: string): Promise<FetchResult<DailySnapshot>> {
  let p = dailyCache.get(date)
  if (!p) {
    p = fetchJsonWithRetry<DailySnapshot>(`${HISTORY_BASE_URL}/daily/${date}.json`)
    dailyCache.set(date, p)
    void p.then(r => { if (r.failed || !r.data) dailyCache.delete(date) })
  }
  return p
}

// comments_*.json は収集対象外のタレントが多く404が正常に発生する（想定内）。
export async function loadTalentComments(talent: string): Promise<ChannelComments> {
  return (await fetchJsonWithRetry<ChannelComments>(
    `${HISTORY_BASE_URL}/comments_${encodeURIComponent(talent)}.json`
  )).data ?? {}
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

// Pending（配信前・配信中で種別が未確定）など、3種別以外はサイトに出さない
function isShownType(t: string): t is VideoType {
  return t === 'Movie' || t === 'Short' || t === 'LiveArchive'
}

// ----------------------------------------------------------------
// ダッシュボード
// ----------------------------------------------------------------

// 日付指定・期間指定で選べる最初の日。これより前は正式なデータ期間の外
export const MIN_DATE = '2026-04-01'

/** 'YYYY-MM-DD' を n 日ずらす。端末のタイムゾーンに左右されないよう UTC で計算する */
export function addDays(date: string, n: number): string {
  const d = new Date(`${date}T00:00:00Z`)
  d.setUTCDate(d.getUTCDate() + n)
  return d.toISOString().slice(0, 10)
}

/** 各タレントの記録を始めた日（途中から加わったタレントは 2026-04-26 などになる） */
function talentFirstDates(summary: DashboardSummary): Record<string, string> {
  const out: Record<string, string> = {}
  for (const [talent, cs] of Object.entries(summary.channel_stats)) {
    const first = Object.keys(cs).sort()[0]
    if (first) out[talent] = first
  }
  return out
}

/**
 * 期間 start〜end の集計に要る日別ファイルの日付。
 * 「終わりの日」と「始まりの前日」、加えて期間の途中で記録を始めたタレントの記録開始日。
 * 1日だけ見るときは start = end。
 */
export function rangeDates(summary: DashboardSummary, start: string, end: string): string[] {
  const base = addDays(start, -1)
  const dates = new Set([base, end])
  for (const first of Object.values(talentFirstDates(summary))) {
    if (first > base && first <= end) dates.add(first)
  }
  return [...dates]
}

/**
 * 期間 start〜end に増えた数でランキングを作る（1日だけなら start = end で、前日比になる）。
 * 増えた数は「終わりの日の累計 − 始まりの前日の累計」。
 * - 始まりの前日に記録が無い動画（期間中に公開されたもの）は 0 から数える
 * - 途中から加わったタレントは、記録を始めた日から数える（0 から数えると昔からの再生数まで増えた数に入るため）。
 *   期間がまるごと記録開始より前なら nodata にする
 * snaps には rangeDates() で挙げた日の日別ファイルを渡す。
 */
export function buildRangeData(
  summary: DashboardSummary,
  flags: VideoFlags,
  start: string,
  end: string,
  snaps: Record<string, DailySnapshot>,
) {
  const base = addDays(start, -1)
  const firstDates = talentFirstDates(summary)
  const endSnap = snaps[end]?.v ?? {}

  const videosByTalent = new Map<string, DashboardSummary['videos']>()
  for (const v of summary.videos) {
    const arr = videosByTalent.get(v.t)
    if (arr) arr.push(v)
    else videosByTalent.set(v.t, [v])
  }

  const singerData: SingerRankItem[] = []
  const videoData: Record<VideoType, VideoRankItem[]> = { Movie: [], Short: [], LiveArchive: [] }

  for (const talent of Object.keys(summary.channel_stats)) {
    const first = firstDates[talent]
    if (!first || first > end) {
      singerData.push({
        talent, nodata: true,
        subs_n: 0, subs_diff: null, subs_rate: null,
        views_n: 0, views_diff: null, views_rate: null,
        comments_n: 0, comments_diff: null, comments_rate: null,
        content_total: 0, content_movie: 0, content_short: 0, content_live: 0,
        content_diff: null, content_rate: null,
      })
      continue
    }
    const baseDate = first > base ? first : base
    const baseSnap = snaps[baseDate]?.v ?? {}
    const cs = summary.channel_stats[talent] as Record<string, ChannelStats>
    const n = cs[end], p = cs[baseDate]
    const subs_n  = n?.登録者数 ?? 0
    const views_n = n?.総再生数 ?? 0
    const subs_diff  = (n && p) ? subs_n  - (p.登録者数 ?? 0) : null
    const views_diff = (n && p) ? views_n - (p.総再生数 ?? 0) : null

    let comments_n = 0, comments_diff = 0
    let content_movie = 0, content_short = 0, content_live = 0, content_p = 0
    for (const v of videosByTalent.get(talent) ?? []) {
      const e = endSnap[v.id]
      if (!e) continue  // 終わりの日にまだ無い（後で公開された）動画
      const b = baseSnap[v.id] ?? [0, 0, 0]
      comments_n += e[2]
      comments_diff += e[2] - b[2]
      const vtype = flags[talent]?.[v.id] ?? v.ty
      if (!isShownType(vtype)) continue
      if (vtype === 'Movie') content_movie++
      else if (vtype === 'Short') content_short++
      else content_live++
      if (baseSnap[v.id]) content_p++
      const vd = e[0] - b[0]
      videoData[vtype].push({
        talent, vid_id: v.id, title: v.ti,
        views_n: e[0], views_diff: vd, views_rate: rate(e[0], vd),
        likes_n: e[1], likes_diff: e[1] - b[1],
        comments_n: e[2], comments_diff: e[2] - b[2],
      })
    }
    const content_total = content_movie + content_short + content_live
    const content_diff = content_total - content_p

    singerData.push({
      talent, subs_n, views_n,
      subs_diff,  subs_rate:  rate(subs_n,  subs_diff),
      views_diff, views_rate: rate(views_n, views_diff),
      comments_n, comments_diff, comments_rate: rate(comments_n, comments_diff),
      content_total, content_movie, content_short, content_live,
      content_diff, content_rate: rate(content_total, content_diff),
    })
  }

  return { singerData, videoData }
}

export function buildStatsData(summary: DashboardSummary): { date: string; subs: number; views: number }[] {
  const dateMap = new Map<string, { subs: number; views: number }>()

  for (const cs of Object.values(summary.channel_stats)) {
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

export interface MilestoneForecast {
  talent: string
  kind: '登録者数' | '総再生数'
  value: number      // 今の値
  milestone: number  // 次のキリ番
  date: string       // 届く予想日
  days: number       // 最新の集計日から何日後か
}

const dayDiff = (from: string, to: string) =>
  Math.round((Date.parse(`${to}T00:00:00Z`) - Date.parse(`${from}T00:00:00Z`)) / 86400000)

/** 次のキリ番。いちばん上の桁が1つ上がる数（8,990→9,000、29,600→30,000、7,792,409→8,000,000） */
function nextMilestone(value: number): number {
  const unit = 10 ** (String(Math.floor(value)).length - 1)
  return (Math.floor(value / unit) + 1) * unit
}

/**
 * 登録者数・総再生数が、最新の集計日から within 日以内に次のキリ番へ届きそうなシンガーを、近い順に返す。
 * 増え方は直近30日の1日平均で見る。チャンネルの総再生数は数日同じ値のまま止まることがあり、短い期間の平均では外れるため。
 */
export function buildMilestoneForecast(summary: DashboardSummary, within = 30): MilestoneForecast[] {
  const result: MilestoneForecast[] = []
  for (const [talent, cs] of Object.entries(summary.channel_stats)) {
    const dates = Object.keys(cs).sort()
    const last = dates.at(-1)
    if (!last) continue
    const from = dates.find(d => d >= addDays(last, -30))!
    const span = dayDiff(from, last)
    if (span <= 0) continue
    for (const kind of ['登録者数', '総再生数'] as const) {
      const value = cs[last][kind]
      const before = cs[from][kind]
      if (!value || before == null) continue
      const perDay = (value - before) / span
      if (perDay <= 0) continue
      const milestone = nextMilestone(value)
      const date = addDays(last, Math.ceil((milestone - value) / perDay))
      const days = dayDiff(summary.n_date, date)
      if (days <= within) result.push({ talent, kind, value, milestone, date, days })
    }
  }
  return result.sort((a, b) => a.days - b.days)
}

export function buildDailyViewsByTalent(
  summary: DashboardSummary
): { views: Record<string, number>; date: string } | null {
  if (!summary.p_date) return null

  const views: Record<string, number> = {}
  for (const talent of Object.keys(summary.channel_stats)) views[talent] = 0
  for (const v of summary.videos) {
    if (v.vn === null || v.vp === null) continue
    const diff = v.vn - v.vp
    if (diff > 0) views[v.t] = (views[v.t] ?? 0) + diff
  }

  return { views, date: summary.n_date }
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
    const type = flags[talentName]?.[vid_id] ?? vid.type ?? 'Movie'
    if (!isShownType(type)) continue

    const sorted = Object.keys(vid.records).sort()
    const last = vid.records[sorted.at(-1) ?? ''] ?? {}
    const current_views    = last.再生数   ?? 0
    const current_likes    = last.高評価数 ?? 0
    const current_comments = last.コメント数 ?? 0

    const daily_views:    (number | null)[] = []
    const daily_likes:    (number | null)[] = []
    const daily_comments: (number | null)[] = []
    const daily_dates:    string[]           = []
    for (let i = 1; i <= 15; i++) {
      if (sorted.length > i) {
        const dateStr = sorted[sorted.length - i]
        const curr = vid.records[dateStr]                       ?? {}
        const prev = vid.records[sorted[sorted.length - i - 1]] ?? {}
        daily_views.push((curr.再生数   ?? 0) - (prev.再生数   ?? 0))
        daily_likes.push((curr.高評価数 ?? 0) - (prev.高評価数 ?? 0))
        daily_comments.push((curr.コメント数 ?? 0) - (prev.コメント数 ?? 0))
        daily_dates.push(dateStr)
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
      type,
      公開日: vid.公開日 ?? '',
      再生数: current_views,
      再生数15d増加: daily_views.reduce<number>((a, v) => a + (v ?? 0), 0),
      高評価数: current_likes,
      高評価15d増加: daily_likes.reduce<number>((a, v) => a + (v ?? 0), 0),
      コメント数: current_comments,
      再生数daily: daily_views,
      再生数daily_dates: daily_dates,
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
      const vtype = flags[talentName]?.[vid_id] ?? vid.type ?? 'Movie'
      if (!isShownType(vtype)) continue
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
    const vtype = flags[talentName]?.[vid_id] ?? vid.type ?? 'Movie'
    if (!isShownType(vtype)) continue

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

// 事前集計済み（auto_check.pyのbuild_dashboard_summary）をそのまま返す。
// video_flags.jsonの手動変更は次回の自動収集まで反映が遅れる点に注意
// （ランキングテーブル側はvideos[].tyにflagsをその場で適用するため即時反映のまま）。
export function buildDashboardDailyViewsBreakdown(summary: DashboardSummary): DailyViewsEntry[] {
  return summary.daily_type_breakdown
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

      const vtype = flags[talentName]?.[vid_id] ?? vid.type ?? 'Movie'
      if (!isShownType(vtype)) continue
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
