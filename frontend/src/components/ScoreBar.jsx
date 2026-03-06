export function ScoreBar({ value, max = 100, color }) {
  const pct = Math.min(100, Math.max(0, (value / max) * 100))
  return (
    <div className="score-bar">
      <div
        className="score-bar-fill"
        style={{
          width: `${pct}%`,
          background: color || 'linear-gradient(90deg, var(--accent), var(--accent2))',
        }}
      />
    </div>
  )
}

export function CategoryScore({ label, value, max = 100 }) {
  const pct = Math.round((value / max) * 100)
  let color = 'var(--green)'
  if (pct < 40) color = 'var(--red)'
  else if (pct < 65) color = 'var(--yellow)'
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12 }}>
        <span style={{ color: 'var(--text-muted)' }}>{label}</span>
        <span style={{ fontWeight: 700, color }}>{value.toFixed(1)}</span>
      </div>
      <ScoreBar value={value} max={max} color={pct >= 65 ? undefined : pct >= 40 ? 'var(--yellow)' : 'var(--red)'} />
    </div>
  )
}
