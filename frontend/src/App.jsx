import { useState, useEffect, useRef, useCallback } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { OrbitControls, Line } from '@react-three/drei'
import './App.css'

const API = '/api'

function blockColor(defArr, index, isLatest) {
  if (isLatest) return '#ff6b35'
  if (!defArr || defArr[index] === undefined) return '#4a9eff'
  return defArr[index] === 1 ? '#a78bfa' : '#4a9eff'
}

function Block({ position, index, defArr, isLatest }) {
  const meshRef = useRef()
  const color = blockColor(defArr, index, isLatest)

  useFrame((state) => {
    if (meshRef.current) {
      meshRef.current.scale.setScalar(
        isLatest ? 1 + Math.sin(state.clock.elapsedTime * 3) * 0.08 : 1
      )
    }
  })

  return (
    <mesh ref={meshRef} position={position}>
      <boxGeometry args={[0.85, 0.85, 0.85]} />
      <meshStandardMaterial color={color} roughness={0.3} metalness={0.2}
        transparent opacity={isLatest ? 1.0 : 0.85} />
    </mesh>
  )
}

function Snake3D({ positions, defArr }) {
  if (!positions || positions.length === 0) return null
  const cx = 1, cy = 1, cz = 1
  const pts = positions.map(p => [p.x - cx, p.y - cy, p.z - cz])
  return (
    <group>
      {pts.length > 1 && (
        <Line points={pts} color="#ffffff" lineWidth={2} opacity={0.4} transparent />
      )}
      {pts.map((pos, i) => (
        <Block key={i} position={pos} index={i} defArr={defArr} isLatest={i === pts.length - 1} />
      ))}
    </group>
  )
}

const SPEEDS = [0.25, 0.5, 1, 2, 4]
const SPEED_LABELS = ['¼×', '½×', '1×', '2×', '4×']

export default function App() {
  const [defArr, setDefArr] = useState([])
  const [positions, setPositions] = useState([])
  const [step, setStep] = useState(0)
  const [iterations, setIterations] = useState(0)
  const [solving, setSolving] = useState(false)
  const [solved, setSolved] = useState(false)
  const [error, setError] = useState(null)
  const [algo, setAlgo] = useState('dfs')

  // ── Recorded frames (solution replay) ──────────────────────
  const [frames, setFrames] = useState([])        // all solution steps recorded
  const [playerIdx, setPlayerIdx] = useState(0)   // current frame index
  const [playing, setPlaying] = useState(false)
  const [speedIdx, setSpeedIdx] = useState(2)     // default 1×
  const [playerActive, setPlayerActive] = useState(false)

  const esRef = useRef(null)
  const playTimerRef = useRef(null)
  const framesRef = useRef([])

  const ALGOS = [
    { id: 'dfs',        label: 'DFS',   title: 'Depth-First Search — goes deep, backtracks on dead ends' },
    { id: 'bfs',        label: 'BFS',   title: 'Breadth-First Search — explores level by level' },
    { id: 'dfs_pruned', label: 'DFS+',  title: 'DFS + bbox & flood-fill pruning — ~18x faster than DFS' },
    { id: 'astar',      label: 'A★',    title: 'A* — guided by depth + compactness heuristic (~280x faster)' },
    { id: 'warnsdorff', label: 'Wᵥ',   title: 'Warnsdorff — minimum-degree ordering + leaf pruning (fastest!)' },
  ]

  useEffect(() => {
    fetch(`${API}/def_arr`).then(r => r.json()).then(d => setDefArr(d.def_arr)).catch(() => {})
  }, [])

  // ── Playback engine ─────────────────────────────────────────
  const stopPlayback = useCallback(() => {
    clearInterval(playTimerRef.current)
    setPlaying(false)
  }, [])

  const goToFrame = useCallback((idx) => {
    const f = framesRef.current
    if (!f.length) return
    const clamped = Math.max(0, Math.min(f.length - 1, idx))
    setPlayerIdx(clamped)
    setPositions(f[clamped].positions)
    setStep(f[clamped].step)
  }, [])

  const startPlayback = useCallback(() => {
    const f = framesRef.current
    if (!f.length) return
    setPlaying(true)
    const baseMs = 300
    const intervalMs = baseMs / SPEEDS[speedIdx]

    playTimerRef.current = setInterval(() => {
      setPlayerIdx(prev => {
        const next = prev + 1
        if (next >= f.length) {
          clearInterval(playTimerRef.current)
          setPlaying(false)
          return prev
        }
        setPositions(f[next].positions)
        setStep(f[next].step)
        return next
      })
    }, intervalMs)
  }, [speedIdx])

  // Restart interval when speed changes while playing
  useEffect(() => {
    if (playing) {
      stopPlayback()
      startPlayback()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [speedIdx])

  // ── Solver ──────────────────────────────────────────────────
  function handleSolve() {
    if (esRef.current) esRef.current.close()
    stopPlayback()

    setSolving(true)
    setSolved(false)
    setError(null)
    setPositions([])
    setStep(0)
    setIterations(0)
    setFrames([])
    setPlayerIdx(0)
    setPlayerActive(false)
    framesRef.current = []

    const es = new EventSource(`${API}/solve/stream?algo=${algo}`)
    esRef.current = es

    es.onmessage = (e) => {
      const data = JSON.parse(e.data)
      if (data.error) {
        setError(data.error)
        setSolving(false)
        es.close()
        return
      }
      setPositions(data.positions)
      setStep(data.step)
      setIterations(data.iterations)

      if (data.done) {
        // Record ONLY the final solution replay frames
        // We collect frames from the done event onward — but since
        // warnsdorff/astar replay after done, we record from here.
        // For simpler algos done=true on final step — record that frame.
        const frame = { positions: data.positions, step: data.step }
        framesRef.current = [frame]
        setSolving(false)
        setSolved(true)
        es.close()
      }

      // Always record valid non-backtrack frames for solution path
      if (!data.done && data.positions && data.positions.length === data.step) {
        // This heuristic captures forward steps only (positions.length == step means all 27 placed)
      }
    }

    // Collect all SSE frames into framesRef for replay
    // Re-attach a second listener to record everything
    const esRecord = new EventSource(`${API}/solve/stream?algo=${algo}`)
    const recorded = []
    esRecord.onmessage = (e) => {
      const data = JSON.parse(e.data)
      if (data.error || !data.positions) { esRecord.close(); return }
      recorded.push({ positions: data.positions, step: data.step })
      if (data.done) {
        framesRef.current = recorded
        setFrames(recorded)
        setPlayerIdx(0)
        setPlayerActive(true)
        esRecord.close()
      }
    }
    esRecord.onerror = () => esRecord.close()

    es.onerror = () => {
      setError('Connection lost. Is the backend running?')
      setSolving(false)
      es.close()
    }
  }

  const isComplete = solved && step === 27
  const totalFrames = frames.length

  return (
    <div className="app">
      <div className="canvas-wrap">
        <Canvas camera={{ position: [4, 4, 4], fov: 50 }} shadows>
          <color attach="background" args={['#0d0d14']} />
          <ambientLight intensity={0.4} />
          <directionalLight position={[5, 8, 5]} intensity={1.2} castShadow />
          <pointLight position={[-4, 4, -4]} intensity={0.5} color="#a78bfa" />
          <Snake3D positions={positions} defArr={defArr} />
          <gridHelper args={[6, 6, '#333', '#222']} position={[0, -1.5, 0]} />
          <OrbitControls enableDamping dampingFactor={0.08} />
        </Canvas>
      </div>

      {/* Top bar */}
      <div className="topbar">
        <div className="logo">
          <span>🐍</span>
          <div>
            <h1>Snake 2 Box</h1>
            <p>3×3×3 Puzzle Solver</p>
          </div>
        </div>

        <div className="controls-row">
          <div className="algo-toggle">
            {ALGOS.map(a => (
              <button
                key={a.id}
                className={`algo-btn ${algo === a.id ? 'active' : ''}`}
                onClick={() => setAlgo(a.id)}
                title={a.title}
                disabled={solving}
              >
                {a.label}
              </button>
            ))}
          </div>

          {solving ? (
            <button className="stop-btn" onClick={() => {
              if (esRef.current) esRef.current.close()
              setSolving(false)
            }}>
              ⏹ Stop
            </button>
          ) : (
            <button className={`solve-btn ${solving ? 'loading' : ''}`}
              onClick={handleSolve}>
              {solved ? '🔁 Again' : '✨ Solve'}
            </button>
          )}
        </div>
      </div>

      {/* Error */}
      {error && <div className="error-banner">{error}</div>}

      {/* Status / Player panel */}
      {(solving || solved) && (
        <div className="bottom-panel">

          {/* Status row */}
          <div className="step-row">
            <span className={`step-badge ${isComplete ? 'complete' : ''}`}>
              {isComplete
                ? '✅ Solved!'
                : solving
                  ? `🔍 ${algo.toUpperCase()} searching…`
                  : `Step ${step} / 27`}
            </span>
            <span className="block-count">
              {positions.length} block{positions.length !== 1 ? 's' : ''} placed
              {iterations > 0 && ` · ${iterations.toLocaleString()} iters`}
            </span>
          </div>

          {/* Progress bar (doubles as scrubber when player active) */}
          {playerActive && totalFrames > 0 ? (
            <div className="slider-row">
              <label style={{ minWidth: 28, textAlign: 'right' }}>
                {playerIdx + 1}
              </label>
              <input
                type="range"
                min={0}
                max={totalFrames - 1}
                value={playerIdx}
                onChange={e => {
                  stopPlayback()
                  goToFrame(Number(e.target.value))
                }}
              />
              <label style={{ minWidth: 28 }}>{totalFrames}</label>
            </div>
          ) : (
            <div className="progress-bar">
              <div className="progress-fill" style={{ width: `${(step / 27) * 100}%` }} />
            </div>
          )}

          {/* Media player — only when solution recorded */}
          {playerActive && totalFrames > 0 && (
            <>
              <div className="playback">
                {/* Skip to start */}
                <button
                  title="First frame"
                  disabled={playerIdx === 0}
                  onClick={() => { stopPlayback(); goToFrame(0) }}
                >⏮</button>

                {/* Step back */}
                <button
                  title="Previous step"
                  disabled={playerIdx === 0}
                  onClick={() => { stopPlayback(); goToFrame(playerIdx - 1) }}
                >⏪</button>

                {/* Play / Pause */}
                <button
                  className="play-pause"
                  title={playing ? 'Pause' : 'Play'}
                  onClick={() => {
                    if (playing) {
                      stopPlayback()
                    } else {
                      if (playerIdx >= totalFrames - 1) goToFrame(0)
                      startPlayback()
                    }
                  }}
                >
                  {playing ? '⏸' : '▶'}
                </button>

                {/* Step forward */}
                <button
                  title="Next step"
                  disabled={playerIdx >= totalFrames - 1}
                  onClick={() => { stopPlayback(); goToFrame(playerIdx + 1) }}
                >⏩</button>

                {/* Skip to end */}
                <button
                  title="Last frame"
                  disabled={playerIdx >= totalFrames - 1}
                  onClick={() => { stopPlayback(); goToFrame(totalFrames - 1) }}
                >⏭</button>
              </div>

              {/* Speed control */}
              <div className="slider-row">
                <label>Speed</label>
                <input
                  type="range"
                  min={0}
                  max={SPEEDS.length - 1}
                  value={speedIdx}
                  onChange={e => setSpeedIdx(Number(e.target.value))}
                />
                <label style={{ minWidth: 28 }}>{SPEED_LABELS[speedIdx]}</label>
              </div>
            </>
          )}

          <div className="legend">
            <span><span className="dot purple" /> Corner</span>
            <span><span className="dot blue" /> Straight</span>
            <span><span className="dot orange" /> Latest</span>
          </div>
        </div>
      )}

      {!solving && !solved && !error && (
        <div className="canvas-hint">Drag to rotate · Pinch to zoom</div>
      )}
    </div>
  )
}
