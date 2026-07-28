import React, { useEffect, useState } from 'react'
import { 
  Save, 
  Download, 
  FileJson, 
  PenTool, 
  DownloadCloud,
  Layers, 
  Maximize, 
  FolderOpen,
  ArrowLeft,
  ChevronRight,
  Code
} from 'lucide-react'
import { useViewerStore, Wall, Door, Window, Room } from '../store/viewerStore'
import { apiService } from '../services/api'

interface EditorSidebarProps {
  onBackToUpload: () => void
}

export const EditorSidebar: React.FC<EditorSidebarProps> = ({ onBackToUpload }) => {
  const {
    projectId,
    filename,
    metadata,
    walls,
    doors,
    windows,
    rooms,
    selectedId,
    selectElement,
    updateWall,
    updateDoor,
    updateWindow,
    deleteElement,
    isSaving,
    setSaving,
    setError,
    setProject
  } = useViewerStore()

  // Local state for properties inputs
  const [wallThickness, setWallThickness] = useState<string>('')
  const [wallHeight, setWallHeight] = useState<string>('')
  
  const [doorWidth, setDoorWidth] = useState<string>('')
  const [doorHeight, setDoorHeight] = useState<string>('')
  
  const [windowWidth, setWindowWidth] = useState<string>('')
  const [windowHeight, setWindowHeight] = useState<string>('')
  const [windowElevation, setWindowElevation] = useState<string>('')
  
  const [roomName, setRoomName] = useState<string>('')

  // Determine selected element type and fetch details
  const selectedWall = walls.find(w => w.id === selectedId)
  const selectedDoor = doors.find(d => d.id === selectedId)
  const selectedWindow = windows.find(w => w.id === selectedId)
  const selectedRoom = rooms.find(r => r.id === selectedId)

  // Sync inputs with selected element updates
  useEffect(() => {
    if (selectedWall) {
      setWallThickness(selectedWall.thickness.toString())
      setWallHeight(selectedWall.height.toString())
    } else if (selectedDoor) {
      setDoorWidth(selectedDoor.width.toString())
      setDoorHeight(selectedDoor.height.toString())
    } else if (selectedWindow) {
      setWindowWidth(selectedWindow.width.toString())
      setWindowHeight(selectedWindow.height.toString())
      setWindowElevation(selectedWindow.elevation.toString())
    } else if (selectedRoom) {
      setRoomName(selectedRoom.name)
    }
  }, [selectedId, selectedWall, selectedDoor, selectedWindow, selectedRoom])

  const handleSaveToServer = async () => {
    if (!projectId) return
    setSaving(true)
    setError(null)
    try {
      const response = await apiService.updateProjectData(projectId, {
        metadata,
        walls,
        doors,
        windows,
        rooms
      })
      
      // Reload details to keep file existence flags in sync
      const freshData = await apiService.getProjectData(projectId)
      setProject(projectId, filename, freshData.floorplan)
    } catch (err: any) {
      setError("Failed to save changes and regenerate CAD files.")
    } finally {
      setSaving(false)
    }
  }

  const handleDownloadScript = async () => {
    try {
      const scriptText = await apiService.getSketchUpExporterScript()
      
      const blob = new Blob([scriptText], { type: 'text/plain' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'sketchup_json_exporter.rb'
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch (err) {
      alert("Failed to download script. Copy directly from repository root.")
    }
  }

  const [downloadingFormat, setDownloadingFormat] = useState<'json' | 'dxf' | 'dwg' | null>(null)

  const handleDownloadFile = async (format: 'json' | 'dxf' | 'dwg') => {
    if (!projectId) return
    setDownloadingFormat(format)
    try {
      const { data, filename: downloadFilename } = await apiService.downloadProjectFile(projectId, format)
      
      const blob = new Blob([data], { type: data.type })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      
      // Construct a safe filename if the backend did not provide a header-based one
      let finalName = downloadFilename
      if (!finalName || finalName.startsWith('project_')) {
        const cleanBaseName = filename.substring(0, filename.lastIndexOf('.')) || filename
        finalName = `${cleanBaseName}.${format}`
      }
      
      a.download = finalName
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch (err) {
      console.error(err)
      alert(`Failed to download ${format.toUpperCase()} file.`)
    } finally {
      setDownloadingFormat(null)
    }
  }

  // Value submission handlers
  const handleWallUpdate = () => {
    if (!selectedWall) return
    updateWall(selectedWall.id, {
      thickness: parseFloat(wallThickness) || selectedWall.thickness,
      height: parseFloat(wallHeight) || selectedWall.height
    })
  }

  const handleDoorUpdate = (field: keyof Door, val: any) => {
    if (!selectedDoor) return
    updateDoor(selectedDoor.id, { [field]: val })
  }

  const handleWindowUpdate = () => {
    if (!selectedWindow) return
    updateWindow(selectedWindow.id, {
      width: parseFloat(windowWidth) || selectedWindow.width,
      height: parseFloat(windowHeight) || selectedWindow.height,
      elevation: parseFloat(windowElevation) || selectedWindow.elevation
    })
  }

  const handleRoomUpdate = () => {
    if (!selectedRoom) return
    // Directly update name in store
    useViewerStore.setState((state) => ({
      rooms: state.rooms.map(r => r.id === selectedRoom.id ? { ...r, name: roomName } : r)
    }))
  }

  return (
    <div className="w-80 h-full glass-panel border-l border-gray-800/80 flex flex-col justify-between shrink-0 shadow-premium z-10 text-xs">
      {/* Header Info */}
      <div className="p-4 border-b border-gray-800/80">
        <button 
          onClick={onBackToUpload}
          className="flex items-center gap-1.5 text-gray-400 hover:text-white transition-colors mb-4 group"
        >
          <ArrowLeft className="h-3.5 w-3.5 group-hover:-translate-x-0.5 transition-transform" />
          <span>Upload New File</span>
        </button>
        
        <h2 className="text-sm font-bold text-white tracking-wide truncate" title={filename}>
          {filename}
        </h2>
        <p className="text-[10px] text-gray-500 font-mono mt-0.5">
          PROJ ID: {projectId?.substring(0, 8)}...
        </p>
      </div>

      {/* Main Inspector Body */}
      <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-4">
        {selectedId ? (
          <div>
            {/* ELEMENT PROPERTIES DETAILED VIEW */}
            <div className="flex items-center justify-between border-b border-gray-800 pb-2 mb-3">
              <span className="text-xs font-bold text-white uppercase tracking-wider">Object Inspector</span>
              <button 
                onClick={() => selectElement(null)}
                className="text-[10px] text-blue-400 hover:underline"
              >
                Clear Selection
              </button>
            </div>

            {/* WALL DETAIL */}
            {selectedWall && (
              <div className="flex flex-col gap-3">
                <div className="flex items-center gap-2 text-white font-semibold">
                  <PenTool className="h-4 w-4 text-blue-400" />
                  <span>Wall Element</span>
                </div>
                <div className="text-[10px] text-gray-400 font-mono -mt-1.5">{selectedWall.id}</div>

                <div className="flex flex-col gap-1.5 mt-1">
                  <label className="text-gray-400 font-medium">Thickness ({metadata.unit})</label>
                  <input
                    type="number"
                    value={wallThickness}
                    onChange={(e) => setWallThickness(e.target.value)}
                    onBlur={handleWallUpdate}
                    className="px-2.5 py-1.5 rounded-lg glass-input text-white"
                  />
                </div>

                <div className="flex flex-col gap-1.5">
                  <label className="text-gray-400 font-medium">Height ({metadata.unit})</label>
                  <input
                    type="number"
                    value={wallHeight}
                    onChange={(e) => setWallHeight(e.target.value)}
                    onBlur={handleWallUpdate}
                    className="px-2.5 py-1.5 rounded-lg glass-input text-white"
                  />
                </div>

                <div className="p-3 bg-gray-950/40 rounded-xl border border-gray-900 flex flex-col gap-1.5 text-[11px] mt-2">
                  <div className="flex justify-between text-gray-500">
                    <span>Center Length:</span>
                    <span className="text-white font-mono font-medium">
                      {(Math.hypot(selectedWall.end.x - selectedWall.start.x, selectedWall.end.y - selectedWall.start.y) / 1000).toFixed(2)} m
                    </span>
                  </div>
                  <div className="flex justify-between text-gray-500">
                    <span>Start:</span>
                    <span className="text-gray-300 font-mono">
                      ({Math.round(selectedWall.start.x)}, {Math.round(selectedWall.start.y)})
                    </span>
                  </div>
                  <div className="flex justify-between text-gray-500">
                    <span>End:</span>
                    <span className="text-gray-300 font-mono">
                      ({Math.round(selectedWall.end.x)}, {Math.round(selectedWall.end.y)})
                    </span>
                  </div>
                </div>
              </div>
            )}

            {/* DOOR DETAIL */}
            {selectedDoor && (
              <div className="flex flex-col gap-3">
                <div className="flex items-center gap-2 text-white font-semibold">
                  <ChevronRight className="h-4 w-4 text-blue-400" />
                  <span>Door Element</span>
                </div>
                <div className="text-[10px] text-gray-400 font-mono -mt-1.5">{selectedDoor.id}</div>

                <div className="flex flex-col gap-1.5 mt-1">
                  <label className="text-gray-400 font-medium">Width ({metadata.unit})</label>
                  <input
                    type="number"
                    value={doorWidth}
                    onChange={(e) => setDoorWidth(e.target.value)}
                    onBlur={() => handleDoorUpdate('width', parseFloat(doorWidth) || selectedDoor.width)}
                    className="px-2.5 py-1.5 rounded-lg glass-input text-white"
                  />
                </div>

                <div className="flex flex-col gap-1.5">
                  <label className="text-gray-400 font-medium">Height ({metadata.unit})</label>
                  <input
                    type="number"
                    value={doorHeight}
                    onChange={(e) => setDoorHeight(e.target.value)}
                    onBlur={() => handleDoorUpdate('height', parseFloat(doorHeight) || selectedDoor.height)}
                    className="px-2.5 py-1.5 rounded-lg glass-input text-white"
                  />
                </div>

                <div className="flex gap-2.5 mt-1">
                  <div className="flex-1 flex flex-col gap-1">
                    <span className="text-gray-400 font-medium mb-1">Hand</span>
                    <div className="flex rounded-lg overflow-hidden border border-gray-800 bg-gray-950/40">
                      <button
                        onClick={() => handleDoorUpdate('hand', 'left')}
                        className={`flex-1 py-1 text-center font-semibold ${selectedDoor.hand === 'left' ? 'bg-blue-600 text-white' : 'text-gray-500 hover:text-gray-300'}`}
                      >
                        LH
                      </button>
                      <button
                        onClick={() => handleDoorUpdate('hand', 'right')}
                        className={`flex-1 py-1 text-center font-semibold ${selectedDoor.hand === 'right' ? 'bg-blue-600 text-white' : 'text-gray-500 hover:text-gray-300'}`}
                      >
                        RH
                      </button>
                    </div>
                  </div>

                  <div className="flex-1 flex flex-col gap-1">
                    <span className="text-gray-400 font-medium mb-1">Swing Direction</span>
                    <div className="flex rounded-lg overflow-hidden border border-gray-800 bg-gray-950/40">
                      <button
                        onClick={() => handleDoorUpdate('direction', 'in')}
                        className={`flex-1 py-1 text-center font-semibold ${selectedDoor.direction === 'in' ? 'bg-blue-600 text-white' : 'text-gray-500 hover:text-gray-300'}`}
                      >
                        IN
                      </button>
                      <button
                        onClick={() => handleDoorUpdate('direction', 'out')}
                        className={`flex-1 py-1 text-center font-semibold ${selectedDoor.direction === 'out' ? 'bg-blue-600 text-white' : 'text-gray-500 hover:text-gray-300'}`}
                      >
                        OUT
                      </button>
                    </div>
                  </div>
                </div>

                <div className="flex flex-col gap-1 mt-1">
                  <span className="text-gray-400 font-medium">Position along wall</span>
                  <input
                    type="range"
                    min="0.05"
                    max="0.95"
                    step="0.01"
                    value={selectedDoor.position}
                    onChange={(e) => handleDoorUpdate('position', parseFloat(e.target.value))}
                    className="w-full h-1 bg-gray-800 rounded-lg appearance-none cursor-pointer accent-blue-500"
                  />
                  <div className="flex justify-between font-mono text-[9px] text-gray-500 -mt-0.5">
                    <span>Start</span>
                    <span>{(selectedDoor.position * 100).toFixed(0)}%</span>
                    <span>End</span>
                  </div>
                </div>
              </div>
            )}

            {/* WINDOW DETAIL */}
            {selectedWindow && (
              <div className="flex flex-col gap-3">
                <div className="flex items-center gap-2 text-white font-semibold">
                  <Maximize className="h-4 w-4 text-blue-400" />
                  <span>Window Element</span>
                </div>
                <div className="text-[10px] text-gray-400 font-mono -mt-1.5">{selectedWindow.id}</div>

                <div className="flex flex-col gap-1.5 mt-1">
                  <label className="text-gray-400 font-medium">Width ({metadata.unit})</label>
                  <input
                    type="number"
                    value={windowWidth}
                    onChange={(e) => setWindowWidth(e.target.value)}
                    onBlur={handleWindowUpdate}
                    className="px-2.5 py-1.5 rounded-lg glass-input text-white"
                  />
                </div>

                <div className="flex flex-col gap-1.5">
                  <label className="text-gray-400 font-medium">Height ({metadata.unit})</label>
                  <input
                    type="number"
                    value={windowHeight}
                    onChange={(e) => setWindowHeight(e.target.value)}
                    onBlur={handleWindowUpdate}
                    className="px-2.5 py-1.5 rounded-lg glass-input text-white"
                  />
                </div>

                <div className="flex flex-col gap-1.5">
                  <label className="text-gray-400 font-medium">Sill Elevation ({metadata.unit})</label>
                  <input
                    type="number"
                    value={windowElevation}
                    onChange={(e) => setWindowElevation(e.target.value)}
                    onBlur={handleWindowUpdate}
                    className="px-2.5 py-1.5 rounded-lg glass-input text-white"
                  />
                </div>

                <div className="flex flex-col gap-1 mt-1">
                  <span className="text-gray-400 font-medium">Position along wall</span>
                  <input
                    type="range"
                    min="0.05"
                    max="0.95"
                    step="0.01"
                    value={selectedWindow.position}
                    onChange={(e) => updateWindow(selectedWindow.id, { position: parseFloat(e.target.value) })}
                    className="w-full h-1 bg-gray-800 rounded-lg appearance-none cursor-pointer accent-blue-500"
                  />
                  <div className="flex justify-between font-mono text-[9px] text-gray-500 -mt-0.5">
                    <span>Start</span>
                    <span>{(selectedWindow.position * 100).toFixed(0)}%</span>
                    <span>End</span>
                  </div>
                </div>
              </div>
            )}

            {/* ROOM DETAIL */}
            {selectedRoom && (
              <div className="flex flex-col gap-3">
                <div className="flex items-center gap-2 text-white font-semibold">
                  <Layers className="h-4 w-4 text-blue-400" />
                  <span>Enclosed Room</span>
                </div>
                <div className="text-[10px] text-gray-400 font-mono -mt-1.5">{selectedRoom.id}</div>

                <div className="flex flex-col gap-1.5 mt-1">
                  <label className="text-gray-400 font-medium">Room Name</label>
                  <input
                    type="text"
                    value={roomName}
                    onChange={(e) => setRoomName(e.target.value)}
                    onBlur={handleRoomUpdate}
                    className="px-2.5 py-1.5 rounded-lg glass-input text-white text-xs font-semibold"
                  />
                </div>

                <div className="p-3 bg-blue-500/5 rounded-xl border border-blue-500/10 flex justify-between text-xs mt-2">
                  <span className="text-gray-400 font-medium">Total Area:</span>
                  <span className="text-blue-400 font-bold font-mono">
                    {selectedRoom.area.toFixed(2)} m²
                  </span>
                </div>
              </div>
            )}

            {/* Delete button inside inspector */}
            <button
              onClick={() => deleteElement(selectedId)}
              className="mt-6 w-full py-2 rounded-xl bg-rose-500/10 hover:bg-rose-500/20 text-rose-500 hover:text-rose-400 font-semibold border border-rose-500/20 transition-all flex items-center justify-center gap-2"
            >
              Remove Element
            </button>
          </div>
        ) : (
          /* METADATA & DELIVERABLES EXPORT PANEL */
          <div className="flex flex-col gap-4">
            <div className="border-b border-gray-800 pb-2">
              <span className="text-xs font-bold text-white uppercase tracking-wider">File Metadata</span>
            </div>

            <div className="flex flex-col gap-1.5">
              <div className="flex justify-between text-gray-500">
                <span>Model Name:</span>
                <span className="text-gray-300 font-medium truncate max-w-[150px]">{metadata.name}</span>
              </div>
              <div className="flex justify-between text-gray-500">
                <span>Total Walls:</span>
                <span className="text-gray-300 font-mono">{walls.length}</span>
              </div>
              <div className="flex justify-between text-gray-500">
                <span>Total Openings:</span>
                <span className="text-gray-300 font-mono">{doors.length + windows.length}</span>
              </div>
              <div className="flex justify-between text-gray-500">
                <span>Detected Rooms:</span>
                <span className="text-gray-300 font-mono">{rooms.length}</span>
              </div>
            </div>

            {/* Save to server button */}
            <button
              onClick={handleSaveToServer}
              disabled={isSaving}
              className="w-full mt-2 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-semibold flex items-center justify-center gap-2 shadow-[0_4px_12px_rgba(37,99,235,0.2)] transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isSaving ? (
                <>
                  <span className="animate-spin h-3.5 w-3.5 border-2 border-white border-t-transparent rounded-full" />
                  <span>Saving Model...</span>
                </>
              ) : (
                <>
                  <Save className="h-4 w-4" />
                  <span>Update CAD Files</span>
                </>
              )}
            </button>

            <div className="border-b border-gray-800 pb-2 mt-4">
              <span className="text-xs font-bold text-white uppercase tracking-wider">Export Deliverables</span>
            </div>

            <div className="flex flex-col gap-2">
              <button
                onClick={() => handleDownloadFile('json')}
                disabled={!projectId || downloadingFormat !== null}
                className={`py-2 px-3 rounded-xl border border-gray-800 hover:border-gray-700 bg-gray-950/40 hover:bg-gray-950/80 transition-all flex items-center justify-between text-gray-300 hover:text-white w-full text-left cursor-pointer ${(!projectId || downloadingFormat !== null) && 'pointer-events-none opacity-50'}`}
              >
                <div className="flex items-center gap-2">
                  <FileJson className="h-4 w-4 text-blue-400" />
                  <span>Structured JSON</span>
                </div>
                {downloadingFormat === 'json' ? (
                  <span className="animate-spin h-3.5 w-3.5 border-2 border-blue-400 border-t-transparent rounded-full" />
                ) : (
                  <Download className="h-3.5 w-3.5 text-gray-500" />
                )}
              </button>

              <button
                onClick={() => handleDownloadFile('dxf')}
                disabled={!projectId || downloadingFormat !== null}
                className={`py-2 px-3 rounded-xl border border-gray-800 hover:border-gray-700 bg-gray-950/40 hover:bg-gray-950/80 transition-all flex items-center justify-between text-gray-300 hover:text-white w-full text-left cursor-pointer ${(!projectId || downloadingFormat !== null) && 'pointer-events-none opacity-50'}`}
              >
                <div className="flex items-center gap-2">
                  <FolderOpen className="h-4 w-4 text-accent-amber" />
                  <span>AutoCAD DXF</span>
                </div>
                {downloadingFormat === 'dxf' ? (
                  <span className="animate-spin h-3.5 w-3.5 border-2 border-amber-400 border-t-transparent rounded-full" />
                ) : (
                  <Download className="h-3.5 w-3.5 text-gray-500" />
                )}
              </button>

              <button
                onClick={() => handleDownloadFile('dwg')}
                disabled={!projectId || downloadingFormat !== null}
                className={`py-2 px-3 rounded-xl border border-gray-800 hover:border-gray-700 bg-gray-950/40 hover:bg-gray-950/80 transition-all flex items-center justify-between text-gray-300 hover:text-white w-full text-left cursor-pointer ${(!projectId || downloadingFormat !== null) && 'pointer-events-none opacity-50'}`}
              >
                <div className="flex items-center gap-2">
                  <Layers className="h-4 w-4 text-accent-emerald" />
                  <span>AutoCAD DWG</span>
                </div>
                {downloadingFormat === 'dwg' ? (
                  <span className="animate-spin h-3.5 w-3.5 border-2 border-emerald-400 border-t-transparent rounded-full" />
                ) : (
                  <Download className="h-3.5 w-3.5 text-gray-500" />
                )}
              </button>
              <p className="text-[9px] text-gray-500 px-1 -mt-1 leading-normal">
                * DWG files are converted via ODA converter logic.
              </p>
            </div>
            
            {/* SketchUp Ruby Extension Exporter */}
            <div className="border-b border-gray-800 pb-2 mt-4">
              <span className="text-xs font-bold text-white uppercase tracking-wider">SketchUp Integration</span>
            </div>
            
            <div className="p-3 bg-blue-500/5 rounded-xl border border-blue-500/10 flex flex-col gap-2">
              <div className="flex items-center gap-2 text-white font-semibold">
                <Code className="h-4 w-4 text-blue-400" />
                <span>Ruby Plugin Exporter</span>
              </div>
              <p className="text-[10px] text-gray-400 leading-relaxed">
                Install this exporter inside SketchUp to export complex, hierarchical building structures with 100% precision.
              </p>
              <button
                onClick={handleDownloadScript}
                className="w-full py-1.5 rounded-lg bg-blue-500/10 hover:bg-blue-500/20 text-blue-400 font-semibold transition-colors flex items-center justify-center gap-1.5 text-[10px] border border-blue-500/20"
              >
                <DownloadCloud className="h-3.5 w-3.5" />
                <span>Get SketchUp Exporter (.rb)</span>
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
