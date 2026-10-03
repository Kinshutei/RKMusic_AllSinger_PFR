export type VideoType = 'Movie' | 'Short' | 'LiveArchive'
// 配信前・配信中で種別がまだ決まらない動画。データには入るが、サイトには出さない
export type StoredType = VideoType | 'Pending'
export type VideoFlags = Record<string, Record<string, VideoType>>

export interface ChannelStats {
  登録者数: number
  総再生数: number
  動画数: number
}

export interface VideoRecord {
  再生数: number
  高評価数: number
  コメント数: number
}

export interface VideoHistoryEntry {
  タイトル: string
  公開日: string
  type: StoredType
  records: Record<string, VideoRecord>
}

export interface TalentHistory {
  _channel_stats: Record<string, ChannelStats>
  [videoId: string]: VideoHistoryEntry | Record<string, ChannelStats>
}

export interface AllHistory {
  [talentName: string]: TalentHistory
}

export interface SingerRankItem {
  talent: string
  nodata?: boolean  // 選んだ期間がまるごと記録開始より前（途中から加わったタレント）
  subs_n: number
  subs_diff: number | null
  subs_rate: number | null
  views_n: number
  views_diff: number | null
  views_rate: number | null
  comments_n: number
  comments_diff: number | null
  comments_rate: number | null
  content_total: number
  content_movie: number
  content_short: number
  content_live: number
  content_diff: number | null
  content_rate: number | null
}

export interface VideoRankItem {
  talent: string
  vid_id: string
  title: string
  views_n: number
  views_diff: number | null
  views_rate: number | null
  likes_n: number
  likes_diff: number | null
  comments_n: number
  comments_diff: number | null
}

export interface VideoCard {
  id: string
  タイトル: string
  type: VideoType
  公開日: string
  再生数: number
  再生数15d増加: number
  高評価数: number
  高評価15d増加: number
  コメント数: number
  再生数daily: (number | null)[]
  再生数daily_dates: string[]
  高評価daily: (number | null)[]
  コメント数daily: (number | null)[]
  collab_tags: string[]
}

export interface CommentItem {
  text: string
  likes: number
  sentiment: 'positive' | 'neutral' | 'negative'
}

export interface VideoCommentData {
  fetched_at: string
  total_fetched: number
  sentiment: {
    positive: number
    neutral: number
    negative: number
  }
  display_comments: CommentItem[]
}

export type ChannelComments = Record<string, VideoCommentData>
export type AllComments = Record<string, ChannelComments>

// ----------------------------------------------------------------
// Dashboard用軽量サマリー（auto_check.pyが生成するdashboard_summary.json）
// ----------------------------------------------------------------

export interface DashboardVideoSnapshot {
  t: string       // talent
  id: string      // vid_id
  ti: string      // タイトル
  ty: StoredType
  vn: number | null // 再生数 at n_date
  ln: number | null // 高評価数 at n_date
  cn: number | null // コメント数 at n_date
  vp: number | null // 再生数 at p_date
  lp: number | null // 高評価数 at p_date
  cp: number | null // コメント数 at p_date
}

export interface DailyTypeBreakdownEntry {
  date: string
  Movie: number
  Short: number
  LiveArchive: number
}

// 日付指定用の日別ファイル（auto_check.py が daily/YYYY-MM-DD.json に書く）。その日0時時点の累計
export interface DailySnapshot {
  date: string
  v: Record<string, [number, number, number]>  // 動画ID → [再生数, 高評価数, コメント数]
}

export interface DashboardSummary {
  generated_at: string
  n_date: string
  p_date: string | null
  channel_stats: Record<string, Record<string, ChannelStats>>
  daily_type_breakdown: DailyTypeBreakdownEntry[]
  videos: DashboardVideoSnapshot[]
}
