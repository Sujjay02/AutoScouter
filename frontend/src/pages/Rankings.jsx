import { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { Trophy, RefreshCw, ChevronUp, ChevronDown } from 'lucide-react'
import { CategoryScore } from '../components/ScoreBar.jsx'

const CATEGORIES = [
  { key: 'overall_score', label: 'Overall' },
  { key: 'auto_scoring', label: 'Auto' },
  { key: 'fuel_scoring', label: 'FUEL' },
  { key: 'tower_climb', label: 'Tower Climb' },
  { key: 'collection_efficiency', label: 'Collection' },
  { key: 'defense', label: 'Defense' },
  { key: 'trench_usage', label: 'Trench' },
  { key: 'consistency', label: 'Consistency' },
  { key: 'speed', label: 'Speed' },
]

export default function Rankings() {
  const [rankings, setRankings] = useState([])
  const [sortBy, setSortBy] = useState('overall_score')
  const [loading, setLoading] = useState(false)
  const [search, setSearch] = useState('')

  const fetchRankings = useCallback(async () => {
    setLoading(true)
    try {
      const cat = sortBy === 'overall_score' ? '' : `?category=${sortBy}`
      const r = await fetch(`/api/rankings${cat}`)
      const data = await r.json()
      setRankings(data.rankings || [])
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }, [sortBy])

  useEffect(() => { fetchRankings() }, [fetchRankings])

  // Auto-refresh every 15s
  useEffect(() => {
    const t = setInterval(fetchRankings, 15000)
    return () => clearInterval(t)
  }, [fetchRankings])

  const filtered = rankings.filter(t =>
    !search || String(t.team_number).includes(search) ||
    (t.team_name || '').toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div style={{ maxWidth: 1100 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: '1.5rem', flexWrap: 'wrap' }}>
        <Trophy size={22} color="var(--yellow)" />
        <h1 style={{ fontSize: 22, fontWeight: 800 }}>Robot Rankings</h1>
        <div style={{ flex: 1 }} />
        <input
          placeholder="Search team…"
          value={search}
          onChange={e => setSearch(e.target.value)}
          style={{ width: 180 }}
        />
        <button className="btn-ghost" onClick={fetchRankings} disabled={loading}>
          <RefreshCw size={14} style={{ marginRight: 4, display: 'inline' }} />
          Refresh
        </button>
      </div>

      {/* Sort tabs */}
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: '1.25rem' }}>
        {CATEGORIES.map(c => (
          <button
            key={c.key}
            onClick={() => setSortBy(c.key)}
            style={{
              padding: '5px 14px', fontSize: 12, fontWeight: 600,
              background: sortBy === c.key ? 'var(--accent)' : 'var(--surface)',
              color: sortBy === c.key ? '#fff' : 'var(--text-muted)',
              border: '1px solid var(--border)', borderRadius: 999,
              cursor: 'pointer',
            }}
          >
            {c.label}
          </button>
        ))}
      </div>

      {filtered.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
          {loading ? 'Loading…' : 'No teams scouted yet. Start a scouting session to see rankings.'}
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {filtered.map((team) => (
            <RankingRow key={team.team_number} team={team} sortBy={sortBy} />
          ))}
        </div>
      )}
    </div>
  )
}

function RankingRow({ team, sortBy }) {
  const [expanded, setExpanded] = useState(false)
  const isTop3 = team.rank <= 3

  return (
    <div className="card" style={{
      border: isTop3 ? '1px solid var(--accent)' : undefined,
    }}>
      <div
        style={{ display: 'flex', alignItems: 'center', gap: 12, cursor: 'pointer' }}
        onClick={() => setExpanded(e => !e)}
      >
        {/* Rank */}
        <div style={{
          width: 36, height: 36, borderRadius: '50%',
          background: isTop3 ? 'var(--accent)' : 'var(--surface2)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontWeight: 800, fontSize: 14, flexShrink: 0,
          color: isTop3 ? '#fff' : 'var(--text-muted)',
        }}>
          {team.rank <= 3 ? ['🥇', '🥈', '🥉'][team.rank - 1] : team.rank}
        </div>

        {/* Team info */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
            <Link
              to={`/teams/${team.team_number}`}
              onClick={e => e.stopPropagation()}
              style={{ fontWeight: 800, fontSize: 16 }}
            >
              {team.team_number}
            </Link>
            {team.team_name && (
              <span style={{ color: 'var(--text-muted)', fontSize: 12, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {team.team_name}
              </span>
            )}
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
            {team.matches_scouted} match{team.matches_scouted !== 1 ? 'es' : ''} scouted
            {' · '}{team.total_game_pieces} game pieces
            {team.climb_attempts > 0 && ` · ${team.climb_rate}% climb rate`}
          </div>
        </div>

        {/* Overall score */}
        <div style={{ textAlign: 'right', flexShrink: 0 }}>
          <div style={{ fontSize: 22, fontWeight: 800, color: 'var(--accent)' }}>
            {team.overall_score}
          </div>
          <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>overall</div>
        </div>

        {/* Highlighted category */}
        {sortBy !== 'overall_score' && (
          <div style={{ textAlign: 'right', flexShrink: 0, minWidth: 60 }}>
            <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--yellow)' }}>
              {(team[sortBy] ?? team[`avg_${sortBy}`] ?? 0).toFixed(1)}
            </div>
            <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>
              {sortBy.replace('avg_', '').replace(/_/g, ' ')}
            </div>
          </div>
        )}

        {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
      </div>

      {expanded && (
        <div style={{ marginTop: '1rem', paddingTop: '1rem', borderTop: '1px solid var(--border)' }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '0.75rem' }}>
            <CategoryScore label="Auto Period" value={team.avg_auto_scoring} />
            <CategoryScore label="FUEL Scoring" value={team.avg_fuel_scoring} />
            <CategoryScore label="Tower Climb" value={team.avg_tower_climb} />
            <CategoryScore label="Collection" value={team.avg_collection_efficiency} />
            <CategoryScore label="Defense" value={team.avg_defense} />
            <CategoryScore label="Trench Usage" value={team.avg_trench_usage} />
            <CategoryScore label="Consistency" value={team.avg_consistency} />
            <CategoryScore label="Speed & Cycling" value={team.avg_speed} />
          </div>
          <div style={{ marginTop: '0.75rem', display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
            <StatPill label="FUEL Scored" value={team.total_fuel_scored} />
            <StatPill label="Penalties" value={team.total_penalties} color="var(--red)" />
            <StatPill label="Climbs" value={`${team.climb_successes}/${team.climb_attempts}`} />
            <StatPill label="Best Level" value={`L${team.best_climb_level || 0}`} />
            <StatPill label="Climb Rate" value={`${team.climb_rate}%`} />
          </div>
          <div style={{ marginTop: '0.75rem' }}>
            <Link to={`/teams/${team.team_number}`} style={{ fontSize: 12 }}>
              View full profile →
            </Link>
          </div>
        </div>
      )}
    </div>
  )
}

function StatPill({ label, value, color }) {
  return (
    <div style={{ fontSize: 12 }}>
      <span style={{ color: 'var(--text-muted)' }}>{label}: </span>
      <span style={{ fontWeight: 700, color: color || 'var(--text)' }}>{value}</span>
    </div>
  )
}
