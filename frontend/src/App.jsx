import { Routes, Route, NavLink, useLocation } from 'react-router-dom'
import { Activity, BarChart3, Radio, Trophy, Settings } from 'lucide-react'
import Rankings from './pages/Rankings.jsx'
import Scout from './pages/Scout.jsx'
import Matches from './pages/Matches.jsx'
import TeamDetail from './pages/TeamDetail.jsx'
import { LiveFeed } from './components/LiveFeed.jsx'
import { useWebSocket } from './hooks/useWebSocket.js'
import { useState } from 'react'

const NAV = [
  { to: '/', icon: Trophy, label: 'Rankings' },
  { to: '/scout', icon: Radio, label: 'Scout' },
  { to: '/matches', icon: Activity, label: 'Matches' },
]

export default function App() {
  const [liveEvents, setLiveEvents] = useState([])
  const { connected } = useWebSocket((msg) => {
    if (msg.type === 'frame_result') {
      setLiveEvents(prev => [msg.data, ...prev].slice(0, 50))
    }
  })

  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      {/* Sidebar */}
      <aside style={{
        width: 220,
        background: 'var(--surface)',
        borderRight: '1px solid var(--border)',
        display: 'flex',
        flexDirection: 'column',
        padding: '1.5rem 1rem',
        gap: '0.5rem',
        flexShrink: 0,
      }}>
        <div style={{ marginBottom: '1.5rem' }}>
          <div style={{ fontSize: 18, fontWeight: 800, color: '#fff' }}>
            🤖 AutoScouter
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>
            FRC Reefscape 2025
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: '0.75rem' }}>
          <div className={connected ? 'pulse-dot' : ''} style={{
            width: 8, height: 8, borderRadius: '50%',
            background: connected ? 'var(--green)' : 'var(--text-muted)'
          }} />
          <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
            {connected ? 'Connected' : 'Offline'}
          </span>
        </div>

        {NAV.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            style={({ isActive }) => ({
              display: 'flex', alignItems: 'center', gap: 10,
              padding: '8px 12px', borderRadius: 8,
              color: isActive ? '#fff' : 'var(--text-muted)',
              background: isActive ? 'var(--accent)' : 'transparent',
              textDecoration: 'none', fontWeight: 600, fontSize: 14,
              transition: 'all .15s',
            })}
          >
            <Icon size={16} />
            {label}
          </NavLink>
        ))}
      </aside>

      {/* Main content */}
      <main style={{ flex: 1, overflow: 'auto', padding: '1.5rem', maxWidth: 'calc(100vw - 220px)' }}>
        <Routes>
          <Route path="/" element={<Rankings />} />
          <Route path="/scout" element={<Scout />} />
          <Route path="/matches" element={<Matches />} />
          <Route path="/teams/:teamNumber" element={<TeamDetail />} />
        </Routes>
      </main>

      {/* Live feed panel */}
      {liveEvents.length > 0 && <LiveFeed events={liveEvents} />}
    </div>
  )
}
