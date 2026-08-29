import { useState, useEffect, useRef } from 'react'
import './App.css'

// ---- Types ----
interface Train {
  train_id: string
  name: string
  priority_class: string
  current_segment: string | null
  route: string[]
  current_status: string
  current_delay_minutes: number
}

interface AgentDecision {
  train_id: string
  round_number: number
  action: string
  proposed_change: Record<string, unknown> | null
  rationale: string
}

interface RoundRecord {
  round_number: number
  decisions: AgentDecision[]
  coordinator_summary: string
}

interface NegotiationSession {
  session_id: string
  disruption_event_id: string
  participating_trains: string[]
  rounds: RoundRecord[]
  terminal_state: string | null
  started_at: string
  ended_at: string | null
}

interface NetworkState {
  timestamp: string
  trains: Train[]
  stations: Array<{ id: string; name: string; capacity: number }>
  segments: Array<{ id: string; source_id: string; target_id: string; length_km: number }>
  active_disruptions: Array<{ event_id: string; affected_station_or_segment: string; delay_minutes: number; cause: string }>
}

const API = 'http://localhost:8000'

const SCENARIOS = [
  { key: 'scenario_1_two_train_conflict', label: 'Scenario 1: Two-Train Platform Conflict', color: '#e67e22' },
  { key: 'scenario_2_three_hop_cascade', label: 'Scenario 2: Three-Hop Cascade Delay', color: '#e74c3c' },
  { key: 'scenario_3_deadlock', label: 'Scenario 3: Deadlock (No Resolution)', color: '#8e44ad' },
  { key: 'scenario_4_agent_dropout', label: 'Scenario 4: Agent Dropout', color: '#2980b9' },
]

// Station positions for SVG map (relative to 600x350 viewBox)
const STATION_POSITIONS: Record<string, { x: number; y: number; label: string }> = {
  NDLS: { x: 80,  y: 80,  label: 'New Delhi' },
  NGP:  { x: 300, y: 200, label: 'Nagpur' },
  MMCT: { x: 160, y: 290, label: 'Mumbai' },
  HWH:  { x: 520, y: 80,  label: 'Howrah' },
  BZA:  { x: 430, y: 270, label: 'Vijayawada' },
  MAS:  { x: 370, y: 320, label: 'Chennai' },
}

// Removed unused SEGMENT_COLORS

function getPriorityColor(priority: string) {
  if (priority === 'express') return '#e74c3c'
  if (priority === 'passenger') return '#3498db'
  return '#7f8c8d'
}

function getActionColor(action: string) {
  if (action === 'accept') return '#27ae60'
  if (action === 'counter_propose') return '#e67e22'
  if (action === 'reject') return '#e74c3c'
  if (action === 'escalate') return '#8e44ad'
  return '#95a5a6'
}

function getTerminalStateColor(state: string | null) {
  if (state === 'consensus_reached') return '#27ae60'
  if (state === 'escalated_unresolved') return '#e74c3c'
  if (state === 'max_rounds_exceeded') return '#e67e22'
  return '#95a5a6'
}

// ---- Network Map Component ----
function NetworkMap({ networkState, activeSessionTrains }: {
  networkState: NetworkState | null
  activeSessionTrains: string[]
}) {
  if (!networkState) {
    return (
      <div style={{ background: '#1a1a2e', borderRadius: 8, padding: 20, height: 320, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#888' }}>
        Loading network...
      </div>
    )
  }

  const trainsBySegment: Record<string, Train[]> = {}
  for (const train of networkState.trains) {
    const seg = train.current_segment
    if (seg) {
      trainsBySegment[seg] = trainsBySegment[seg] || []
      trainsBySegment[seg].push(train)
    }
  }

  const affectedSegments = new Set(
    networkState.active_disruptions.map(d => d.affected_station_or_segment)
  )

  return (
    <div style={{ background: '#1a1a2e', borderRadius: 8, padding: 12 }}>
      <svg viewBox="0 0 600 350" width="100%" style={{ maxHeight: 320 }}>
        {/* Segments */}
        {networkState.segments.map(seg => {
          const src = STATION_POSITIONS[seg.source_id]
          const tgt = STATION_POSITIONS[seg.target_id]
          if (!src || !tgt) return null
          const isAffected = affectedSegments.has(seg.id)
          return (
            <line
              key={seg.id}
              x1={src.x} y1={src.y}
              x2={tgt.x} y2={tgt.y}
              stroke={isAffected ? '#e74c3c' : '#334155'}
              strokeWidth={isAffected ? 3 : 2}
              strokeDasharray={isAffected ? '6,3' : undefined}
            />
          )
        })}

        {/* Stations */}
        {Object.entries(STATION_POSITIONS).map(([id, pos]) => {
          const isAffected = affectedSegments.has(id)
          return (
            <g key={id}>
              <circle
                cx={pos.x} cy={pos.y} r={14}
                fill={isAffected ? '#e74c3c' : '#1e3a5f'}
                stroke={isAffected ? '#ff6b6b' : '#3b82f6'}
                strokeWidth={2}
              />
              <text x={pos.x} y={pos.y + 4} textAnchor="middle" fontSize={9} fill="#e2e8f0" fontWeight="bold">
                {id}
              </text>
              <text x={pos.x} y={pos.y + 24} textAnchor="middle" fontSize={8} fill="#94a3b8">
                {pos.label}
              </text>
            </g>
          )
        })}

        {/* Trains */}
        {networkState.trains.map((train, i) => {
          const seg = networkState.segments.find(s => s.id === train.current_segment)
          if (!seg) return null
          const src = STATION_POSITIONS[seg.source_id]
          const tgt = STATION_POSITIONS[seg.target_id]
          if (!src || !tgt) return null
          // Position train midway along segment
          const mx = (src.x + tgt.x) / 2 + (i % 3) * 8 - 8
          const my = (src.y + tgt.y) / 2 + (i % 2) * 8 - 4
          const isActive = activeSessionTrains.includes(train.train_id)
          const color = getPriorityColor(train.priority_class)
          return (
            <g key={train.train_id}>
              <circle
                cx={mx} cy={my} r={7}
                fill={color}
                stroke={isActive ? '#fff' : 'transparent'}
                strokeWidth={isActive ? 2 : 0}
                opacity={0.9}
              />
              <text x={mx} y={my + 3} textAnchor="middle" fontSize={6} fill="#fff" fontWeight="bold">
                🚆
              </text>
              {train.current_delay_minutes > 0 && (
                <text x={mx + 9} y={my - 5} fontSize={8} fill="#fbbf24">
                  +{train.current_delay_minutes}m
                </text>
              )}
            </g>
          )
        })}
      </svg>

      {/* Legend */}
      <div style={{ display: 'flex', gap: 16, marginTop: 8, fontSize: 11, color: '#94a3b8' }}>
        <span>● <span style={{ color: '#e74c3c' }}>Express</span></span>
        <span>● <span style={{ color: '#3498db' }}>Passenger</span></span>
        <span>● <span style={{ color: '#7f8c8d' }}>Freight</span></span>
        <span style={{ marginLeft: 'auto' }}>🔴 Disrupted segment</span>
      </div>
    </div>
  )
}

// ---- Negotiation Transcript Component ----
function NegotiationTranscript({ session }: { session: NegotiationSession | null }) {
  const bottomRef = useRef<HTMLDivElement>(null)
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [session?.rounds.length])

  if (!session) {
    return (
      <div style={{ color: '#64748b', padding: 20, textAlign: 'center' }}>
        No active session. Inject a scenario to begin.
      </div>
    )
  }

  const termColor = getTerminalStateColor(session.terminal_state)

  return (
    <div style={{ fontFamily: 'monospace', fontSize: 13 }}>
      <div style={{ marginBottom: 12, padding: '8px 12px', background: '#0f172a', borderRadius: 6, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ color: '#94a3b8' }}>Session: <code style={{ color: '#60a5fa' }}>{session.session_id.slice(0, 8)}...</code></span>
        <span style={{ color: '#94a3b8' }}>Trains: {session.participating_trains.join(', ')}</span>
        {session.terminal_state && (
          <span style={{
            background: termColor + '22',
            color: termColor,
            padding: '2px 8px',
            borderRadius: 4,
            border: `1px solid ${termColor}44`,
            fontFamily: 'sans-serif',
            fontWeight: 600,
            fontSize: 12,
          }}>
            {session.terminal_state.replace(/_/g, ' ').toUpperCase()}
          </span>
        )}
      </div>

      {session.rounds.map(round => (
        <div key={round.round_number} style={{ marginBottom: 16 }}>
          <div style={{ color: '#475569', fontSize: 11, marginBottom: 6, textTransform: 'uppercase', letterSpacing: 1 }}>
            ── Round {round.round_number} ──
          </div>
          {round.decisions.map((d, i) => (
            <div key={i} style={{
              background: '#0f172a',
              border: `1px solid ${getActionColor(d.action)}44`,
              borderLeft: `3px solid ${getActionColor(d.action)}`,
              borderRadius: 6,
              padding: '8px 12px',
              marginBottom: 6,
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                <span style={{ color: getPriorityColor('express'), fontWeight: 600 }}>{d.train_id}</span>
                <span style={{
                  color: getActionColor(d.action),
                  fontSize: 11,
                  textTransform: 'uppercase',
                  fontWeight: 700,
                  letterSpacing: 1,
                }}>
                  {d.action.replace(/_/g, ' ')}
                </span>
              </div>
              <div style={{ color: '#cbd5e1', lineHeight: 1.5 }}>{d.rationale}</div>
              {d.proposed_change && (
                <div style={{ marginTop: 4, color: '#64748b', fontSize: 11 }}>
                  Proposal: {JSON.stringify(d.proposed_change)}
                </div>
              )}
            </div>
          ))}
          {round.coordinator_summary && (
            <div style={{ color: '#64748b', fontSize: 11, fontStyle: 'italic', marginTop: 4, paddingLeft: 4 }}>
              📋 {round.coordinator_summary}
            </div>
          )}
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  )
}

// ---- Advisory Summary Component ----
function AdvisorySummary({ session }: { session: NegotiationSession | null }) {
  if (!session || !session.terminal_state) return null

  const state = session.terminal_state
  const rounds = session.rounds.length
  const trains = session.participating_trains

  const summaries: Record<string, { icon: string; headline: string; color: string }> = {
    consensus_reached: {
      icon: '✅',
      headline: 'Agents reached consensus',
      color: '#27ae60',
    },
    escalated_unresolved: {
      icon: '⚠️',
      headline: 'No resolution — human dispatcher required',
      color: '#e74c3c',
    },
    max_rounds_exceeded: {
      icon: '⏱️',
      headline: `Max rounds (${rounds}) exceeded — applying priority fallback`,
      color: '#e67e22',
    },
  }

  const s = summaries[state] || { icon: '🔄', headline: state, color: '#94a3b8' }

  return (
    <div style={{
      background: s.color + '11',
      border: `1px solid ${s.color}44`,
      borderRadius: 8,
      padding: 16,
      marginBottom: 16,
    }}>
      <div style={{ fontSize: 18, fontWeight: 700, color: s.color, marginBottom: 8 }}>
        {s.icon} {s.headline}
      </div>
      <div style={{ color: '#94a3b8', fontSize: 13, lineHeight: 1.6 }}>
        <strong>Session:</strong> {session.session_id.slice(0, 12)}... &nbsp;|
        &nbsp;<strong>Trains:</strong> {trains.join(', ')} &nbsp;|
        &nbsp;<strong>Rounds:</strong> {rounds} &nbsp;|
        &nbsp;<strong>Decisions:</strong> {session.rounds.reduce((a, r) => a + r.decisions.length, 0)}
      </div>
      {state === 'escalated_unresolved' && (
        <div style={{ marginTop: 8, color: '#e74c3c', fontSize: 12 }}>
          Recommendation: Dispatcher should manually assign slot priority based on passenger load and operational urgency.
        </div>
      )}
      {state === 'consensus_reached' && (
        <div style={{ marginTop: 8, color: '#27ae60', fontSize: 12 }}>
          Schedule adjustments have been logged and are advisory only. Confirm with operations team before implementation.
        </div>
      )}
    </div>
  )
}

// ---- Scenario Injector Component ----
function ScenarioInjector({ onInject }: { onInject: (sessionId: string) => void }) {
  const [loading, setLoading] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function inject(scenarioKey: string) {
    setLoading(scenarioKey)
    setError(null)
    try {
      const res = await fetch(`${API}/scenarios/inject`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scenario: scenarioKey, seed: 42 }),
      })
      const data = await res.json()
      if (data.session_id) {
        onInject(data.session_id)
      } else {
        setError(JSON.stringify(data))
      }
    } catch (e: unknown) {
      setError(String(e))
    } finally {
      setLoading(null)
    }
  }

  return (
    <div style={{ marginBottom: 16 }}>
      <div style={{ fontSize: 12, color: '#64748b', marginBottom: 8, textTransform: 'uppercase', letterSpacing: 1 }}>Inject Scenario</div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
        {SCENARIOS.map(s => (
          <button
            key={s.key}
            onClick={() => inject(s.key)}
            disabled={loading !== null}
            style={{
              background: loading === s.key ? s.color : s.color + '22',
              color: loading === s.key ? '#fff' : s.color,
              border: `1px solid ${s.color}55`,
              borderRadius: 6,
              padding: '8px 10px',
              cursor: loading !== null ? 'wait' : 'pointer',
              fontSize: 12,
              fontWeight: 600,
              textAlign: 'left',
              transition: 'all 0.2s',
            }}
          >
            {loading === s.key ? '⏳ Running...' : s.label}
          </button>
        ))}
      </div>
      {error && <div style={{ color: '#e74c3c', fontSize: 12, marginTop: 8 }}>{error}</div>}
    </div>
  )
}

// ---- Data Mode Toggle ----
function DataModeToggle() {
  const [mode, setMode] = useState<string>('synthetic')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    fetch(`${API}/config/data-mode`).then(r => r.json()).then(d => setMode(d.mode)).catch(() => {})
  }, [])

  async function toggle() {
    const newMode = mode === 'synthetic' ? 'static' : 'synthetic'
    setLoading(true)
    try {
      await fetch(`${API}/config/data-mode`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode: newMode }),
      })
      setMode(newMode)
    } finally {
      setLoading(false)
    }
  }

  return (
    <button
      onClick={toggle}
      disabled={loading}
      style={{
        background: mode === 'synthetic' ? '#0f4c7544' : '#1a4731',
        color: mode === 'synthetic' ? '#60a5fa' : '#34d399',
        border: `1px solid ${mode === 'synthetic' ? '#60a5fa44' : '#34d39944'}`,
        borderRadius: 6,
        padding: '4px 12px',
        cursor: 'pointer',
        fontSize: 12,
        fontWeight: 600,
      }}
    >
      {loading ? '⏳' : `DATA: ${mode.toUpperCase()}`}
    </button>
  )
}

// ---- Main App ----
export default function App() {
  const [networkState, setNetworkState] = useState<NetworkState | null>(null)
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null)
  const [activeSession, setActiveSession] = useState<NegotiationSession | null>(null)
  const [sessions, setSessions] = useState<NegotiationSession[]>([])
  const [pollInterval, setPollInterval] = useState<ReturnType<typeof setInterval> | null>(null)

  // Fetch network state periodically
  useEffect(() => {
    const fetchNetwork = () => {
      fetch(`${API}/network/state`)
        .then(r => r.json())
        .then(setNetworkState)
        .catch(() => {})
    }
    fetchNetwork()
    const iv = setInterval(fetchNetwork, 3000)
    return () => clearInterval(iv)
  }, [])

  // Poll active session
  useEffect(() => {
    if (!activeSessionId) return
    if (pollInterval) clearInterval(pollInterval)
    const iv = setInterval(() => {
      fetch(`${API}/sessions/${activeSessionId}`)
        .then(r => r.json())
        .then(data => {
          setActiveSession(data)
          if (data.terminal_state) {
            clearInterval(iv)
          }
        })
        .catch(() => {})
    }, 1500)
    setPollInterval(iv)
    return () => clearInterval(iv)
  }, [activeSessionId])

  // Fetch session list
  useEffect(() => {
    const fetchSessions = () => {
      fetch(`${API}/sessions`).then(r => r.json()).then(setSessions).catch(() => {})
    }
    fetchSessions()
    const iv = setInterval(fetchSessions, 5000)
    return () => clearInterval(iv)
  }, [])

  function handleInject(sessionId: string) {
    setActiveSessionId(sessionId)
    setActiveSession(null)
  }

  const activeTrains = activeSession?.participating_trains || []

  return (
    <div style={{
      minHeight: '100vh',
      background: '#0d1117',
      color: '#e2e8f0',
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
    }}>
      {/* Header */}
      <header style={{
        background: '#161b22',
        borderBottom: '1px solid #21262d',
        padding: '12px 24px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span style={{ fontSize: 20 }}>🚆</span>
          <div>
            <div style={{ fontWeight: 700, fontSize: 18, letterSpacing: 0.5 }}>RailMesh</div>
            <div style={{ fontSize: 11, color: '#64748b' }}>Swarm-Based Railway Delay Cascade Simulator</div>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <DataModeToggle />
          <div style={{
            background: '#e67e2222',
            color: '#e67e22',
            border: '1px solid #e67e2244',
            borderRadius: 6,
            padding: '4px 12px',
            fontSize: 11,
            fontWeight: 600,
          }}>
            ⚠️ SIMULATION / ADVISORY LAYER
          </div>
        </div>
      </header>

      {/* Main Layout */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 420px', gap: 0, height: 'calc(100vh - 57px)' }}>
        {/* Left: Map + Advisory + Sessions */}
        <div style={{ padding: 20, overflowY: 'auto' }}>
          <NetworkMap networkState={networkState} activeSessionTrains={activeTrains} />

          <div style={{ marginTop: 16 }}>
            <AdvisorySummary session={activeSession} />
          </div>

          {/* Session list */}
          {sessions.length > 0 && (
            <div style={{ marginTop: 16 }}>
              <div style={{ fontSize: 12, color: '#64748b', marginBottom: 8, textTransform: 'uppercase', letterSpacing: 1 }}>Session History</div>
              {sessions.slice(-5).reverse().map(s => (
                <div
                  key={s.session_id}
                  onClick={() => {
                    setActiveSessionId(s.session_id)
                    fetch(`${API}/sessions/${s.session_id}`).then(r => r.json()).then(setActiveSession).catch(() => {})
                  }}
                  style={{
                    background: activeSessionId === s.session_id ? '#1e3a5f' : '#161b22',
                    border: `1px solid ${activeSessionId === s.session_id ? '#3b82f6' : '#21262d'}`,
                    borderRadius: 6,
                    padding: '8px 12px',
                    marginBottom: 6,
                    cursor: 'pointer',
                    display: 'flex',
                    justifyContent: 'space-between',
                    fontSize: 12,
                  }}
                >
                  <span style={{ color: '#60a5fa' }}>{s.session_id.slice(0, 8)}...</span>
                  <span style={{ color: '#64748b' }}>{s.participating_trains?.join(', ')}</span>
                  <span style={{ color: getTerminalStateColor(s.terminal_state) }}>
                    {s.terminal_state ? s.terminal_state.replace(/_/g, ' ') : 'running...'}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Right: Injector + Transcript */}
        <div style={{
          borderLeft: '1px solid #21262d',
          padding: 16,
          overflowY: 'auto',
          background: '#0d1117',
        }}>
          <ScenarioInjector onInject={handleInject} />

          <div style={{ borderTop: '1px solid #21262d', paddingTop: 12, marginTop: 4 }}>
            <div style={{ fontSize: 12, color: '#64748b', marginBottom: 8, textTransform: 'uppercase', letterSpacing: 1 }}>
              Negotiation Transcript
              {activeSession && !activeSession.terminal_state && (
                <span style={{ marginLeft: 8, color: '#60a5fa' }}>⏳ running</span>
              )}
            </div>
            <NegotiationTranscript session={activeSession} />
          </div>
        </div>
      </div>
    </div>
  )
}
