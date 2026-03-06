import { useState } from 'react'
import { Radio, StopCircle, AlertCircle, CheckCircle2 } from 'lucide-react'

export default function Scout() {
  const [form, setForm] = useState({
    match_key: '',
    twitch_channel: '',
    event_key: '',
    tba_match_key: '',
    red_alliance: '',
    blue_alliance: '',
    use_mock: false,
  })
  const [status, setStatus] = useState(null)  // null | 'running' | 'stopped' | 'error'
  const [message, setMessage] = useState('')
  const [loading, setLoading] = useState(false)

  const handleChange = e => {
    const { name, value, type, checked } = e.target
    setForm(f => ({ ...f, [name]: type === 'checkbox' ? checked : value }))
  }

  const parseTeams = str => str
    .split(/[,\s]+/)
    .map(s => parseInt(s.trim()))
    .filter(n => !isNaN(n) && n > 0)

  const handleStart = async () => {
    if (!form.match_key || !form.twitch_channel) {
      setMessage('Match key and Twitch channel are required.')
      setStatus('error')
      return
    }
    setLoading(true)
    setMessage('')
    try {
      const body = {
        match_key: form.match_key,
        twitch_channel: form.twitch_channel.replace('https://www.twitch.tv/', '').replace('@', '').trim(),
        event_key: form.event_key || null,
        tba_match_key: form.tba_match_key || null,
        red_alliance: parseTeams(form.red_alliance),
        blue_alliance: parseTeams(form.blue_alliance),
        use_mock: form.use_mock,
      }
      const r = await fetch('/api/matches/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      const data = await r.json()
      if (!r.ok) throw new Error(data.detail || 'Failed to start')
      setStatus('running')
      setMessage(`Scouting started for ${data.match_key} on twitch.tv/${data.channel}`)
    } catch (e) {
      setStatus('error')
      setMessage(e.message)
    } finally {
      setLoading(false)
    }
  }

  const handleStop = async () => {
    if (!form.match_key) return
    setLoading(true)
    try {
      await fetch(`/api/matches/${form.match_key}/stop`, { method: 'POST' })
      setStatus('stopped')
      setMessage(`Scouting stopped for ${form.match_key}`)
    } catch (e) {
      setMessage(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ maxWidth: 680 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: '1.5rem' }}>
        <Radio size={22} color="var(--accent)" />
        <h1 style={{ fontSize: 22, fontWeight: 800 }}>Start Scouting</h1>
      </div>

      <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        <div className="grid-2">
          <div>
            <label style={{ display: 'block', fontSize: 12, color: 'var(--text-muted)', marginBottom: 4 }}>
              Match Key *
            </label>
            <input
              name="match_key"
              value={form.match_key}
              onChange={handleChange}
              placeholder="e.g. 2025casd_qm1"
            />
          </div>
          <div>
            <label style={{ display: 'block', fontSize: 12, color: 'var(--text-muted)', marginBottom: 4 }}>
              Twitch Channel *
            </label>
            <input
              name="twitch_channel"
              value={form.twitch_channel}
              onChange={handleChange}
              placeholder="e.g. firstinspires or twitch.tv/..."
            />
          </div>
        </div>

        <div className="grid-2">
          <div>
            <label style={{ display: 'block', fontSize: 12, color: 'var(--text-muted)', marginBottom: 4 }}>
              Event Key (optional)
            </label>
            <input
              name="event_key"
              value={form.event_key}
              onChange={handleChange}
              placeholder="e.g. 2025casd"
            />
          </div>
          <div>
            <label style={{ display: 'block', fontSize: 12, color: 'var(--text-muted)', marginBottom: 4 }}>
              TBA Match Key (optional)
            </label>
            <input
              name="tba_match_key"
              value={form.tba_match_key}
              onChange={handleChange}
              placeholder="e.g. 2025casd_qm1 (auto-fills alliances)"
            />
          </div>
        </div>

        <div className="grid-2">
          <div>
            <label style={{ display: 'block', fontSize: 12, color: 'var(--text-muted)', marginBottom: 4 }}>
              Red Alliance Teams
            </label>
            <input
              name="red_alliance"
              value={form.red_alliance}
              onChange={handleChange}
              placeholder="e.g. 254, 1678, 3310"
            />
          </div>
          <div>
            <label style={{ display: 'block', fontSize: 12, color: 'var(--text-muted)', marginBottom: 4 }}>
              Blue Alliance Teams
            </label>
            <input
              name="blue_alliance"
              value={form.blue_alliance}
              onChange={handleChange}
              placeholder="e.g. 2056, 1114, 2767"
            />
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <input
            type="checkbox"
            id="use_mock"
            name="use_mock"
            checked={form.use_mock}
            onChange={handleChange}
            style={{ width: 'auto' }}
          />
          <label htmlFor="use_mock" style={{ fontSize: 13, cursor: 'pointer' }}>
            Use mock stream (for testing without a live Twitch feed)
          </label>
        </div>

        {status === 'running' && (
          <div style={{
            background: 'rgba(34,197,94,.1)', border: '1px solid rgba(34,197,94,.3)',
            borderRadius: 8, padding: '10px 14px', display: 'flex', alignItems: 'center', gap: 8,
          }}>
            <div className="pulse-dot" />
            <span style={{ fontSize: 13, color: 'var(--green)' }}>{message}</span>
          </div>
        )}
        {status === 'error' && (
          <div style={{
            background: 'rgba(239,68,68,.1)', border: '1px solid rgba(239,68,68,.3)',
            borderRadius: 8, padding: '10px 14px', display: 'flex', alignItems: 'center', gap: 8,
          }}>
            <AlertCircle size={16} color="var(--red)" />
            <span style={{ fontSize: 13, color: 'var(--red)' }}>{message}</span>
          </div>
        )}
        {status === 'stopped' && (
          <div style={{
            background: 'rgba(148,163,184,.1)', border: '1px solid var(--border)',
            borderRadius: 8, padding: '10px 14px', display: 'flex', alignItems: 'center', gap: 8,
          }}>
            <CheckCircle2 size={16} color="var(--text-muted)" />
            <span style={{ fontSize: 13, color: 'var(--text-muted)' }}>{message}</span>
          </div>
        )}

        <div style={{ display: 'flex', gap: 10, marginTop: 4 }}>
          <button
            className="btn-primary"
            onClick={handleStart}
            disabled={loading || status === 'running'}
            style={{ flex: 1 }}
          >
            <Radio size={14} style={{ marginRight: 6, display: 'inline' }} />
            {loading && status !== 'running' ? 'Starting…' : 'Start Scouting'}
          </button>
          <button
            className="btn-danger"
            onClick={handleStop}
            disabled={loading || status !== 'running'}
            style={{ flex: 1 }}
          >
            <StopCircle size={14} style={{ marginRight: 6, display: 'inline' }} />
            Stop Scouting
          </button>
        </div>
      </div>

      <div className="card" style={{ marginTop: '1.5rem' }}>
        <h3 style={{ fontWeight: 700, marginBottom: '0.75rem' }}>How It Works</h3>
        <ol style={{ paddingLeft: '1.2rem', color: 'var(--text-muted)', fontSize: 13, lineHeight: 1.8 }}>
          <li>Enter the Twitch channel broadcasting the FRC event (e.g. <code>firstinspires</code>)</li>
          <li>Optionally enter the alliance teams so the AI can identify robots more accurately</li>
          <li>Click <strong>Start Scouting</strong> — the AI will capture a frame every {5} seconds</li>
          <li>Claude Vision analyzes each frame to detect robots, actions, and scores</li>
          <li>Results appear in the <strong>Live Feed</strong> panel and update the <strong>Rankings</strong></li>
          <li>Use the <strong>Mock stream</strong> option for testing without a live Twitch feed</li>
        </ol>
      </div>
    </div>
  )
}
