import { useState } from 'react'
import { ChevronDown, ChevronUp, Zap } from 'lucide-react'

export function LiveFeed({ events }) {
  const [open, setOpen] = useState(true)

  return (
    <aside style={{
      width: 290, background: 'var(--surface)',
      borderLeft: '1px solid var(--border)',
      display: 'flex', flexDirection: 'column',
      flexShrink: 0, overflow: 'hidden',
    }}>
      <button
        onClick={() => setOpen(o => !o)}
        style={{
          display: 'flex', alignItems: 'center', gap: 8,
          padding: '1rem', background: 'transparent',
          borderRadius: 0, borderBottom: '1px solid var(--border)',
          color: 'var(--text)', fontSize: 13, fontWeight: 700,
          justifyContent: 'space-between',
        }}
      >
        <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <Zap size={14} color="var(--yellow)" />
          Live Feed
          <span className="badge badge-green" style={{ fontSize: 10 }}>
            {events.length}
          </span>
        </span>
        {open ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
      </button>

      {open && (
        <div style={{ flex: 1, overflowY: 'auto', padding: '0.75rem', display: 'flex', flexDirection: 'column', gap: 8 }}>
          {events.map((ev, i) => (
            <div key={i} className="card" style={{ padding: '0.75rem', fontSize: 12 }}>
              {/* Header row */}
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                <span style={{ fontWeight: 700 }}>Frame {ev.frame}</span>
                <PhaseBadge phase={ev.phase} />
              </div>

              {/* Hub shift indicator — the key REBUILT mechanic */}
              {ev.active_hub && ev.active_hub !== 'unknown' && (
                <HubBadge active={ev.active_hub} />
              )}

              {/* Scoreboard */}
              {ev.score_red != null && (
                <div style={{ display: 'flex', gap: 8, marginBottom: 4, marginTop: 4 }}>
                  <span style={{ color: 'var(--red)', fontWeight: 700 }}>R {ev.score_red}</span>
                  <span style={{ color: 'var(--text-muted)' }}>vs</span>
                  <span style={{ color: 'var(--blue)', fontWeight: 700 }}>B {ev.score_blue}</span>
                  {ev.time_remaining != null && (
                    <span style={{ color: 'var(--text-muted)', marginLeft: 'auto' }}>
                      :{String(ev.time_remaining).padStart(2, '0')}
                    </span>
                  )}
                </div>
              )}

              <div style={{ color: 'var(--text-muted)', marginBottom: 4, lineHeight: 1.4 }}>
                {ev.field_observations?.slice(0, 110)}
              </div>

              {/* Per-robot summary */}
              {ev.robots?.filter(r => r.team_number).map(r => (
                <div key={r.team_number} style={{
                  display: 'flex', alignItems: 'center', gap: 5, padding: '2px 0', flexWrap: 'wrap',
                }}>
                  <span className={`badge badge-${r.alliance === 'red' ? 'red' : r.alliance === 'blue' ? 'blue' : 'gray'}`}>
                    {r.team_number}
                  </span>
                  {r.hub_active && (
                    <span style={{ fontSize: 10, color: 'var(--green)', fontWeight: 700 }}>HUB✓</span>
                  )}
                  {r.fuel_scored > 0 && (
                    <span style={{ fontSize: 10, color: 'var(--yellow)' }}>+{r.fuel_scored} FUEL</span>
                  )}
                  {r.fuel_wasted > 0 && (
                    <span style={{ fontSize: 10, color: 'var(--red)' }}>⚠{r.fuel_wasted} wasted</span>
                  )}
                  {r.climb_level > 0 && (
                    <span style={{ fontSize: 10, color: 'var(--accent)', fontWeight: 700 }}>L{r.climb_level}↑</span>
                  )}
                </div>
              ))}
            </div>
          ))}
        </div>
      )}
    </aside>
  )
}

function HubBadge({ active }) {
  const map = {
    red:  { bg: 'rgba(239,68,68,.15)',   color: 'var(--red)',        label: '🔴 Red Hub Active' },
    blue: { bg: 'rgba(59,130,246,.15)',  color: 'var(--blue)',       label: '🔵 Blue Hub Active' },
    both: { bg: 'rgba(34,197,94,.12)',   color: 'var(--green)',      label: '⚡ Both Hubs Active' },
    none: { bg: 'rgba(148,163,184,.08)', color: 'var(--text-muted)', label: '⏸ Hubs Inactive' },
  }
  const style = map[active] || map.none
  return (
    <div style={{
      background: style.bg, color: style.color,
      borderRadius: 6, padding: '2px 8px', fontSize: 11,
      fontWeight: 700, marginBottom: 4, textAlign: 'center',
    }}>
      {style.label}
    </div>
  )
}

function PhaseBadge({ phase }) {
  const map = {
    auto:       ['badge-yellow', 'AUTO'],
    transition: ['badge-gray',   'TRANSITION'],
    shift1:     ['badge-green',  'SHIFT 1'],
    shift2:     ['badge-green',  'SHIFT 2'],
    shift3:     ['badge-green',  'SHIFT 3'],
    shift4:     ['badge-green',  'SHIFT 4'],
    endgame:    ['badge-red',    'ENDGAME'],
    pre_match:  ['badge-gray',   'PRE'],
    post_match: ['badge-gray',   'POST'],
  }
  const [cls, label] = map[phase] || ['badge-gray', phase?.toUpperCase() || '?']
  return <span className={`badge ${cls}`}>{label}</span>
}
