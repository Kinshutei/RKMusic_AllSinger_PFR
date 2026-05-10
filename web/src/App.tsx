import { useState, useEffect } from 'react'
import { AllHistory, VideoFlags } from './types'
import { loadHistory, loadVideoFlags, getAvailableTalents } from './utils/data'
import DashboardPage from './components/DashboardPage'
import TalentPage from './components/TalentPage'
import Footer from './components/Footer'
import './App.css'

type Page = string  // 'Dashboard' or talent name

export default function App() {
  const [history, setHistory]       = useState<AllHistory | null>(null)
  const [flags, setFlags]           = useState<VideoFlags>({})
  const [loading, setLoading]       = useState(true)
  const [error, setError]           = useState<string | null>(null)
  const [activePage, setActivePage] = useState<Page>('Dashboard')

  useEffect(() => {
    Promise.all([loadHistory(), loadVideoFlags()])
      .then(([h, f]) => { setHistory(h); setFlags(f) })
      .catch(e => setError(String(e)))
      .finally(() => setLoading(false))
  }, [])

  const talents = history ? getAvailableTalents(history) : ['Dashboard']

  return (
    <div className="app-layout">
      {/* ヘッダー */}
      <header className="app-header">
        <span className="app-header-title">RKMusic AllSinger PFR</span>
      </header>

      {/* サイドバー */}
      <aside className="sidebar">
        <nav className="sidebar-nav">
          {talents.map(talent => (
            <button
              key={talent}
              className={`sidebar-nav-btn${activePage === talent ? ' active' : ''}`}
              onClick={() => setActivePage(talent)}
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
              : <TalentPage history={history} talentName={activePage} flags={flags} />
          )}
        </div>
        <Footer />
      </div>
    </div>
  )
}
