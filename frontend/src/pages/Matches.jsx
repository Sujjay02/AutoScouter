import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Activity, RefreshCw } from 'lucide-react'

export default function Matches() {
  const [matches, setMatches] = useState([])
  const [loading, setLoading] = useState(false)

  const fetch_ = async () => {
    setLoading(true)
    try {
      const r = await fetch('/api/matches')
      setMatches(await r.json())
    } catch {}
    setLoading(false)
  }
  useEffect(() => { fetch_() }, [])

  return (
    <div style={{ maxWidth: 900 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: '1.5rem' }}>
        <Activity size={22} color="var(--accent)" />
        <h1 style={{ fontSize: 22, fontWeight: 800 }}>Scouted Matches</h1>
        <div style={{ flex: 1 }} />
        <button className="btn-ghost" onClick={fetch_} disabled={loading}>
          <RefreshCw size={14} style={{ marginRight: 4, display: 'inline' }} />
          Refresh
        </button>
      </div>

      {matches.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
          {loading ? 'Loading…' : 'No matches scouted yet.'}
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {matches.map(m => (
            <div key={m.match_key} className="card">
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <Link to={`/matches`} style={{ fontWeight: 800, fontSize: 15 }}>
                      {m.match_key}
                    </Link>
                    {m.is_active && (
                      <span className="badge badge-green">
                        <span className="pulse-dot" style={{ width: 6, height: 6, marginRight: 2 }} />
                        LIVE
                      </span>
                    )}
                    <PhaseBadge phase={m.match_phase} />
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
                    twitch.tv/{m.twitch_channel}
                    {m.event_key && ` · ${m.event_key}`}
                    {' · '}{m.started_at ? new Date(m.started_at).toLocaleString() : ''}
                  </div>
                </div>

                <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                  <AllianceChip teams={m.red_alliance} color="var(--red)" />
                  <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>vs</span>
                  <AllianceChip teams={m.blue_alliance} color="var(--blue)" />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function PhaseBadge({ phase }) {
  const map = {
    auto: ['badge-yellow', 'AUTO'],
    teleop: ['badge-green', 'TELEOP'],
    endgame: ['badge-red', 'ENDGAME'],
    pre_match: ['badge-gray', 'PRE'],
    post_match: ['badge-gray', 'DONE'],
  }
  const [cls, label] = map[phase] || ['badge-gray', phase || '?']
  return <span className={`badge ${cls}`}>{label}</span>
}

function AllianceChip({ teams, color }) {
  if (!teams?.length) return null
  return (
    <div style={{ display: 'flex', gap: 4 }}>
      {teams.map(t => (
        <Link
          key={t}
          to={`/teams/${t}`}
          style={{
            padding: '2px 8px', borderRadius: 999, fontSize: 12, fontWeight: 700,
            background: color + '22', color, textDecoration: 'none',
          }}
        >
          {t}
        </Link>
      ))}
    </div>
  )
}
