import React, { useRef, useMemo } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { OrbitControls, Grid, Text, Box, Line } from '@react-three/drei'
import * as THREE from 'three'
import { useViewerStore, Wall, Door, Window, Room } from '../store/viewerStore'

// ─── Unit scale: mm → Three.js world units (1 unit = 1 m) ───────────────────
const MM = 0.001

interface WallMeshProps { wall: Wall; selected: boolean; onClick: () => void }
function WallMesh({ wall, selected, onClick }: WallMeshProps) {
  const { start, end, thickness, height } = wall
  const dx = (end.x - start.x) * MM
  const dy = (end.y - start.y) * MM
  const len = Math.hypot(dx, dy)
  const cx = ((start.x + end.x) / 2) * MM
  const cz = ((start.y + end.y) / 2) * MM
  const angle = Math.atan2(dy, dx)
  const h = height * MM
  const t = thickness * MM

  return (
    <mesh
      position={[cx, h / 2, cz]}
      rotation={[0, -angle, 0]}
      onClick={(e) => { e.stopPropagation(); onClick() }}
      castShadow
    >
      <boxGeometry args={[len, h, t]} />
      <meshStandardMaterial
        color={selected ? '#3b82f6' : '#64748b'}
        roughness={0.6}
        metalness={0.05}
        transparent={selected}
        opacity={selected ? 0.85 : 1}
      />
    </mesh>
  )
}

interface DoorMeshProps { door: Door; walls: Wall[] }
function DoorMesh({ door, walls }: DoorMeshProps) {
  const wall = walls.find(w => w.id === door.wallId)
  if (!wall) return null
  const { start, end } = wall
  const dx = (end.x - start.x) * MM
  const dy = (end.y - start.y) * MM
  const cx = (start.x * MM + door.position * dx)
  const cz = (start.y * MM + door.position * dy)
  const h = door.height * MM
  const w = door.width * MM
  const angle = Math.atan2(dy, dx)

  return (
    <group position={[cx, h / 2, cz]} rotation={[0, -angle, 0]}>
      {/* Door frame */}
      <mesh>
        <boxGeometry args={[w, h, 0.05]} />
        <meshStandardMaterial color="#ef4444" transparent opacity={0.5} />
      </mesh>
      {/* Door panel (open position) */}
      <mesh position={[w / 2, 0, w / 2]} rotation={[0, Math.PI / 2, 0]}>
        <boxGeometry args={[w, h * 0.95, 0.04]} />
        <meshStandardMaterial color="#dc2626" />
      </mesh>
    </group>
  )
}

interface WindowMeshProps { win: Window; walls: Wall[] }
function WindowMesh({ win, walls }: WindowMeshProps) {
  const wall = walls.find(w => w.id === win.wallId)
  if (!wall) return null
  const { start, end } = wall
  const dx = (end.x - start.x) * MM
  const dy = (end.y - start.y) * MM
  const cx = start.x * MM + win.position * dx
  const cz = start.y * MM + win.position * dy
  const cy = (win.elevation + win.height / 2) * MM
  const ww = win.width * MM
  const wh = win.height * MM
  const angle = Math.atan2(dy, dx)

  return (
    <mesh position={[cx, cy, cz]} rotation={[0, -angle, 0]}>
      <boxGeometry args={[ww, wh, 0.08]} />
      <meshStandardMaterial color="#22d3ee" transparent opacity={0.4} roughness={0.1} metalness={0.3} />
    </mesh>
  )
}

interface RoomLabelProps { room: Room }
function RoomLabel({ room }: RoomLabelProps) {
  const pts = room.points
  if (!pts.length) return null
  const cx = pts.reduce((s, p) => s + p.x, 0) / pts.length * MM
  const cz = pts.reduce((s, p) => s + p.y, 0) / pts.length * MM

  return (
    <group position={[cx, 0.1, cz]}>
      <Text
        fontSize={0.25}
        color="#f59e0b"
        anchorX="center"
        anchorY="middle"
        rotation={[-Math.PI / 2, 0, 0]}
      >
        {`${room.name}\n${room.area.toFixed(1)}m²`}
      </Text>
    </group>
  )
}

// Floor slab extruded from room polygon
function RoomFloor({ room, selected, onClick }: { room: Room; selected: boolean; onClick: () => void }) {
  const pts = room.points
  if (pts.length < 3) return null

  const shape = useMemo(() => {
    const s = new THREE.Shape()
    s.moveTo(pts[0].x * MM, pts[0].y * MM)
    for (let i = 1; i < pts.length; i++) s.lineTo(pts[i].x * MM, pts[i].y * MM)
    s.closePath()
    return s
  }, [pts])

  return (
    <mesh
      position={[0, -0.01, 0]}
      rotation={[-Math.PI / 2, 0, 0]}
      onClick={(e) => { e.stopPropagation(); onClick() }}
    >
      <shapeGeometry args={[shape]} />
      <meshStandardMaterial
        color={selected ? '#3b82f640' : '#1e293b'}
        transparent opacity={0.7} side={THREE.DoubleSide}
      />
    </mesh>
  )
}

// Bounding box helper
function SceneCenter({ walls }: { walls: Wall[] }) {
  if (!walls.length) return null
  const xs = walls.flatMap(w => [w.start.x, w.end.x]).map(v => v * MM)
  const zs = walls.flatMap(w => [w.start.y, w.end.y]).map(v => v * MM)
  const cx = (Math.min(...xs) + Math.max(...xs)) / 2
  const cz = (Math.min(...zs) + Math.max(...zs)) / 2
  return <group position={[-cx, 0, -cz]} />
}

export const Viewer3D: React.FC = () => {
  const { walls, doors, windows, rooms, selectedId, selectElement, showAiOverlay, aiDetections } = useViewerStore()

  const unknownDetections = showAiOverlay
    ? aiDetections.filter(d => d.type === 'unknown' || d.needs_review)
    : []

  return (
    <div className="flex-1 w-full h-full bg-[#09090b]">
      <Canvas
        shadows
        camera={{ position: [15, 12, 15], fov: 45, near: 0.1, far: 10000 }}
        gl={{ antialias: true }}
        onPointerMissed={() => selectElement(null)}
      >
        {/* Lighting */}
        <ambientLight intensity={0.4} />
        <directionalLight position={[10, 20, 10]} intensity={1.2} castShadow shadow-mapSize={[2048, 2048]} />
        <directionalLight position={[-10, 5, -10]} intensity={0.3} color="#93c5fd" />
        <hemisphereLight args={['#1e3a5f', '#0f172a', 0.3]} />

        {/* Grid */}
        <Grid
          args={[100, 100]}
          cellSize={1}
          cellThickness={0.5}
          cellColor="#1e293b"
          sectionSize={5}
          sectionThickness={1}
          sectionColor="#334155"
          fadeDistance={80}
          fadeStrength={1}
          infiniteGrid
        />

        {/* Camera Controls */}
        <OrbitControls makeDefault enableDamping dampingFactor={0.05} minDistance={1} maxDistance={500} />

        {/* Rooms */}
        {rooms.map(r => (
          <group key={r.id}>
            <RoomFloor room={r} selected={selectedId === r.id} onClick={() => selectElement(r.id)} />
            <RoomLabel room={r} />
          </group>
        ))}

        {/* Walls */}
        {walls.map(w => (
          <WallMesh
            key={w.id}
            wall={w}
            selected={selectedId === w.id}
            onClick={() => selectElement(w.id)}
          />
        ))}

        {/* Doors */}
        {doors.map(d => <DoorMesh key={d.id} door={d} walls={walls} />)}

        {/* Windows */}
        {windows.map(w => <WindowMesh key={w.id} win={w} walls={walls} />)}

        {/* AI Review overlays — highlight unknown/low-confidence objects */}
        {unknownDetections.map(det => {
          const wall = walls.find(w => w.id === det.id)
          if (!wall) return null
          const cx = ((wall.start.x + wall.end.x) / 2) * MM
          const cz = ((wall.start.y + wall.end.y) / 2) * MM
          const h = wall.height * MM
          return (
            <mesh key={`ai-${det.id}`} position={[cx, h / 2, cz]}>
              <boxGeometry args={[
                Math.hypot((wall.end.x - wall.start.x) * MM, (wall.end.y - wall.start.y) * MM) + 0.1,
                h + 0.1,
                wall.thickness * MM + 0.1
              ]} />
              <meshStandardMaterial color="#f59e0b" wireframe />
            </mesh>
          )
        })}
      </Canvas>

      {/* 3D Controls legend */}
      <div className="absolute bottom-4 left-1/2 -translate-x-1/2 flex gap-3 text-[10px] text-gray-500 pointer-events-none">
        <span>🖱 Drag to orbit</span>
        <span>·</span>
        <span>Scroll to zoom</span>
        <span>·</span>
        <span>Right-drag to pan</span>
      </div>
    </div>
  )
}
