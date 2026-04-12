import { useState, useEffect, useRef } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { OrbitControls, Line, Text } from '@react-three/drei'
import * as THREE from 'three'
import './App.css'

const API = 'http://localhost:8000'

// Color a block based on its type (corner vs straight) and index
function blockColor(defArr, index, isLatest) {
  if (isLatest) return '#ff6b35'
  if (!defArr || defArr[index] === undefined) return '#4a9eff'
  return defArr[index] === 1 ? '#a78bfa' : '#4a9eff'
}

function Block({ position, index, defArr, isLatest, totalBlocks }) {
  const meshRef = useRef()
  const color = blockColor(defArr, index, isLatest)

  useFrame((state) => {
    if (meshRef.current && isLatest) {
      meshRef.current.scale.setScalar(
        1 + Math.sin(state.clock.elapsedTime * 3) * 0.08
      )
    } else if (meshRef.current) {
      meshRef.current.scale.setScalar(1)
    }
  })

  return (
    <mesh ref={meshRef} position={position} castShadow receiveShadow>
      <boxGeometry args={[0.85, 0.85, 0.85]} />
      <meshStandardMaterial
        color={color}
        roughness={0.3}
        metalness={0.2}
        transparent
        opacity={isLatest ? 1.0 : 0.85}
      />
    </mesh>
  )
}

function Snake3D({ positions, defArr }) {
  if (!positions || positions.length === 0) return null

  // center the snake/cube
  const cx = 1, cy = 1, cz = 1

  const pts = positions.map(p => [p.x - cx, p.y - cy, p.z - cz])

  return (
    <group>
      {/* Connection line */}
      {pts.length > 1 && (
        <Line
          points={pts}
          color="#ffffff"
          lineWidth={2}
          opacity={0.4}
          transparent
        />
      )}
      {/* Blocks */}
      {pts.map((pos, i) => (
        <Block
          key={i}
          position={pos}
          index={i}
          defArr={defArr}
          isLatest={i === pts.length - 1}
          totalBlocks={positions.length}
        />
      ))}
    </group>
  )
}

function GridHelper() {
  return (
    <group>
      <gridHelper args={[6, 6, '#333', '#222']} position={[0, -1.5, 0]} />
    </group>
  )
}

export default function App() {
  const [steps, setSteps] = useState([])
  const [defArr, setDefArr] = useState([])
  const [currentStep, setCurrentStep] = useState(0)
  const [isPlaying, setIsPlaying] = useState(false)
  const [speed, setSpeed] = useState(600)
  const [loading, setLoading] = useState(false)
  const [solved, setSolved] = useState(false)
  const intervalRef = useRef(null)

  useEffect(() => {
    // Load def_arr
    fetch(`${API}/def_arr`)
      .then(r => r.json())
      .then(d => setDefArr(d.def_arr))
      .catch(() => {})
  }, [])

  function handleSolve() {
    setLoading(true)
    setSolved(false)
    setIsPlaying(false)
    setCurrentStep(0)
    fetch(`${API}/solve`, { method: 'POST' })
      .then(r => r.json())
      .then(data => {
        setSteps(data.steps)
        setDefArr(data.def_arr)
        setCurrentStep(0)
        setLoading(false)
        setSolved(true)
      })
      .catch(() => setLoading(false))
  }

  useEffect(() => {
    if (isPlaying && steps.length > 0) {
      intervalRef.current = setInterval(() => {
        setCurrentStep(s => {
          if (s >= steps.length - 1) {
            setIsPlaying(false)
            return s
          }
          return s + 1
        })
      }, speed)
    } else {
      clearInterval(intervalRef.current)
    }
    return () => clearInterval(intervalRef.current)
  }, [isPlaying, speed, steps.length])

  const currentPositions = steps[currentStep]?.positions || []
  const isComplete = steps[currentStep]?.valid

  return (
    <div className="app">
      <div className="sidebar">
        <div className="logo">
          <span className="logo-icon">🐍</span>
          <div>
            <h1>Snake 2 Box</h1>
            <p>3×3×3 Puzzle Solver</p>
          </div>
        </div>

        <div className="puzzle-desc">
          A chain of 27 wooden blocks linked by elastic string.
          Fold the snake into a perfect cube!
        </div>

        <button
          className={`solve-btn ${loading ? 'loading' : ''}`}
          onClick={handleSolve}
          disabled={loading}
        >
          {loading ? '🔄 Solving...' : '✨ Solve Puzzle'}
        </button>

        {solved && steps.length > 0 && (
          <div className="controls">
            <div className="step-info">
              <span className={`step-badge ${isComplete ? 'complete' : ''}`}>
                {isComplete ? '✅ Solved!' : `Step ${currentStep + 1} / ${steps.length}`}
              </span>
              <span className="block-count">{currentPositions.length} blocks placed</span>
            </div>

            <div className="progress-bar">
              <div
                className="progress-fill"
                style={{ width: `${((currentStep + 1) / steps.length) * 100}%` }}
              />
            </div>

            <div className="playback">
              <button onClick={() => setCurrentStep(s => Math.max(0, s - 1))} disabled={currentStep === 0}>⏮</button>
              <button
                className="play-pause"
                onClick={() => setIsPlaying(p => !p)}
              >
                {isPlaying ? '⏸' : '▶️'}
              </button>
              <button onClick={() => setCurrentStep(s => Math.min(steps.length - 1, s + 1))} disabled={currentStep === steps.length - 1}>⏭</button>
            </div>

            <div className="speed-control">
              <label>Speed</label>
              <input
                type="range"
                min={100}
                max={1200}
                step={100}
                value={1300 - speed}
                onChange={e => setSpeed(1300 - Number(e.target.value))}
              />
              <span>{speed < 400 ? 'Fast' : speed < 800 ? 'Med' : 'Slow'}</span>
            </div>

            <div className="scrubber">
              <label>Scrub</label>
              <input
                type="range"
                min={0}
                max={steps.length - 1}
                value={currentStep}
                onChange={e => { setIsPlaying(false); setCurrentStep(Number(e.target.value)) }}
              />
            </div>
          </div>
        )}

        {defArr.length > 0 && (
          <div className="legend">
            <h3>Block Types</h3>
            <div className="legend-item">
              <span className="dot purple" /> Corner (elastic turns)
            </div>
            <div className="legend-item">
              <span className="dot blue" /> Straight (elastic goes through)
            </div>
            <div className="legend-item">
              <span className="dot orange" /> Latest block placed
            </div>
          </div>
        )}
      </div>

      <div className="canvas-wrap">
        <Canvas
          camera={{ position: [4, 4, 4], fov: 50 }}
          shadows
        >
          <color attach="background" args={['#0d0d14']} />
          <ambientLight intensity={0.4} />
          <directionalLight position={[5, 8, 5]} intensity={1.2} castShadow />
          <pointLight position={[-4, 4, -4]} intensity={0.5} color="#a78bfa" />
          <Snake3D positions={currentPositions} defArr={defArr} />
          <GridHelper />
          <OrbitControls enableDamping dampingFactor={0.08} />
        </Canvas>

        {!solved && !loading && (
          <div className="canvas-hint">
            👆 Click <strong>Solve Puzzle</strong> to start the animation
          </div>
        )}
      </div>
    </div>
  )
}
