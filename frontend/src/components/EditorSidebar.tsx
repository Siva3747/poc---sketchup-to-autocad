import React, { useEffect, useState } from 'react'
import {
  Save, Download, FileJson, PenTool, DownloadCloud,
  Layers, Maximize, FolderOpen, ArrowLeft, ChevronRight, Code, FileCode2
} from 'lucide-react'
import { useViewerStore, Wall, Door, Window, Room } from '../store/viewerStore'
import { apiService } from '../services/api'

interface EditorSidebarProps {
  onBackToUpload: () => void
}

export const EditorSidebar: React.FC<EditorSidebarProps> = ({ onBackToUpload }) => {
  const {
    projectId, filename, sourceFormat, metadata,
    walls, doors, windows, rooms,
    selectedId, selectElement,
    updateWall, updateDoor, updateWindow, deleteElement,
    isSaving, setSaving, setError, setProject, setAiData,
  } = useViewerStore()

  const [wallThickness, setWallThickness] = useState('')
  const [wallHeight, setWallHeight] = useState('')
  const [doorWidth, setDoorWidth] = useState('')
  const [doorHeight, setDoorHeight] = useState('')
  const [windowWidth, setWindowWidth] = useState('')
  const [windowHeight, setWindowHeight] = useState('')
  const [windowElevation, setWindowElevation] = useState('')
  const [roomName, setRoomName] = useState('')
  const [downloadingFormat, setDownloadingFormat] = useState<string | null>(null)

  const selectedWall = walls.find(w => w.id === selectedId)
  const selectedDoor = doors.find(d => d.id === selectedId)
  const selectedWindow = windows.find(w => w.id === selectedId)
  const selectedRoom = rooms.find(r => r.id === selectedId)

  useEffect(() => {
    if (selectedWall) { setWallThickness(selectedWall.thickness.toString()); setWallHeight(selectedWall.height.toString()) }
    else if (selectedDoor) { setDoorWidth(selectedDoor.width.toString()); setDoorHeight(selectedDoor.height.toString()) }
    else if (selectedWindow) { setWindowWidth(selectedWindow.width.toString()); setWindowHeight(selectedWindow.height.toString()); setWindowElevation(selectedWindow.elevation.toString()) }
    else if (selectedRoom) setRoomName(selectedRoom.name)
  }, [selectedId, selectedWall, selectedDoor, selectedWindow, selectedRoom])

  const handleSaveToServer = async () => {
    if (!projectId) return
    setSaving(true); setError(null)
    try {
      await apiService.updateProjectData(projectId, { metadata, walls, doors, windows, rooms })
      const fresh = await apiService.getProjectData(projectId)
      setProject(projectId, filename, fresh.floorplan, fresh.source_format)
      setAiData(fresh.ai_detections, fresh.ai_metadata)
    } catch {
      setError('Failed to save changes and regenerate CAD files.')
    } finally { setSaving(false) }
  }

  const handleDownload = async (format: 'json' | 'dxf' | 'dwg' | 'skp') => {
    if (!projectId) return
    setDownloadingFormat(format)
    try {
      const { data, filename: dl } = await apiService.downloadProjectFile(projectId, format)
      const url = URL.createObjectURL(new Blob([data]))
      const a = document.createElement('a')
      a.href = url
      a.download = dl || `project.${format === 'skp' ? 'rb' : format}`
      document.body.appendChild(a); a.click()
      document.body.removeChild(a); URL.revokeObjectURL(url)
    } catch { alert(`Failed to download ${format.toUpperCase()}.`) }
    finally { setDownloadingFormat(null) }
  }

  const handleDownloadRubyExporter = async () => {
    try {
      const txt = await apiService.getSketchUpExporterScript()
      const url = URL.createObjectURL(new Blob([txt], { type: 'text/plain' }))
      const a = document.createElement('a')
      a.href = url; a.download = 'sketchup_json_exporter.rb'
      document.body.appendChild(a); a.click()
      document.body.removeChild(a); URL.revokeObjectURL(url)
    } catch { alert('Failed to download exporter script.') }
  }

  const dlBtn = (fmt: 'json' | 'dxf' | 'dwg' | 'skp', label: string, icon: React.ReactNode, color: string) => (
    <button
      onClick={() => handleDownload(fmt)}
      disabled={!projectId || downloadingFormat !== null}
      className="py-2 px-3 rounded-xl border border-gray-800 hover:border-gray-700 bg-gray-950/40 hover:bg-gray-950/80 transition-all flex items-center justify-between text-gray-300 hover:text-white w-full disabled:opacity-50 disabled:pointer-events-none"
    >
      <div className="flex items-center gap-2">{icon}<span>{label}</span></div>
      {downloadingFormat === fmt
        ? <span className={`animate-spin h-3.5 w-3.5 border-2 ${color} border-t-transparent rounded-full`} />
        : <Download className="h-3.5 w-3.5 text-gray-500" />}
    </button>
  )

  return (
    <div className="w-80 h-full bg-[#0d0e12] border-l border-gray-800/80 flex flex-col justify-between shrink-0 z-10 text-xs">
      {/* Header */}
      <div className="p-4 border-b border-gray-800/80">
        <button onClick={onBackToUpload} className="flex items-center gap-1.5 text-gray-400 hover:text-white transition-colors mb-4 group">
          <ArrowLeft className="h-3.5 w-3.5 group-hover:-translate-x-0.5 transition-transform" />
          <span>Back to Dashboard</span>
        </button>
        <h2 className="text-sm font-bold text-white tracking-wide truncate" title={filename}>{filename}</h2>
        <div className="flex items-center gap-2 mt-1">
          <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/10 uppercase">{sourceFormat}</span>
          <span className="text-[10px] text-gray-500 font-mono">ID: {projectId?.substring(0, 8)}…</span>
        </div>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-4">
        {selectedId ? (
          <div>
            <div className="flex items-center justify-between border-b border-gray-800 pb-2 mb-3">
              <span className="text-xs font-bold text-white uppercase tracking-wider">Object Inspector</span>
              <button onClick={() => selectElement(null)} className="text-[10px] text-blue-400 hover:underline">Clear</button>
            </div>

            {/* Wall */}
            {selectedWall && (
              <div className="flex flex-col gap-3">
                <div className="flex items-center gap-2 text-white font-semibold"><PenTool className="h-4 w-4 text-blue-400" /><span>Wall</span></div>
                <div className="text-[10px] text-gray-500 font-mono">{selectedWall.id}</div>
                {[['Thickness', wallThickness, setWallThickness], ['Height', wallHeight, setWallHeight]].map(([lbl, val, setter]) => (
                  <div key={lbl as string} className="flex flex-col gap-1.5">
                    <label className="text-gray-400">{lbl as string} ({metadata.unit})</label>
                    <input type="number" value={val as string} onChange={e => (setter as any)(e.target.value)}
                      onBlur={() => updateWall(selectedWall.id, { thickness: parseFloat(wallThickness) || selectedWall.thickness, height: parseFloat(wallHeight) || selectedWall.height })}
                      className="px-2.5 py-1.5 rounded-lg bg-gray-900 border border-gray-800 text-white" />
                  </div>
                ))}
                <div className="p-3 bg-gray-950/40 rounded-xl border border-gray-900 flex flex-col gap-1.5 text-[11px] mt-1">
                  <div className="flex justify-between text-gray-500"><span>Length:</span><span className="text-white font-mono">{(Math.hypot(selectedWall.end.x-selectedWall.start.x, selectedWall.end.y-selectedWall.start.y)/1000).toFixed(2)} m</span></div>
                  <div className="flex justify-between text-gray-500"><span>Start:</span><span className="text-gray-300 font-mono">({Math.round(selectedWall.start.x)}, {Math.round(selectedWall.start.y)})</span></div>
                  <div className="flex justify-between text-gray-500"><span>End:</span><span className="text-gray-300 font-mono">({Math.round(selectedWall.end.x)}, {Math.round(selectedWall.end.y)})</span></div>
                </div>
              </div>
            )}

            {/* Door */}
            {selectedDoor && (
              <div className="flex flex-col gap-3">
                <div className="flex items-center gap-2 text-white font-semibold"><ChevronRight className="h-4 w-4 text-red-400" /><span>Door</span></div>
                <div className="text-[10px] text-gray-500 font-mono">{selectedDoor.id}</div>
                {[['Width', doorWidth, setDoorWidth, 'width'], ['Height', doorHeight, setDoorHeight, 'height']].map(([lbl, val, setter, field]) => (
                  <div key={field as string} className="flex flex-col gap-1.5">
                    <label className="text-gray-400">{lbl as string} ({metadata.unit})</label>
                    <input type="number" value={val as string} onChange={e => (setter as any)(e.target.value)}
                      onBlur={() => updateDoor(selectedDoor.id, { [field as string]: parseFloat(val as string) || selectedDoor[field as keyof Door] })}
                      className="px-2.5 py-1.5 rounded-lg bg-gray-900 border border-gray-800 text-white" />
                  </div>
                ))}
                <div className="flex gap-2">
                  {(['left','right'] as const).map(h => (
                    <button key={h} onClick={() => updateDoor(selectedDoor.id, { hand: h })}
                      className={`flex-1 py-1 rounded-lg text-xs font-bold border transition-colors ${selectedDoor.hand===h ? 'bg-blue-600 border-blue-600 text-white' : 'border-gray-800 text-gray-500 hover:text-white'}`}>
                      {h === 'left' ? 'LH' : 'RH'}
                    </button>
                  ))}
                  {(['in','out'] as const).map(d => (
                    <button key={d} onClick={() => updateDoor(selectedDoor.id, { direction: d })}
                      className={`flex-1 py-1 rounded-lg text-xs font-bold border transition-colors ${selectedDoor.direction===d ? 'bg-blue-600 border-blue-600 text-white' : 'border-gray-800 text-gray-500 hover:text-white'}`}>
                      {d.toUpperCase()}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Window */}
            {selectedWindow && (
              <div className="flex flex-col gap-3">
                <div className="flex items-center gap-2 text-white font-semibold"><Maximize className="h-4 w-4 text-cyan-400" /><span>Window</span></div>
                <div className="text-[10px] text-gray-500 font-mono">{selectedWindow.id}</div>
                {[['Width', windowWidth, setWindowWidth], ['Height', windowHeight, setWindowHeight], ['Sill Elevation', windowElevation, setWindowElevation]].map(([lbl, val, setter]) => (
                  <div key={lbl as string} className="flex flex-col gap-1.5">
                    <label className="text-gray-400">{lbl as string} ({metadata.unit})</label>
                    <input type="number" value={val as string} onChange={e => (setter as any)(e.target.value)}
                      onBlur={() => updateWindow(selectedWindow.id, { width: parseFloat(windowWidth)||selectedWindow.width, height: parseFloat(windowHeight)||selectedWindow.height, elevation: parseFloat(windowElevation)||selectedWindow.elevation })}
                      className="px-2.5 py-1.5 rounded-lg bg-gray-900 border border-gray-800 text-white" />
                  </div>
                ))}
              </div>
            )}

            {/* Room */}
            {selectedRoom && (
              <div className="flex flex-col gap-3">
                <div className="flex items-center gap-2 text-white font-semibold"><Layers className="h-4 w-4 text-amber-400" /><span>Room</span></div>
                <div className="flex flex-col gap-1.5">
                  <label className="text-gray-400">Name</label>
                  <input type="text" value={roomName} onChange={e => setRoomName(e.target.value)}
                    onBlur={() => useViewerStore.setState(s => ({ rooms: s.rooms.map(r => r.id === selectedRoom.id ? { ...r, name: roomName } : r) }))}
                    className="px-2.5 py-1.5 rounded-lg bg-gray-900 border border-gray-800 text-white" />
                </div>
                <div className="p-3 bg-amber-500/5 rounded-xl border border-amber-500/10 flex justify-between">
                  <span className="text-gray-400">Area:</span>
                  <span className="text-amber-400 font-bold font-mono">{selectedRoom.area.toFixed(2)} m²</span>
                </div>
              </div>
            )}

            <button onClick={() => deleteElement(selectedId)}
              className="mt-6 w-full py-2 rounded-xl bg-rose-500/10 hover:bg-rose-500/20 text-rose-500 font-semibold border border-rose-500/20 transition-all">
              Remove Element
            </button>
          </div>
        ) : (
          <div className="flex flex-col gap-4">
            {/* Metadata */}
            <div className="border-b border-gray-800 pb-2">
              <span className="text-xs font-bold text-white uppercase tracking-wider">Model Stats</span>
            </div>
            <div className="flex flex-col gap-1.5">
              {[['Model', metadata.name], ['Source', sourceFormat.toUpperCase()], ['Unit', metadata.unit], ['Walls', walls.length], ['Openings', doors.length + windows.length], ['Rooms', rooms.length]].map(([k, v]) => (
                <div key={k as string} className="flex justify-between text-gray-500">
                  <span>{k as string}:</span><span className="text-gray-300 font-mono">{v as string}</span>
                </div>
              ))}
            </div>

            {/* Save */}
            <button onClick={handleSaveToServer} disabled={isSaving}
              className="w-full mt-2 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-semibold flex items-center justify-center gap-2 shadow-lg transition-all disabled:opacity-50">
              {isSaving ? <><span className="animate-spin h-3.5 w-3.5 border-2 border-white border-t-transparent rounded-full" /><span>Saving…</span></> : <><Save className="h-4 w-4" /><span>Save & Regenerate</span></>}
            </button>

            {/* Exports */}
            <div className="border-b border-gray-800 pb-2 mt-2">
              <span className="text-xs font-bold text-white uppercase tracking-wider">Export</span>
            </div>
            <div className="flex flex-col gap-2">
              {dlBtn('json', 'Canonical JSON', <FileJson className="h-4 w-4 text-purple-400" />, 'border-purple-400')}
              {dlBtn('dxf', 'AutoCAD DXF', <FolderOpen className="h-4 w-4 text-amber-400" />, 'border-amber-400')}
              {dlBtn('dwg', 'AutoCAD DWG', <Layers className="h-4 w-4 text-emerald-400" />, 'border-emerald-400')}
              {dlBtn('skp', 'SketchUp Script (.rb)', <FileCode2 className="h-4 w-4 text-blue-400" />, 'border-blue-400')}
              <p className="text-[9px] text-gray-600 px-1 leading-normal">
                .rb = Ruby reconstruction script. Open in SketchUp's Ruby Console to rebuild the model.
              </p>
            </div>

            {/* SketchUp Plugin */}
            <div className="border-b border-gray-800 pb-2 mt-2">
              <span className="text-xs font-bold text-white uppercase tracking-wider">SketchUp Plugin</span>
            </div>
            <div className="p-3 bg-blue-500/5 rounded-xl border border-blue-500/10 flex flex-col gap-2">
              <div className="flex items-center gap-2 text-white font-semibold"><Code className="h-4 w-4 text-blue-400" /><span>Ruby Exporter</span></div>
              <p className="text-[10px] text-gray-400 leading-relaxed">Export complex SketchUp models with full geometry precision.</p>
              <button onClick={handleDownloadRubyExporter}
                className="w-full py-1.5 rounded-lg bg-blue-500/10 hover:bg-blue-500/20 text-blue-400 font-semibold transition-colors flex items-center justify-center gap-1.5 text-[10px] border border-blue-500/20">
                <DownloadCloud className="h-3.5 w-3.5" />Get Plugin (.rb)
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
