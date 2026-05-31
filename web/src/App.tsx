import { useState, useEffect } from 'react'
import { AllHistory, VideoFlags, AllComments } from './types'
import { loadHistory, loadVideoFlags, loadComments, getAvailableTalents } from './utils/data'
import DashboardPage from './components/DashboardPage'
import TalentPage from './components/TalentPage'
import Footer from './components/Footer'
import './App.css'

type Page = string

export default function App() {
  const [history, setHistory]   = useState<AllHistory | null>(null)
  const [flags, setFlags]       = useState<VideoFlags>({})
  const [comments, setComments] = useState<AllComments>({})
  const [loading, setLoading]   = useState(true)
  const [error, setError]       = useState<string | null>(null)
  const [activePage, setActivePage] = useState<Page>('Dashboard')
  const [sidebarOpen, setSidebarOpen] = useState(false)

  useEffect(() => {
    Promise.all([loadHistory(), loadVideoFlags(), loadComments()])
      .then(([h, f, c]) => { setHistory(h); setFlags(f); setComments(c) })
      .catch(e => setError(String(e)))
      .finally(() => setLoading(false))
  }, [])

  const talents = history ? getAvailableTalents(history) : ['Dashboard']

  function navigate(page: Page) {
    setActivePage(page)
    setSidebarOpen(false)
  }

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
          {talents.map(talent => (
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
          {loading && <p className="muted">読み込み中...</p>}
          {error   && <p className="error-text">データの取得に失敗しました: {error}</p>}
          {!loading && !error && history && (
            activePage === 'Dashboard'
              ? <DashboardPage history={history} flags={flags} />
              : <TalentPage key={activePage} history={history} talentName={activePage} flags={flags} comments={comments} />
          )}
        </div>
        <Footer />
      </div>
    </div>
  )
}
