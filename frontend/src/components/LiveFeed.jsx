import { useState } from 'react'
import { ChevronDown, ChevronUp, Zap } from 'lucide-react'

export function LiveFeed({ events }) {
  const [open, setOpen] = useState(true)
  const latest = events[0]

  return (
    <aside style={{
      width: 280, background: 'var(--surface)',
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
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                <span style={{ fontWeight: 700 }}>Frame {ev.frame}</span>
                <PhaseBadge phase={ev.phase} />
              </div>
              {ev.score_red != null && (
                <div style={{ display: 'flex', gap: 8, marginBottom: 4 }}>
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
                {ev.field_observations?.slice(0, 100)}
              </div>
              {ev.robots?.filter(r => r.team_number).map(r => (
                <div key={r.team_number} style={{
                  display: 'flex', alignItems: 'center', gap: 6,
                  padding: '2px 0',
                }}>
                  <span className={`badge badge-${r.alliance === 'red' ? 'red' : r.alliance === 'blue' ? 'blue' : 'gray'}`}>
                    {r.team_number}
                  </span>
                  <span style={{ color: 'var(--text-muted)', fontSize: 11 }}>
                    {r.actions?.slice(0, 2).join(', ')}
                  </span>
                </div>
              ))}
            </div>
          ))}
        </div>
      )}
    </aside>
  )
}

function PhaseBadge({ phase }) {
  const map = {
    auto: ['badge-yellow', 'AUTO'],
    teleop: ['badge-green', 'TELEOP'],
    endgame: ['badge-red', 'ENDGAME'],
    pre_match: ['badge-gray', 'PRE'],
    post_match: ['badge-gray', 'POST'],
  }
  const [cls, label] = map[phase] || ['badge-gray', phase?.toUpperCase() || '?']
  return <span className={`badge ${cls}`}>{label}</span>
}
