import { useState, useEffect } from 'react'
import { AllHistory } from './types'
import { loadHistory, getAvailableTalents } from './utils/data'
import DashboardPage from './components/DashboardPage'
import TalentPage from './components/TalentPage'
import Footer from './components/Footer'
import './App.css'

type Page = string  // 'Dashboard' or talent name

export default function App() {
  const [history, setHistory]       = useState<AllHistory | null>(null)
  const [loading, setLoading]       = useState(true)
  const [error, setError]           = useState<string | null>(null)
  const [activePage, setActivePage] = useState<Page>('Dashboard')
  const [sidebarOpen, setSidebarOpen] = useState(true)

  useEffect(() => {
    loadHistory()
      .then(h => setHistory(h))
      .catch(e => setError(String(e)))
      .finally(() => setLoading(false))
  }, [])

  const talents = history ? getAvailableTalents(history) : ['Dashboard']

  const handleSelect = (page: Page) => {
    setActivePage(page)
    setSidebarOpen(false)
  }

  return (
    <>
      {/* サイドバー */}
      <aside className={`sidebar${sidebarOpen ? ' sidebar-open' : ''}`}>
        <button
          className="sidebar-toggle"
          onClick={() => setSidebarOpen(o => !o)}
          aria-label={sidebarOpen ? 'Close menu' : 'Open menu'}
        >
          <span>ME</span>
          <span>NU</span>
        </button>
        <nav className="sidebar-nav">
          {talents.map(talent => (
            <button
              key={talent}
              className={`sidebar-nav-btn${activePage === talent ? ' active' : ''}`}
              onClick={() => handleSelect(talent)}
            >
              <span className="sidebar-nav-text">{talent}</span>
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
              ? <DashboardPage history={history} />
              : <TalentPage history={history} talentName={activePage} />
          )}
        </div>
        <Footer />
      </div>
    </>
  )
}
