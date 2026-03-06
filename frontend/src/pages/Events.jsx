import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Globe, ChevronRight, ChevronDown, Radio, Tv, Youtube,
  Search, Calendar, MapPin, AlertCircle, Loader2, Play,
} from 'lucide-react'

const CURRENT_YEAR = new Date().getFullYear()

// ─── Helpers ─────────────────────────────────────────────────────────────────

function StreamBadge({ stream }) {
  if (!stream) return null
  const isYT = stream.type === 'youtube'
  const isTwitch = stream.type === 'twitch'
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 4,
      fontSize: 11, padding: '2px 8px', borderRadius: 99,
      background: isTwitch ? 'rgba(145,71,255,.15)' : isYT ? 'rgba(255,0,0,.12)' : 'rgba(100,116,139,.15)',
      color: isTwitch ? '#a855f7' : isYT ? '#ef4444' : 'var(--text-muted)',
      border: `1px solid ${isTwitch ? 'rgba(145,71,255,.3)' : isYT ? 'rgba(255,0,0,.3)' : 'var(--border)'}`,
      fontWeight: 600,
    }}>
      {isTwitch ? <Tv size={10} /> : isYT ? <Youtube size={10} /> : <Globe size={10} />}
      {stream.label}
    </span>
  )
}

function AllianceChip({ teams, color }) {
  const bg = color === 'red' ? 'rgba(239,68,68,.1)' : 'rgba(59,130,246,.1)'
  const border = color === 'red' ? 'rgba(239,68,68,.3)' : 'rgba(59,130,246,.3)'
  const text = color === 'red' ? '#f87171' : '#60a5fa'
  return (
    <span style={{
      display: 'inline-flex', gap: 4, fontSize: 11,
      background: bg, border: `1px solid ${border}`,
      color: text, borderRadius: 6, padding: '2px 8px', fontWeight: 700,
    }}>
      {teams.map(t => t).join(' · ')}
    </span>
  )
}

// ─── Match row ────────────────────────────────────────────────────────────────

function MatchRow({ match, streams, onScout, scouting }) {
  const hasScore = match.score_red != null && match.score_blue != null && match.score_red >= 0
  const isScouted = scouting === match.key

  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 12,
      padding: '10px 14px',
      borderBottom: '1px solid var(--border)',
      background: isScouted ? 'rgba(34,197,94,.05)' : 'transparent',
      transition: 'background .15s',
    }}>
      {/* Match label */}
      <span style={{ width: 72, fontWeight: 700, fontSize: 13, flexShrink: 0 }}>
        {match.label}
      </span>

      {/* Alliances */}
      <div style={{ display: 'flex', gap: 6, flex: 1, flexWrap: 'wrap' }}>
        <AllianceChip teams={match.red_alliance} color="red" />
        <AllianceChip teams={match.blue_alliance} color="blue" />
      </div>

      {/* Score or status */}
      {hasScore ? (
        <span style={{ fontSize: 12, color: 'var(--text-muted)', flexShrink: 0 }}>
          <span style={{ color: '#f87171', fontWeight: 700 }}>{match.score_red}</span>
          {' – '}
          <span style={{ color: '#60a5fa', fontWeight: 700 }}>{match.score_blue}</span>
        </span>
      ) : (
        <span style={{ fontSize: 11, color: 'var(--text-muted)', flexShrink: 0 }}>
          upcoming
        </span>
      )}

      {/* Scout buttons */}
      <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
        {streams.map((s, i) => (
          <button
            key={i}
            onClick={() => onScout(match, s)}
            disabled={isScouted}
            style={{
              display: 'flex', alignItems: 'center', gap: 4,
              padding: '4px 10px', borderRadius: 6, fontSize: 11, fontWeight: 700,
              cursor: isScouted ? 'not-allowed' : 'pointer',
              background: isScouted ? 'rgba(34,197,94,.1)' : 'var(--accent)',
              color: isScouted ? 'var(--green)' : '#fff',
              border: 'none', transition: 'opacity .15s',
            }}
            title={`Scout via ${s.label}`}
          >
            {isScouted
              ? <><Radio size={10} /> Live</>
              : <><Play size={10} /> {streams.length > 1 ? s.type.slice(0, 2).toUpperCase() : 'Scout'}</>
            }
          </button>
        ))}
      </div>
    </div>
  )
}

// ─── Event card ───────────────────────────────────────────────────────────────

function EventCard({ event, onScoutMatch }) {
  const [expanded, setExpanded] = useState(false)
  const [matches, setMatches] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [scoutingMatch, setScoutingMatch] = useState(null)
  const [scoutResult, setScoutResult] = useState(null)

  const loadMatches = async () => {
    if (matches) { setExpanded(e => !e); return }
    setExpanded(true)
    setLoading(true)
    setError(null)
    try {
      const r = await fetch(`/api/tba/events/${event.key}/matches`)
      if (!r.ok) throw new Error((await r.json()).detail || 'Failed to load matches')
      setMatches(await r.json())
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const handleScout = async (match, stream) => {
    setScoutingMatch(match.key)
    setScoutResult(null)
    try {
      const body = {
        match_key: match.key,
        event_key: event.key,
        tba_match_key: match.key,
        red_alliance: match.red_alliance,
        blue_alliance: match.blue_alliance,
        stream_type: stream.type,
      }
      if (stream.type === 'twitch') body.twitch_channel = stream.channel
      else if (stream.type === 'youtube') body.youtube_id = stream.channel
      else body.stream_url = stream.url

      const r = await fetch('/api/matches/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      const data = await r.json()
      if (!r.ok) throw new Error(data.detail || 'Failed to start')
      setScoutResult({ ok: true, msg: `Scouting ${match.label} via ${stream.label}` })
      if (onScoutMatch) onScoutMatch(match, stream)
    } catch (e) {
      setScoutResult({ ok: false, msg: e.message })
      setScoutingMatch(null)
    }
  }

  return (
    <div className="card" style={{ padding: 0, overflow: 'hidden', marginBottom: '0.75rem' }}>
      {/* Header row */}
      <div
        onClick={loadMatches}
        style={{
          display: 'flex', alignItems: 'center', gap: 12,
          padding: '12px 16px', cursor: 'pointer',
          borderBottom: expanded ? '1px solid var(--border)' : 'none',
        }}
      >
        {expanded
          ? <ChevronDown size={16} color="var(--text-muted)" />
          : <ChevronRight size={16} color="var(--text-muted)" />
        }

        <div style={{ flex: 1 }}>
          <div style={{ fontWeight: 700, fontSize: 14 }}>{event.name}</div>
          <div style={{
            display: 'flex', gap: 12, marginTop: 2,
            fontSize: 11, color: 'var(--text-muted)',
          }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: 3 }}>
              <MapPin size={10} />
              {[event.city, event.state_prov, event.country].filter(Boolean).join(', ')}
            </span>
            <span style={{ display: 'flex', alignItems: 'center', gap: 3 }}>
              <Calendar size={10} />
              {event.start_date} – {event.end_date}
            </span>
          </div>
        </div>

        <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
          {event.webcasts?.map((s, i) => <StreamBadge key={i} stream={s} />)}
          {event.webcasts?.length === 0 && (
            <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>no stream</span>
          )}
        </div>

        <span style={{
          fontSize: 10, padding: '2px 8px', borderRadius: 99,
          background: 'rgba(100,116,139,.15)', color: 'var(--text-muted)',
          fontWeight: 600,
        }}>
          {event.event_type_string}
        </span>
      </div>

      {/* Expanded match list */}
      {expanded && (
        <div>
          {loading && (
            <div style={{ padding: '20px', textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>
              <Loader2 size={16} style={{ display: 'inline', marginRight: 6 }} />
              Loading matches…
            </div>
          )}
          {error && (
            <div style={{ padding: '12px 16px', color: 'var(--red)', fontSize: 13, display: 'flex', gap: 6 }}>
              <AlertCircle size={14} /> {error}
            </div>
          )}
          {scoutResult && (
            <div style={{
              padding: '8px 16px', fontSize: 12,
              background: scoutResult.ok ? 'rgba(34,197,94,.08)' : 'rgba(239,68,68,.08)',
              color: scoutResult.ok ? 'var(--green)' : 'var(--red)',
              borderBottom: '1px solid var(--border)',
            }}>
              {scoutResult.ok ? '✓' : '✗'} {scoutResult.msg}
            </div>
          )}
          {matches && (
            <>
              {matches.matches.length === 0 ? (
                <div style={{ padding: '16px', color: 'var(--text-muted)', fontSize: 13 }}>
                  No matches found for this event yet.
                </div>
              ) : (
                <>
                  {/* Stream selector header */}
                  {matches.streams.length > 0 && (
                    <div style={{
                      padding: '8px 16px', fontSize: 11, color: 'var(--text-muted)',
                      background: 'rgba(100,116,139,.07)', borderBottom: '1px solid var(--border)',
                      display: 'flex', alignItems: 'center', gap: 8,
                    }}>
                      <Radio size={11} />
                      Streams: {matches.streams.map((s, i) => (
                        <StreamBadge key={i} stream={s} />
                      ))}
                    </div>
                  )}
                  {matches.matches.map(m => (
                    <MatchRow
                      key={m.key}
                      match={m}
                      streams={matches.streams.length > 0 ? matches.streams : [{ type: 'mock', label: 'Mock', channel: 'mock' }]}
                      onScout={handleScout}
                      scouting={scoutingMatch}
                    />
                  ))}
                </>
              )}
            </>
          )}
        </div>
      )}
    </div>
  )
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function Events() {
  const [year, setYear] = useState(CURRENT_YEAR)
  const [events, setEvents] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [search, setSearch] = useState('')

  const loadEvents = useCallback(async (y) => {
    setLoading(true)
    setError(null)
    setEvents(null)
    try {
      const r = await fetch(`/api/tba/events?year=${y}`)
      const data = await r.json()
      if (!r.ok) throw new Error(data.detail || 'Failed to load events')
      setEvents(data)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { loadEvents(year) }, [year, loadEvents])

  const filtered = events?.events?.filter(e => {
    if (!search) return true
    const q = search.toLowerCase()
    return (
      e.name?.toLowerCase().includes(q) ||
      e.key?.toLowerCase().includes(q) ||
      e.city?.toLowerCase().includes(q) ||
      e.state_prov?.toLowerCase().includes(q)
    )
  }) ?? []

  const years = Array.from({ length: 5 }, (_, i) => CURRENT_YEAR - i)

  return (
    <div style={{ maxWidth: 900 }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: '1.5rem' }}>
        <Globe size={22} color="var(--accent)" />
        <h1 style={{ fontSize: 22, fontWeight: 800 }}>TBA Events</h1>
        {events && (
          <span style={{
            fontSize: 12, color: 'var(--text-muted)', marginLeft: 4,
            background: 'rgba(100,116,139,.15)', borderRadius: 99, padding: '2px 10px',
          }}>
            {filtered.length} events
          </span>
        )}
      </div>

      {/* Controls */}
      <div style={{ display: 'flex', gap: 12, marginBottom: '1.25rem', flexWrap: 'wrap' }}>
        {/* Year selector */}
        <div style={{ display: 'flex', gap: 0, background: 'var(--surface)', borderRadius: 8, border: '1px solid var(--border)', overflow: 'hidden' }}>
          {years.map(y => (
            <button
              key={y}
              onClick={() => setYear(y)}
              style={{
                padding: '6px 14px', fontSize: 13, fontWeight: 700,
                background: year === y ? 'var(--accent)' : 'transparent',
                color: year === y ? '#fff' : 'var(--text-muted)',
                border: 'none', cursor: 'pointer', transition: 'all .15s',
              }}
            >
              {y}
            </button>
          ))}
        </div>

        {/* Search */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flex: 1, minWidth: 200 }}>
          <Search size={14} color="var(--text-muted)" />
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search events by name, city, or key…"
            style={{ flex: 1, fontSize: 13 }}
          />
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="card" style={{
          display: 'flex', gap: 10, alignItems: 'center',
          color: 'var(--red)', padding: '14px 18px', marginBottom: '1rem',
          background: 'rgba(239,68,68,.07)', border: '1px solid rgba(239,68,68,.25)',
        }}>
          <AlertCircle size={16} />
          <div>
            <div style={{ fontWeight: 700, fontSize: 13 }}>{error}</div>
            {error.includes('TBA_API_KEY') && (
              <div style={{ fontSize: 12, marginTop: 4, color: 'var(--text-muted)' }}>
                Get a free key at{' '}
                <a href="https://www.thebluealliance.com/account" target="_blank" rel="noreferrer"
                   style={{ color: 'var(--accent)' }}>
                  thebluealliance.com/account
                </a>
                {' '}and add <code>TBA_API_KEY=your_key</code> to your <code>.env</code> file.
              </div>
            )}
          </div>
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)', fontSize: 14 }}>
          <Loader2 size={24} style={{ display: 'inline', marginRight: 8 }} />
          Loading {year} events from The Blue Alliance…
        </div>
      )}

      {/* Event list */}
      {!loading && !error && events && (
        <>
          {filtered.length === 0 ? (
            <div className="card" style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
              No events found{search ? ` matching "${search}"` : ''}.
            </div>
          ) : (
            filtered.map(event => (
              <EventCard key={event.key} event={event} />
            ))
          )}
        </>
      )}

      {/* Help */}
      {!loading && !error && !events && (
        <div className="card" style={{ padding: '24px' }}>
          <h3 style={{ fontWeight: 700, marginBottom: '0.75rem' }}>Getting Started with TBA Events</h3>
          <ol style={{ paddingLeft: '1.2rem', color: 'var(--text-muted)', fontSize: 13, lineHeight: 1.9 }}>
            <li>Add your TBA API key to <code>.env</code>: <code>TBA_API_KEY=your_key</code></li>
            <li>Get a free key at <a href="https://www.thebluealliance.com/account" target="_blank" rel="noreferrer" style={{ color: 'var(--accent)' }}>thebluealliance.com/account</a></li>
            <li>Select a year and browse events — click any event to expand its match schedule</li>
            <li>Click <strong>Scout</strong> on any match to auto-fill alliances and start scouting from the event's live stream</li>
            <li>Streams are detected automatically from TBA's webcast data (Twitch or YouTube)</li>
          </ol>
        </div>
      )}
    </div>
  )
}
