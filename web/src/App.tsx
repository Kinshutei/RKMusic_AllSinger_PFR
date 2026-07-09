import { useState, useEffect, useRef } from 'react'
import { AllHistory, VideoFlags, ChannelComments, DashboardSummary } from './types'
import { loadDashboardSummary, loadVideoFlags, loadTalentHistory, loadTalentComments, TALENT_ORDER } from './utils/data'
import DashboardPage from './components/DashboardPage'
import TalentPage from './components/TalentPage'
import Footer from './components/Footer'
import './App.css'

type Page = string

export default function App() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null)
  const [flags, setFlags]     = useState<VideoFlags>({})
  const [summaryLoading, setSummaryLoading] = useState(true)
  const [summaryError, setSummaryError]     = useState<string | null>(null)

  const [talentCache, setTalentCache]     = useState<Record<string, AllHistory[string] | null>>({})
  const [commentsCache, setCommentsCache] = useState<Record<string, ChannelComments>>({})
  const [talentLoading, setTalentLoading] = useState<Record<string, boolean>>({})
  const [talentError, setTalentError]     = useState<Record<string, string | null>>({})
  const inFlightRef = useRef<Set<string>>(new Set())

  const [activePage, setActivePage] = useState<Page>('Dashboard')
  const [sidebarOpen, setSidebarOpen] = useState(false)

  useEffect(() => {
    (async () => {
      try {
        const [s, f] = await Promise.all([loadDashboardSummary(), loadVideoFlags()])
        setSummary(s)
        setFlags(f)
      } catch (e) {
        setSummaryError(String(e))
      } finally {
        setSummaryLoading(false)
      }
    })()
  }, [])

  async function ensureTalentLoaded(talent: string) {
    if (talent === 'Dashboard') return
    if (talent in talentCache || inFlightRef.current.has(talent)) return
    inFlightRef.current.add(talent)
    setTalentLoading(prev => ({ ...prev, [talent]: true }))
    setTalentError(prev => ({ ...prev, [talent]: null }))
    try {
      const [h, c] = await Promise.all([loadTalentHistory(talent), loadTalentComments(talent)])
      if (h.failed) {
        setTalentError(prev => ({ ...prev, [talent]: 'データの取得に失敗しました' }))
      } else {
        setTalentCache(prev => ({ ...prev, [talent]: h.data }))
        setCommentsCache(prev => ({ ...prev, [talent]: c }))
      }
    } finally {
      inFlightRef.current.delete(talent)
      setTalentLoading(prev => ({ ...prev, [talent]: false }))
    }
  }

  function navigate(page: Page) {
    setActivePage(page)
    setSidebarOpen(false)
    if (page !== 'Dashboard') void ensureTalentLoaded(page)
  }

  const talentHistoryForPage: AllHistory =
    activePage in talentCache && talentCache[activePage]
      ? { [activePage]: talentCache[activePage] }
      : {}

  return (
    <div className="app-layout">
      {/* ヘッダー */}
      <header className="app-header">
        <button
          className="hamburger-btn"
          onClick={() => setSidebarOpen(o => !o)}
          aria-label="メニュー"
        >
          <span />
          <span />
          <span />
        </button>
        <span className="app-header-title">RKMusic AllSinger PFR</span>
      </header>

      {/* オーバーレイ */}
      {sidebarOpen && (
        <div className="sidebar-overlay" onClick={() => setSidebarOpen(false)} />
      )}

      {/* サイドバー */}
      <aside className={`sidebar${sidebarOpen ? ' sidebar--open' : ''}`}>
        <nav className="sidebar-nav">
          {TALENT_ORDER.map(talent => (
            <button
              key={talent}
              className={`sidebar-nav-btn${activePage === talent ? ' active' : ''}`}
              onClick={() => navigate(talent)}
            >
              {talent}
            </button>
          ))}
        </nav>
      </aside>

      {/* メインコンテンツ */}
      <div className="main-wrapper">
        <div className="content">
          {activePage === 'Dashboard' ? (
            summaryError ? (
              <p className="error-text">データの取得に失敗しました: {summaryError}</p>
            ) : summaryLoading ? (
              <p className="muted">読み込み中...</p>
            ) : !summary ? (
              <p className="muted">集計データを準備中です。しばらくしてから再度お試しください。</p>
            ) : (
              <DashboardPage summary={summary} flags={flags} />
            )
          ) : (
            talentError[activePage] ? (
              <p className="error-text">
                {talentError[activePage]}
                {' '}
                <button onClick={() => ensureTalentLoaded(activePage)}>再試行</button>
              </p>
            ) : talentLoading[activePage] || !(activePage in talentCache) ? (
              <p className="muted">読み込み中...</p>
            ) : (
              <TalentPage
                key={activePage}
                history={talentHistoryForPage}
                talentName={activePage}
                flags={flags}
                comments={{ [activePage]: commentsCache[activePage] ?? {} }}
              />
            )
          )}
        </div>
        <Footer />
      </div>
    </div>
  )
}
