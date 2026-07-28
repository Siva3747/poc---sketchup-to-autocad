import React, { useRef, useState, useEffect } from 'react'
import { Stage, Layer, Line, Circle, Text as KonvaText, Arc, Rect, Group } from 'react-konva'
import { useViewerStore, Point, Wall, Door, Window, Room } from '../store/viewerStore'

interface FloorPlanViewerProps {
  onCursorChange: (pos: Point | null) => void
  onSnapChange: (active: boolean) => void
}

export const FloorPlanViewer: React.FC<FloorPlanViewerProps> = ({ onCursorChange, onSnapChange }) => {
  const {
    walls,
    doors,
    windows,
    rooms,
    selectedId,
    selectElement,
    activeTool,
    setActiveTool,
    zoom,
    setZoom,
    pan,
    setPan,
    visibleLayers,
    drawingStart,
    drawingCurrent,
    addWall,
    addDoor,
    addWindow,
    updateWall
  } = useViewerStore()

  const stageRef = useRef<any>(null)
  
  // Responsive sizing states
  const [dimensions, setDimensions] = useState({
    width: window.innerWidth - 320,
    height: window.innerHeight
  })
  
  useEffect(() => {
    const handleResize = () => {
      setDimensions({
        width: window.innerWidth - 320,
        height: window.innerHeight
      })
    }
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])
  
  // Snap settings
  const GRID_SIZE = 100 // Snapping grid size in mm
  const SNAP_THRESHOLD = 150 // Pixel distance threshold in model space to snap to endpoints
  
  // Local cursor states
  const [modelCursor, setModelCursor] = useState<Point>({ x: 0, y: 0 })
  const [isSnapping, setIsSnapping] = useState<boolean>(false)
  const [hoveredWallId, setHoveredWallId] = useState<string | null>(null)
  const [draggedEndpoint, setDraggedEndpoint] = useState<{ wallId: string; pointType: 'start' | 'end' } | null>(null)

  // Get current cursor location in Model Space (mm)
  const getModelCoordinates = (e: any): Point => {
    const stage = stageRef.current
    if (!stage) return { x: 0, y: 0 }
    
    const transform = stage.getAbsoluteTransform().copy().invert()
    const pos = stage.getPointerPosition()
    if (!pos) return { x: 0, y: 0 }
    
    const pt = transform.point(pos)
    return { x: pt.x, y: pt.y }
  }

  // Snap calculation
  const calculateSnappedPoint = (rawPt: Point): { pt: Point; snapped: boolean } => {
    let bestPt = { ...rawPt }
    let snapped = false
    let minDist = SNAP_THRESHOLD
    
    // 1. Snap to wall endpoints
    if (activeTool === 'draw_wall' || activeTool === 'select') {
      for (const w of walls) {
        // Start point
        const distStart = Math.hypot(rawPt.x - w.start.x, rawPt.y - w.start.y)
        if (distStart < minDist) {
          minDist = distStart
          bestPt = { ...w.start }
          snapped = true
        }
        // End point
        const distEnd = Math.hypot(rawPt.x - w.end.x, rawPt.y - w.end.y)
        if (distEnd < minDist) {
          minDist = distEnd
          bestPt = { ...w.end }
          snapped = true
        }
      }
    }

    // 2. Orthogonal Snap when drawing walls
    if (activeTool === 'draw_wall' && drawingStart && !snapped) {
      const dx = Math.abs(rawPt.x - drawingStart.x)
      const dy = Math.abs(rawPt.y - drawingStart.y)
      // If close to horizontal or vertical
      if (dx < 150) {
        bestPt.x = drawingStart.x
        snapped = true
      } else if (dy < 150) {
        bestPt.y = drawingStart.y
        snapped = true
      }
    }

    // 3. Snap to grid if enabled and not snapped to endpoint
    if (!snapped && visibleLayers["Grid"]) {
      const gridX = Math.round(rawPt.x / GRID_SIZE) * GRID_SIZE
      const gridY = Math.round(rawPt.y / GRID_SIZE) * GRID_SIZE
      const distGrid = Math.hypot(rawPt.x - gridX, rawPt.y - gridY)
      
      if (distGrid < 80) { // snap threshold for grid
        bestPt = { x: gridX, y: gridY }
        snapped = true
      }
    }

    return { pt: bestPt, snapped }
  }

  // Mouse Move Handler
  const handleMouseMove = (e: any) => {
    const rawCursor = getModelCoordinates(e)
    const { pt: snappedCursor, snapped } = calculateSnappedPoint(rawCursor)
    
    setModelCursor(snappedCursor)
    setIsSnapping(snapped)
    onCursorChange(snappedCursor)
    onSnapChange(snapped)

    // Update drawing preview
    if (activeTool === 'draw_wall' && drawingStart) {
      useViewerStore.setState({ drawingCurrent: snappedCursor })
    }

    // Hover wall detection for doors/windows
    if (activeTool === 'add_door' || activeTool === 'add_window') {
      let closestWallId = null
      let minDistance = 250 // mm threshold
      
      for (const w of walls) {
        const dist = getDistanceToWall(snappedCursor, w)
        if (dist < minDistance) {
          minDistance = dist
          closestWallId = w.id
        }
      }
      setHoveredWallId(closestWallId)
    }

    // Handle wall endpoint drag-and-resize
    if (draggedEndpoint) {
      const { wallId, pointType } = draggedEndpoint
      updateWall(wallId, { [pointType]: snappedCursor })
    }
  }

  // Distance from point to line segment
  const getDistanceToWall = (pt: Point, w: Wall): number => {
    const x1 = w.start.x, y1 = w.start.y
    const x2 = w.end.x, y2 = w.end.y
    const px = pt.x, py = pt.y
    
    const dx = x2 - x1, dy = y2 - y1
    const lenSq = dx*dx + dy*dy
    if (lenSq < 1e-3) return Math.hypot(px - x1, py - y1)
    
    const t = Math.max(0, Math.min(1, ((px - x1)*dx + (py - y1)*dy) / lenSq))
    return Math.hypot(px - (x1 + t*dx), py - (y1 + t*dy))
  }

  // Get snap ratio position along wall centerline
  const getWallPositionRatio = (pt: Point, w: Wall): number => {
    const x1 = w.start.x, y1 = w.start.y
    const x2 = w.end.x, y2 = w.end.y
    const px = pt.x, py = pt.y
    
    const dx = x2 - x1, dy = y2 - y1
    const lenSq = dx*dx + dy*dy
    if (lenSq < 1e-3) return 0.5
    
    const t = Math.max(0, Math.min(1, ((px - x1)*dx + (py - y1)*dy) / lenSq))
    return t
  }

  // Click Handler
  const handleStageClick = (e: any) => {
    // If clicking on background, clear selection
    if (e.target === stageRef.current) {
      selectElement(null)
    }
    
    if (activeTool === 'draw_wall') {
      if (!drawingStart) {
        // Start drawing
        useViewerStore.setState({ drawingStart: modelCursor, drawingCurrent: modelCursor })
      } else {
        // Place wall
        if (Math.hypot(modelCursor.x - drawingStart.x, modelCursor.y - drawingStart.y) > 100) {
          addWall(drawingStart, modelCursor)
          // Keep drawing sequentially
          useViewerStore.setState({ drawingStart: modelCursor })
        }
      }
    } else if ((activeTool === 'add_door' || activeTool === 'add_window') && hoveredWallId) {
      const selectedWall = walls.find(w => w.id === hoveredWallId)
      if (selectedWall) {
        const ratio = getWallPositionRatio(modelCursor, selectedWall)
        if (activeTool === 'add_door') {
          addDoor(hoveredWallId, ratio)
        } else {
          addWindow(hoveredWallId, ratio)
        }
        setActiveTool('select')
        setHoveredWallId(null)
      }
    }
  }

  // Esc key / Double-click to escape drawing modes
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        useViewerStore.setState({ drawingStart: null, drawingCurrent: null })
        setActiveTool('select')
        selectElement(null)
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [activeTool])

  const handleStageDblClick = () => {
    if (activeTool === 'draw_wall') {
      // Escape current sequence
      useViewerStore.setState({ drawingStart: null, drawingCurrent: null })
      setActiveTool('select')
    }
  }

  // Zooming stage handler
  const handleWheel = (e: any) => {
    e.evt.preventDefault()
    const scaleBy = 1.08
    const stage = stageRef.current
    if (!stage) return
    
    const oldScale = stage.scaleX()
    const pointer = stage.getPointerPosition()
    if (!pointer) return

    const mousePointTo = {
      x: (pointer.x - stage.x()) / oldScale,
      y: (pointer.y - stage.y()) / oldScale,
    }

    const newScale = e.evt.deltaY < 0 ? oldScale * scaleBy : oldScale / scaleBy
    
    // Limits
    const finalScale = Math.max(0.005, Math.min(1.0, newScale))
    
    setZoom(finalScale)
    setPan({
      x: pointer.x - mousePointTo.x * finalScale,
      y: pointer.y - mousePointTo.y * finalScale
    })
  }

  // Wall double line points drawer helper
  const getWallDoubleLines = (w: Wall): number[] => {
    const x1 = w.start.x, y1 = w.start.y
    const x2 = w.end.x, y2 = w.end.y
    const t = w.thickness
    
    const dx = x2 - x1, dy = y2 - y1
    const len = Math.hypot(dx, dy)
    if (len < 1e-3) return []
    
    const nx = -dy / len, ny = dx / len
    const half = t / 2.0
    
    return [
      x1 + nx * half, y1 + ny * half,
      x2 + nx * half, y2 + ny * half,
      x2 - nx * half, y2 - ny * half,
      x1 - nx * half, y1 - ny * half,
      x1 + nx * half, y1 + ny * half
    ]
  }

  // Renders door arcs and panel representations
  const renderDoorElements = (d: Door) => {
    const w = walls.find(wall => wall.id === d.wallId)
    if (!w) return null
    
    const wx1 = w.start.x, wy1 = w.start.y
    const wx2 = w.end.x, wy2 = w.end.y
    const dx = wx2 - wx1, dy = wy2 - wy1
    const len = Math.hypot(dx, dy)
    if (len < 1e-3) return null
    
    const ux = dx / len, uy = dy / len
    
    // Position coordinates
    const dcx = wx1 + d.position * dx
    const dcy = wy1 + d.position * dy
    
    // Door opening endpoints
    const hx = dcx - (d.width / 2.0) * ux
    const hy = dcy - (d.width / 2.0) * uy
    
    // Perpendicular normal vector
    const pnx = -uy
    const pny = ux
    
    // Dir modifier: swing direction
    const dir_mult = d.direction === 'in' ? -1 : 1
    
    // Swung open endpoint (door leaf)
    const dpx = hx + d.width * pnx * dir_mult
    const dpy = hy + d.width * pny * dir_mult
    
    const angle_base = Math.atan2(uy, ux)
    const angle_swing = Math.atan2(pny * dir_mult, pnx * dir_mult)
    
    let a1 = Math.round(angle_base * (180 / Math.PI))
    let a2 = Math.round(angle_swing * (180 / Math.PI))
    
    // Arc configs
    let start = Math.min(a1, a2)
    let end = Math.max(a1, a2)
    if (end - start > 180) {
      const t = start
      start = end
      end = t + 360
    }
    
    const isSelected = selectedId === d.id

    return (
      <Group key={d.id} onClick={(e) => { e.cancelBubble = true; selectElement(d.id) }}>
        {/* Door hinge panel */}
        <Line
          points={[hx, hy, dpx, dpy]}
          stroke={isSelected ? '#3b82f6' : '#ef4444'}
          strokeWidth={isSelected ? 40 : 20}
        />
        {/* Swing path arc */}
        <Arc
          x={hx}
          y={hy}
          innerRadius={d.width - 5}
          outerRadius={d.width + 5}
          angle={end - start}
          rotation={start}
          fill={isSelected ? '#3b82f640' : '#ef444420'}
          stroke={isSelected ? '#3b82f6' : '#ef4444'}
          strokeWidth={5}
        />
      </Group>
    )
  }

  // Renders windows
  const renderWindowElements = (win: Window) => {
    const w = walls.find(wall => wall.id === win.wallId)
    if (!w) return null
    
    const wx1 = w.start.x, wy1 = w.start.y
    const wx2 = w.end.x, wy2 = w.end.y
    const dx = wx2 - wx1, dy = wy2 - wy1
    const len = Math.hypot(dx, dy)
    if (len < 1e-3) return null
    
    const ux = dx / len, uy = dy / len
    
    // Position
    const wcx = wx1 + win.position * dx
    const wcy = wy1 + win.position * dy
    
    const x1_win = wcx - (win.width / 2.0) * ux
    const y1_win = wcy - (win.width / 2.0) * uy
    const x2_win = wcx + (win.width / 2.0) * ux
    const y2_win = wcy + (win.width / 2.0) * uy
    
    const nx = -uy, ny = ux
    const half_t = w.thickness / 2.0
    
    const outline = [
      x1_win + nx * half_t, y1_win + ny * half_t,
      x2_win + nx * half_t, y2_win + ny * half_t,
      x2_win - nx * half_t, y2_win - ny * half_t,
      x1_win - nx * half_t, y1_win - ny * half_t,
    ]
    
    const isSelected = selectedId === win.id

    return (
      <Group key={win.id} onClick={(e) => { e.cancelBubble = true; selectElement(win.id) }}>
        {/* Frame Outline */}
        <Line
          points={outline}
          closed
          fill={isSelected ? '#3b82f630' : '#22d3ee20'}
          stroke={isSelected ? '#3b82f6' : '#22d3ee'}
          strokeWidth={isSelected ? 30 : 15}
        />
        {/* Longitudinal glass lines */}
        <Line
          points={[
            x1_win + nx * (half_t * 0.1), y1_win + ny * (half_t * 0.1),
            x2_win + nx * (half_t * 0.1), y2_win + ny * (half_t * 0.1)
          ]}
          stroke={isSelected ? '#3b82f6' : '#22d3ee'}
          strokeWidth={5}
        />
        <Line
          points={[
            x1_win - nx * (half_t * 0.1), y1_win - ny * (half_t * 0.1),
            x2_win - nx * (half_t * 0.1), y2_win - ny * (half_t * 0.1)
          ]}
          stroke={isSelected ? '#3b82f6' : '#22d3ee'}
          strokeWidth={5}
        />
      </Group>
    )
  }

  return (
    <div className="flex-1 w-full h-full relative outline-none bg-[#09090b]">
      {/* Background CAD grid container */}
      <Stage
        ref={stageRef}
        width={dimensions.width}
        height={dimensions.height}
        scaleX={zoom}
        scaleY={zoom}
        x={pan.x}
        y={pan.y}
        onWheel={handleWheel}
        onMouseMove={handleMouseMove}
        onClick={handleStageClick}
        onDblClick={handleStageDblClick}
        draggable={activeTool === 'select' && !draggedEndpoint}
        onDragEnd={(e) => setPan({ x: e.target.x(), y: e.target.y() })}
        className="cursor-crosshair"
      >
        {/* 1. LAYER: GRID LINES */}
        {visibleLayers["Grid"] && (
          <Layer>
            {/* Horizontal & Vertical grid reference lines in mm */}
            {Array.from({ length: 150 }).map((_, idx) => {
              const pos = (idx - 75) * 500 // lines every 500mm
              const isMajor = pos % 2000 === 0
              return (
                <React.Fragment key={`grid-${idx}`}>
                  {/* Vertical grid line */}
                  <Line
                    points={[pos, -40000, pos, 40000]}
                    stroke={isMajor ? '#ffffff0b' : '#ffffff04'}
                    strokeWidth={isMajor ? 12 : 5}
                    listening={false}
                  />
                  {/* Horizontal grid line */}
                  <Line
                    points={[-40000, pos, 40000, pos]}
                    stroke={isMajor ? '#ffffff0b' : '#ffffff04'}
                    strokeWidth={isMajor ? 12 : 5}
                    listening={false}
                  />
                </React.Fragment>
              )
            })}
          </Layer>
        )}

        {/* 2. LAYER: ROOMS */}
        {visibleLayers["Rooms"] && (
          <Layer>
            {rooms.map((r) => {
              const points = r.points.flatMap(p => [p.x, p.y])
              const cx = r.points.reduce((sum, p) => sum + p.x, 0) / r.points.length
              const cy = r.points.reduce((sum, p) => sum + p.y, 0) / r.points.length
              const isSelected = selectedId === r.id
              
              return (
                <Group key={r.id} onClick={(e) => { e.cancelBubble = true; selectElement(r.id) }}>
                  <Line
                    points={points}
                    closed
                    fill={isSelected ? '#3b82f615' : '#f59e0b09'}
                    stroke={isSelected ? '#3b82f6' : '#f59e0b20'}
                    strokeWidth={10}
                  />
                  {/* Centered label */}
                  <KonvaText
                    x={cx}
                    y={cy - 120}
                    text={`${r.name}\n${r.area.toFixed(1)} m²`}
                    fontSize={180}
                    fontFamily="Outfit, sans-serif"
                    fill={isSelected ? '#60a5fa' : '#fbbf24'}
                    align="center"
                    offsetX={500} // offset to center roughly
                  />
                </Group>
              )
            })}
          </Layer>
        )}

        {/* 3. LAYER: WALLS */}
        {visibleLayers["Walls"] && (
          <Layer>
            {walls.map((w) => {
              const doubleLinePoints = getWallDoubleLines(w)
              const isSelected = selectedId === w.id
              const isHovered = hoveredWallId === w.id
              
              return (
                <Group key={w.id}>
                  {/* Double line border representation */}
                  <Line
                    points={doubleLinePoints}
                    closed
                    fill={isHovered ? '#3b82f630' : isSelected ? '#3b82f640' : '#374151'}
                    stroke={isSelected ? '#3b82f6' : '#4b5563'}
                    strokeWidth={isSelected ? 40 : 15}
                    onClick={(e) => { e.cancelBubble = true; selectElement(w.id) }}
                  />

                  {/* Wall dimension text */}
                  {visibleLayers["Dimensions"] && (
                    <KonvaText
                      x={(w.start.x + w.end.x) / 2}
                      y={(w.start.y + w.end.y) / 2 - 300}
                      text={`${(Math.hypot(w.end.x - w.start.x, w.end.y - w.start.y) / 1000).toFixed(2)} m`}
                      fontSize={110}
                      fontFamily="monospace"
                      fill="#9ca3af"
                      align="center"
                    />
                  )}

                  {/* Resizing handles for select mode */}
                  {activeTool === 'select' && isSelected && (
                    <>
                      {/* Start point handle */}
                      <Circle
                        x={w.start.x}
                        y={w.start.y}
                        radius={150}
                        fill="#3b82f6"
                        stroke="#ffffff"
                        strokeWidth={30}
                        onMouseDown={() => setDraggedEndpoint({ wallId: w.id, pointType: 'start' })}
                        onMouseUp={() => setDraggedEndpoint(null)}
                      />
                      {/* End point handle */}
                      <Circle
                        x={w.end.x}
                        y={w.end.y}
                        radius={150}
                        fill="#3b82f6"
                        stroke="#ffffff"
                        strokeWidth={30}
                        onMouseDown={() => setDraggedEndpoint({ wallId: w.id, pointType: 'end' })}
                        onMouseUp={() => setDraggedEndpoint(null)}
                      />
                    </>
                  )}
                </Group>
              )
            })}
          </Layer>
        )}

        {/* 4. LAYER: OPENINGS (DOORS & WINDOWS) */}
        <Layer>
          {visibleLayers["Doors"] && doors.map(d => renderDoorElements(d))}
          {visibleLayers["Windows"] && windows.map(w => renderWindowElements(w))}
        </Layer>

        {/* 5. LAYER: INTERACTIVE GUIDES */}
        <Layer>
          {/* Snap position helper dot */}
          {isSnapping && (
            <Circle
              x={modelCursor.x}
              y={modelCursor.y}
              radius={80}
              fill="#10b981"
              stroke="#ffffff"
              strokeWidth={20}
              listening={false}
            />
          )}

          {/* Wall drawing preview line */}
          {activeTool === 'draw_wall' && drawingStart && drawingCurrent && (
            <Line
              points={[drawingStart.x, drawingStart.y, drawingCurrent.x, drawingCurrent.y]}
              stroke="#10b981"
              strokeWidth={30}
              dash={[150, 150]}
              listening={false}
            />
          )}
        </Layer>
      </Stage>
    </div>
  )
}
