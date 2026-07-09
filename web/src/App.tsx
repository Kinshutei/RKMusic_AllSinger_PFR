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
  const [failedTalents, setFailedTalents] = useState<string[]>([])
  const [activePage, setActivePage] = useState<Page>('Dashboard')
  const [sidebarOpen, setSidebarOpen] = useState(false)

  useEffect(() => {
    // comments取得はhistoryより優先度が低いため後段で行い、
    // raw.githubusercontent.comのレート制限枠をhistory取得に優先して使わせる。
    (async () => {
      try {
        const [h, f] = await Promise.all([loadHistory(), loadVideoFlags()])
        const c = await loadComments()
        setHistory(h.data)
        setFlags(f)
        setComments(c.data)
        setFailedTalents(h.failedTalents)
      } catch (e) {
        setError(String(e))
      } finally {
        setLoading(false)
      }
    })()
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
          {!loading && !error && failedTalents.length > 0 && (
            <p className="error-text">
              一部データの取得に失敗しました（再読み込みで解消する場合があります）: {failedTalents.join('、')}
            </p>
          )}
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
