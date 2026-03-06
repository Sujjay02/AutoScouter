import { useState } from 'react'
import { Radio, StopCircle, AlertCircle, CheckCircle2, Tv, Youtube, Link, Search } from 'lucide-react'

const STREAM_TYPES = [
  { value: 'twitch', label: 'Twitch', icon: Tv, placeholder: 'e.g. firstinspires' },
  { value: 'youtube', label: 'YouTube', icon: Youtube, placeholder: 'e.g. dQw4w9WgXcQ (video/live ID)' },
  { value: 'direct', label: 'Direct URL', icon: Link, placeholder: 'https://…/stream.m3u8' },
]

export default function Scout() {
  const [form, setForm] = useState({
    match_key: '',
    stream_type: 'twitch',
    stream_source: '',
    event_key: '',
    tba_match_key: '',
    red_alliance: '',
    blue_alliance: '',
    use_mock: false,
  })
  const [status, setStatus] = useState(null)
  const [message, setMessage] = useState('')
  const [loading, setLoading] = useState(false)
  const [tbaLoading, setTbaLoading] = useState(false)

  const handleChange = e => {
    const { name, value, type, checked } = e.target
    setForm(f => ({ ...f, [name]: type === 'checkbox' ? checked : value }))
  }

  const parseTeams = str =>
    str.split(/[,\s]+/).map(s => parseInt(s.trim())).filter(n => !isNaN(n) && n > 0)

  const autoFillFromTBA = async () => {
    const key = form.tba_match_key || form.match_key
    if (!key) return
    setTbaLoading(true)
    try {
      const eventKey = key.split('_')[0]
      const r = await fetch(`/api/tba/events/${eventKey}/matches`)
      if (!r.ok) return
      const data = await r.json()
      const match = data.matches?.find(m => m.key === key)
      if (match) {
        setForm(f => ({
          ...f,
          red_alliance: match.red_alliance.join(', '),
          blue_alliance: match.blue_alliance.join(', '),
          ...((!f.stream_source && data.primary_stream) ? {
            stream_type: data.primary_stream.type === 'youtube' ? 'youtube' : 'twitch',
            stream_source: data.primary_stream.channel,
          } : {}),
        }))
      }
    } catch (_) {}
    finally { setTbaLoading(false) }
  }

  const handleStart = async () => {
    if (!form.match_key) { setMessage('Match key is required.'); setStatus('error'); return }
    if (!form.stream_source && !form.use_mock) {
      setMessage('Enter a stream source or enable mock mode.')
      setStatus('error')
      return
    }
    setLoading(true)
    setMessage('')
    try {
      const body = {
        match_key: form.match_key,
        stream_type: form.use_mock ? 'twitch' : form.stream_type,
        event_key: form.event_key || null,
        tba_match_key: form.tba_match_key || null,
        red_alliance: parseTeams(form.red_alliance),
        blue_alliance: parseTeams(form.blue_alliance),
        use_mock: form.use_mock,
      }
      if (!form.use_mock) {
        if (form.stream_type === 'twitch') {
          body.twitch_channel = form.stream_source.replace('https://www.twitch.tv/', '').replace('@', '').trim()
        } else if (form.stream_type === 'youtube') {
          const ytMatch = form.stream_source.match(/(?:v=|youtu\.be\/)([A-Za-z0-9_-]{11})/)
          body.youtube_id = ytMatch ? ytMatch[1] : form.stream_source.trim()
        } else {
          body.stream_url = form.stream_source.trim()
        }
      }

      const r = await fetch('/api/matches/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      const data = await r.json()
      if (!r.ok) throw new Error(data.detail || 'Failed to start')
      setStatus('running')
      setMessage(`Scouting ${data.match_key} via ${data.stream_type}: ${data.channel}`)
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

  const currentStreamType = STREAM_TYPES.find(t => t.value === form.stream_type) ?? STREAM_TYPES[0]

  return (
    <div style={{ maxWidth: 700 }}>
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
            <input name="match_key" value={form.match_key} onChange={handleChange} placeholder="e.g. 2026casd_qm1" />
          </div>
          <div>
            <label style={{ display: 'block', fontSize: 12, color: 'var(--text-muted)', marginBottom: 4 }}>
              TBA Match Key
              <span style={{ marginLeft: 6, fontSize: 10 }}>(auto-fills alliances + stream)</span>
            </label>
            <div style={{ display: 'flex', gap: 6 }}>
              <input
                name="tba_match_key" value={form.tba_match_key} onChange={handleChange}
                placeholder="e.g. 2026casd_qm1" style={{ flex: 1 }}
              />
              <button
                onClick={autoFillFromTBA}
                disabled={tbaLoading || (!form.tba_match_key && !form.match_key)}
                style={{
                  padding: '6px 10px', borderRadius: 6, border: '1px solid var(--border)',
                  background: 'var(--surface)', cursor: 'pointer', flexShrink: 0,
                  display: 'flex', alignItems: 'center', gap: 4, fontSize: 12, color: 'var(--text-muted)',
                }}
                title="Auto-fill alliances and stream from TBA"
              >
                <Search size={12} />{tbaLoading ? '…' : 'Fill'}
              </button>
            </div>
          </div>
        </div>

        <div>
          <label style={{ display: 'block', fontSize: 12, color: 'var(--text-muted)', marginBottom: 6 }}>
            Stream Source
          </label>
          <div style={{
            display: 'flex', gap: 0, marginBottom: 8,
            background: 'rgba(100,116,139,.1)', borderRadius: 8, padding: 3, width: 'fit-content',
          }}>
            {STREAM_TYPES.map(({ value, label, icon: Icon }) => (
              <button
                key={value}
                onClick={() => setForm(f => ({ ...f, stream_type: value }))}
                style={{
                  display: 'flex', alignItems: 'center', gap: 5, padding: '5px 12px',
                  borderRadius: 6, fontSize: 12, fontWeight: 700,
                  background: form.stream_type === value ? 'var(--accent)' : 'transparent',
                  color: form.stream_type === value ? '#fff' : 'var(--text-muted)',
                  border: 'none', cursor: 'pointer', transition: 'all .15s',
                }}
              >
                <Icon size={12} />{label}
              </button>
            ))}
          </div>
          <input
            name="stream_source" value={form.stream_source} onChange={handleChange}
            placeholder={currentStreamType.placeholder}
            disabled={form.use_mock} style={{ opacity: form.use_mock ? 0.5 : 1 }}
          />
        </div>

        <div className="grid-2">
          <div>
            <label style={{ display: 'block', fontSize: 12, color: 'var(--text-muted)', marginBottom: 4 }}>Red Alliance</label>
            <input name="red_alliance" value={form.red_alliance} onChange={handleChange} placeholder="254, 1678, 3310" />
          </div>
          <div>
            <label style={{ display: 'block', fontSize: 12, color: 'var(--text-muted)', marginBottom: 4 }}>Blue Alliance</label>
            <input name="blue_alliance" value={form.blue_alliance} onChange={handleChange} placeholder="2056, 1114, 2767" />
          </div>
        </div>

        <div>
          <label style={{ display: 'block', fontSize: 12, color: 'var(--text-muted)', marginBottom: 4 }}>
            Event Key <span style={{ fontSize: 10 }}>(optional)</span>
          </label>
          <input name="event_key" value={form.event_key} onChange={handleChange} placeholder="e.g. 2026casd" style={{ maxWidth: 240 }} />
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <input type="checkbox" id="use_mock" name="use_mock" checked={form.use_mock} onChange={handleChange} style={{ width: 'auto' }} />
          <label htmlFor="use_mock" style={{ fontSize: 13, cursor: 'pointer' }}>
            Use mock stream <span style={{ color: 'var(--text-muted)', fontSize: 11 }}>(test without a live feed)</span>
          </label>
        </div>

        {status === 'running' && (
          <div style={{ background: 'rgba(34,197,94,.1)', border: '1px solid rgba(34,197,94,.3)', borderRadius: 8, padding: '10px 14px', display: 'flex', alignItems: 'center', gap: 8 }}>
            <div className="pulse-dot" />
            <span style={{ fontSize: 13, color: 'var(--green)' }}>{message}</span>
          </div>
        )}
        {status === 'error' && (
          <div style={{ background: 'rgba(239,68,68,.1)', border: '1px solid rgba(239,68,68,.3)', borderRadius: 8, padding: '10px 14px', display: 'flex', alignItems: 'center', gap: 8 }}>
            <AlertCircle size={16} color="var(--red)" />
            <span style={{ fontSize: 13, color: 'var(--red)' }}>{message}</span>
          </div>
        )}
        {status === 'stopped' && (
          <div style={{ background: 'rgba(148,163,184,.1)', border: '1px solid var(--border)', borderRadius: 8, padding: '10px 14px', display: 'flex', alignItems: 'center', gap: 8 }}>
            <CheckCircle2 size={16} color="var(--text-muted)" />
            <span style={{ fontSize: 13, color: 'var(--text-muted)' }}>{message}</span>
          </div>
        )}

        <div style={{ display: 'flex', gap: 10, marginTop: 4 }}>
          <button className="btn-primary" onClick={handleStart} disabled={loading || status === 'running'} style={{ flex: 1 }}>
            <Radio size={14} style={{ marginRight: 6, display: 'inline' }} />
            {loading && status !== 'running' ? 'Starting…' : 'Start Scouting'}
          </button>
          <button className="btn-danger" onClick={handleStop} disabled={loading || status !== 'running'} style={{ flex: 1 }}>
            <StopCircle size={14} style={{ marginRight: 6, display: 'inline' }} />
            Stop Scouting
          </button>
        </div>
      </div>

      <div className="card" style={{ marginTop: '1.5rem' }}>
        <h3 style={{ fontWeight: 700, marginBottom: '0.75rem' }}>How It Works</h3>
        <ol style={{ paddingLeft: '1.2rem', color: 'var(--text-muted)', fontSize: 13, lineHeight: 1.9 }}>
          <li>Browse <strong>TBA Events</strong> to pick an event and start scouting in one click</li>
          <li>Or fill in a match key and choose a <strong>Twitch</strong>, <strong>YouTube</strong>, or direct stream URL</li>
          <li>Enter a TBA match key and click <strong>Fill</strong> to auto-populate alliances and stream</li>
          <li>The AI captures a frame every 5 s and analyzes robot actions, FUEL cycles, climbs, and scores</li>
          <li>Results stream into the <strong>Live Feed</strong> panel and update <strong>Rankings</strong> in real time</li>
        </ol>
      </div>
    </div>
  )
}
