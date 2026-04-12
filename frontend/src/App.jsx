import { useState, useEffect, useRef } from 'react'
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

export default function App() {
  const [defArr, setDefArr] = useState([])
  const [positions, setPositions] = useState([])
  const [step, setStep] = useState(0)
  const [iterations, setIterations] = useState(0)
  const [solving, setSolving] = useState(false)
  const [solved, setSolved] = useState(false)
  const [error, setError] = useState(null)
  const [algo, setAlgo] = useState('dfs')
  const esRef = useRef(null)

  const ALGOS = [
    { id: 'dfs',        label: 'DFS',  title: 'Depth-First Search — goes deep, backtracks on dead ends' },
    { id: 'bfs',        label: 'BFS',  title: 'Breadth-First Search — explores level by level' },
    { id: 'dfs_pruned', label: 'DFS+', title: 'DFS + bbox & flood-fill pruning — far fewer iterations' },
    { id: 'astar',      label: 'A★',   title: 'A* — guided by depth + compactness heuristic' },
  ]

  useEffect(() => {
    fetch(`${API}/def_arr`).then(r => r.json()).then(d => setDefArr(d.def_arr)).catch(() => {})
  }, [])

  function handleSolve() {
    if (esRef.current) esRef.current.close()

    setSolving(true)
    setSolved(false)
    setError(null)
    setPositions([])
    setStep(0)
    setIterations(0)

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
        setSolving(false)
        setSolved(true)
        es.close()
      }
    }

    es.onerror = () => {
      setError('Connection lost. Is the backend running?')
      setSolving(false)
      es.close()
    }
  }

  const isComplete = solved && step === 27

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
                disabled={solving}
                title={a.title}
              >
                {a.label}
              </button>
            ))}
          </div>

          <button className={`solve-btn ${solving ? 'loading' : ''}`}
            onClick={handleSolve} disabled={solving}>
            {solving ? '🔄 Solving…' : solved ? '🔁 Again' : '✨ Solve'}
          </button>
        </div>
      </div>

      {/* Error */}
      {error && <div className="error-banner">{error}</div>}

      {/* Status panel */}
      {(solving || solved) && (
        <div className="bottom-panel">
          <div className="step-row">
            <span className={`step-badge ${isComplete ? 'complete' : ''}`}>
              {isComplete ? '✅ Solved!' : solving ? `🔍 ${algo.toUpperCase()} searching…` : `Step ${step} / 27`}
            </span>
            <span className="block-count">
              {positions.length} block{positions.length !== 1 ? 's' : ''} placed
              {iterations > 0 && ` · ${iterations.toLocaleString()} iters`}
            </span>
          </div>

          <div className="progress-bar">
            <div className="progress-fill" style={{ width: `${(step / 27) * 100}%` }} />
          </div>

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
