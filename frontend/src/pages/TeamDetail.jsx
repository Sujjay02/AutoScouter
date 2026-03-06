import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { ArrowLeft, Star, AlertTriangle } from 'lucide-react'
import { RadarChart, PolarGrid, PolarAngleAxis, Radar, ResponsiveContainer, Tooltip } from 'recharts'
import { CategoryScore } from '../components/ScoreBar.jsx'

export default function TeamDetail() {
  const { teamNumber } = useParams()
  const [team, setTeam] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [note, setNote] = useState('')
  const [noteSaved, setNoteSaved] = useState(false)

  useEffect(() => {
    fetch(`/api/teams/${teamNumber}`)
      .then(r => r.ok ? r.json() : Promise.reject(r.statusText))
      .then(d => { setTeam(d); setNote(d.notes || '') })
      .catch(e => setError(String(e)))
      .finally(() => setLoading(false))
  }, [teamNumber])

  const saveNote = async () => {
    await fetch(`/api/teams/${teamNumber}/notes`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ notes: note }),
    })
    setNoteSaved(true)
    setTimeout(() => setNoteSaved(false), 2000)
  }

  if (loading) return <div style={{ color: 'var(--text-muted)' }}>Loading…</div>
  if (error) return (
    <div>
      <Link to="/" style={{ fontSize: 13 }}>← Back</Link>
      <div className="card" style={{ marginTop: 16, color: 'var(--red)' }}>
        <AlertTriangle size={16} style={{ marginRight: 6 }} />
        {error === 'Not Found' ? `Team ${teamNumber} not yet in scouting data.` : error}
      </div>
    </div>
  )

  const radarData = Object.entries(team.scores).map(([key, cat]) => ({
    subject: cat.label,
    value: cat.avg,
    fullMark: 100,
  }))

  return (
    <div style={{ maxWidth: 900 }}>
      <Link to="/" style={{ fontSize: 13, display: 'inline-flex', alignItems: 'center', gap: 4, marginBottom: '1rem' }}>
        <ArrowLeft size={14} /> Back to Rankings
      </Link>

      {/* Header */}
      <div className="card" style={{ marginBottom: '1rem' }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: '1rem', flexWrap: 'wrap' }}>
          <div style={{ flex: 1 }}>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 10 }}>
              <h1 style={{ fontSize: 32, fontWeight: 900 }}>{team.team_number}</h1>
              {team.team_name && (
                <span style={{ fontSize: 18, color: 'var(--text-muted)' }}>{team.team_name}</span>
              )}
            </div>
            {team.tba_name && team.tba_name !== team.team_name && (
              <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>{team.tba_name}</div>
            )}
            {team.location && (
              <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>{team.location}</div>
            )}
            {team.school && (
              <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>{team.school}</div>
            )}
            <div style={{ marginTop: 6, fontSize: 12, color: 'var(--text-muted)' }}>
              {team.matches_scouted} matches scouted
            </div>
          </div>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 48, fontWeight: 900, color: 'var(--accent)', lineHeight: 1 }}>
              {team.overall_score}
            </div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Overall Score</div>
          </div>
        </div>
      </div>

      <div className="grid-2" style={{ marginBottom: '1rem' }}>
        {/* Radar chart */}
        <div className="card">
          <h3 style={{ fontWeight: 700, marginBottom: '0.75rem', fontSize: 14 }}>Performance Radar</h3>
          <ResponsiveContainer width="100%" height={220}>
            <RadarChart data={radarData}>
              <PolarGrid stroke="var(--border)" />
              <PolarAngleAxis
                dataKey="subject"
                tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
              />
              <Radar
                name={String(team.team_number)}
                dataKey="value"
                stroke="var(--accent)"
                fill="var(--accent)"
                fillOpacity={0.25}
              />
              <Tooltip
                contentStyle={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8 }}
                labelStyle={{ color: 'var(--text)' }}
              />
            </RadarChart>
          </ResponsiveContainer>
        </div>

        {/* Event stats */}
        <div className="card">
          <h3 style={{ fontWeight: 700, marginBottom: '0.75rem', fontSize: 14 }}>Event Stats</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <Stat label="Total FUEL Scored" value={team.events.total_fuel_scored} />
            <Stat label="Penalties" value={team.events.total_penalties} color="var(--red)" />
            <Stat
              label="Tower Climbs"
              value={`${team.events.climb_successes} / ${team.events.climb_attempts} attempts`}
            />
            <Stat
              label="Best Climb Level"
              value={team.events.best_climb_level ? `L${team.events.best_climb_level}` : 'None'}
              color={team.events.best_climb_level === 3 ? 'var(--green)' : team.events.best_climb_level === 2 ? 'var(--yellow)' : 'var(--text)'}
            />
            <Stat
              label="Climb Success Rate"
              value={`${team.events.climb_success_rate}%`}
              color={team.events.climb_success_rate >= 70 ? 'var(--green)' : 'var(--yellow)'}
            />
            <Stat label="Auto Climb Bonuses" value={team.events.auto_climb_bonuses} />
            <Stat label="Trench Passes" value={team.events.trench_uses} />
          </div>
        </div>
      </div>

      {/* Category scores */}
      <div className="card" style={{ marginBottom: '1rem' }}>
        <h3 style={{ fontWeight: 700, marginBottom: '1rem', fontSize: 14 }}>Category Breakdown</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: '1rem' }}>
          {Object.entries(team.scores).map(([key, cat]) => (
            <div key={key}>
              <CategoryScore label={cat.label} value={cat.avg} />
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>{cat.description}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Scout notes */}
      <div className="card" style={{ marginBottom: '1rem' }}>
        <h3 style={{ fontWeight: 700, marginBottom: '0.75rem', fontSize: 14 }}>
          <Star size={14} style={{ marginRight: 6, display: 'inline' }} />
          Scout Notes
        </h3>
        <textarea
          value={note}
          onChange={e => setNote(e.target.value)}
          placeholder="Add manual scouting notes…"
          rows={3}
          style={{ marginBottom: 8 }}
        />
        <button className="btn-primary" onClick={saveNote} style={{ width: 'auto' }}>
          {noteSaved ? '✓ Saved' : 'Save Notes'}
        </button>
      </div>

      {/* Recent observations */}
      {team.observations.length > 0 && (
        <div className="card">
          <h3 style={{ fontWeight: 700, marginBottom: '0.75rem', fontSize: 14 }}>Recent AI Observations</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {team.observations.slice().reverse().map((o, i) => (
              <div key={i} style={{
                padding: '8px 12px', background: 'var(--surface2)',
                borderRadius: 8, fontSize: 12,
              }}>
                <div style={{ display: 'flex', gap: 8, marginBottom: 2 }}>
                  <span style={{ fontWeight: 700 }}>{o.match_key}</span>
                  <span className={`badge badge-${o.phase === 'auto' ? 'yellow' : o.phase === 'teleop' ? 'green' : 'gray'}`}>
                    {o.phase}
                  </span>
                  <span style={{ marginLeft: 'auto', color: 'var(--text-muted)' }}>
                    Frame {o.frame} · {Math.round(o.confidence * 100)}% conf
                  </span>
                </div>
                <div style={{ color: 'var(--text-muted)' }}>{o.analysis}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function Stat({ label, value, color }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13 }}>
      <span style={{ color: 'var(--text-muted)' }}>{label}</span>
      <span style={{ fontWeight: 700, color: color || 'var(--text)' }}>{value}</span>
    </div>
  )
}
