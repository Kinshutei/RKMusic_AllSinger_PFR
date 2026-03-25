export type VideoType = 'Movie' | 'Short' | 'LiveArchive'

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
  type: VideoType
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
  subs_n: number
  subs_diff: number | null
  subs_rate: number | null
  views_n: number
  views_diff: number | null
  views_rate: number | null
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
  再生数: number
  再生数5d増加: number
  高評価数: number
  高評価5d増加: number
  再生数daily: (number | null)[]
  高評価daily: (number | null)[]
}
