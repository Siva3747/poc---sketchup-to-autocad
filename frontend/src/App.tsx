import React, { useEffect, useState } from 'react'
import {
  Cpu, Upload, HelpCircle, FolderLock, Clock, ChevronRight,
  RefreshCcw, AlertCircle, Brain, CheckCircle, Trash2
} from 'lucide-react'
import { UploadZone } from './components/UploadZone'
import { Toolbar } from './components/Toolbar'
import { LayerPanel } from './components/LayerPanel'
import { StatusBar } from './components/StatusBar'
import { EditorSidebar } from './components/EditorSidebar'
import { AIReviewPanel } from './components/AIReviewPanel'
import { ViewToggle } from './components/ViewToggle'
import { FloorPlanViewer } from './viewer/FloorPlanViewer'
import { Viewer3D } from './viewer/Viewer3D'
import { useViewerStore, Point } from './store/viewerStore'
import { apiService, ProjectListResponse } from './services/api'

const FORMAT_BADGE: Record<string, string> = {
  skp: 'bg-blue-500/10 text-blue-400 border-blue-500/10',
  dxf: 'bg-amber-500/10 text-amber-400 border-amber-500/10',
  dwg: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/10',
  json: 'bg-purple-500/10 text-purple-400 border-purple-500/10',
}

const App: React.FC = () => {
  const [activeProjectId, setActiveProjectId] = useState<string | null>(null)
  const [cursorPos, setCursorPos] = useState<Point | null>(null)
  const [snapActive, setSnapActive] = useState(false)
  const [projectsList, setProjectsList] = useState<ProjectListResponse[]>([])
  const [loadingList, setLoadingList] = useState(false)

  const {
    setProject, isLoading, setLoading, error, setError,
    setAiData, viewMode, hasAi,
  } = useViewerStore()

  const fetchProjects = async () => {
    setLoadingList(true)
    try { setProjectsList(await apiService.listProjects()) }
    catch { /* ignore */ }
    finally { setLoadingList(false) }
  }

  useEffect(() => { if (!activeProjectId) fetchProjects() }, [activeProjectId])

  const handleLoadProject = async (id: string, name: string) => {
    setLoading(true); setError(null); setActiveProjectId(id)
    try {
      const data = await apiService.getProjectData(id)
      setProject(id, name, data.floorplan, data.source_format)
      setAiData(data.ai_detections ?? [], data.ai_metadata ?? null)
    } catch (err: any) {
      setError(err.response?.data?.detail ?? 'Failed to load project.')
    } finally { setLoading(false) }
  }

  const handleUploadSuccess = (projectId: string) => {
    handleLoadProject(projectId, 'Processing Model…')
  }

  const handleClearHistory = async () => {
    if (!projectsList.length || !window.confirm('Delete all conversion history and generated files? This cannot be undone.')) return
    setLoadingList(true)
    try {
      await apiService.clearProjects()
      setProjectsList([])
    } catch {
      setError('Could not delete conversion history. Please try again.')
    } finally {
      setLoadingList(false)
    }
  }

  return (
    <div className="h-full w-full flex flex-col select-none overflow-hidden text-gray-200">
      {/* ── Top navbar ── */}
      <header className="h-14 border-b border-gray-900 bg-[#0d0e12]/80 backdrop-blur-md flex items-center justify-between px-6 z-30 shrink-0">
        <div className="flex items-center gap-3">
          <div className="h-8 w-8 rounded-lg bg-blue-600 flex items-center justify-center shadow-[0_0_15px_rgba(37,99,235,0.4)]">
            <Cpu className="h-5 w-5 text-white" />
          </div>
          <div>
            <h1 className="text-sm font-extrabold text-white tracking-wider uppercase font-display">CAD AI Converter</h1>
            <p className="text-[9px] text-gray-500 font-medium tracking-widest uppercase -mt-0.5">
              SKP · DXF · DWG · JSON ↔ Canonical Pipeline
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {activeProjectId && <ViewToggle />}
          {activeProjectId && (
            <button onClick={() => setActiveProjectId(null)}
              className="text-xs px-3.5 py-1.5 rounded-xl border border-gray-800 hover:border-gray-700 bg-gray-950/40 hover:bg-gray-950/80 transition-colors">
              Dashboard
            </button>
          )}
          <a href="https://github.com" target="_blank" rel="noreferrer"
            className="h-8 w-8 rounded-full border border-gray-800 flex items-center justify-center hover:bg-gray-800/30 transition-colors text-gray-400 hover:text-white">
            <HelpCircle className="h-4 w-4" />
          </a>
        </div>
      </header>

      {/* ── Content area ── */}
      {!activeProjectId ? (
        /* Dashboard */
        <div className="flex-1 w-full overflow-y-auto px-6 py-10 flex flex-col items-center">
          <div className="text-center max-w-2xl mb-12">
            <span className="text-xs font-bold text-blue-500 uppercase tracking-widest bg-blue-500/10 px-3.5 py-1 rounded-full border border-blue-500/10">
              AI-Powered CAD Pipeline
            </span>
            <h2 className="text-3xl md:text-4xl font-extrabold text-white tracking-tight font-display mt-4 mb-4">
              Convert, Detect, Edit & Export
            </h2>
            <p className="text-sm text-gray-400 leading-relaxed">
              Upload SKP, DXF, DWG, or JSON — the AI pipeline extracts architecture,
              classifies elements with confidence scores, and lets you export back to any format.
            </p>
          </div>

          {/* Feature pills */}
          <div className="flex flex-wrap gap-2 justify-center mb-10">
            {['AI Detection', '2D Floor Plan', '3D Viewer', 'DXF Export', 'DWG Export', 'SKP Script', 'Undo / Redo', 'Layer Control'].map(f => (
              <span key={f} className="text-[10px] font-bold px-3 py-1 rounded-full border border-gray-800 text-gray-400 bg-gray-950/40">{f}</span>
            ))}
          </div>

          <div className="w-full max-w-5xl grid grid-cols-1 md:grid-cols-2 gap-8 items-start">
            {/* Uploader */}
            <div className="flex justify-center md:sticky md:top-4">
              <UploadZone onUploadSuccess={handleUploadSuccess} />
            </div>

            {/* Recent projects */}
            <div className="flex flex-col gap-4 bg-[#0d0e12] border border-gray-900/60 rounded-2xl p-5 h-[400px] overflow-hidden">
              <div className="flex items-center justify-between border-b border-gray-800/60 pb-3 mb-2">
                <div className="flex items-center gap-2 text-white font-bold text-xs uppercase tracking-wider">
                  <Clock className="h-4 w-4 text-blue-400" />
                  <span>Recent Conversions</span>
                </div>
                <div className="flex items-center gap-1">
                  <button onClick={handleClearHistory} disabled={!projectsList.length || loadingList}
                    title="Clear conversion history"
                    className="text-gray-500 hover:text-rose-400 disabled:opacity-30 disabled:hover:text-gray-500 transition-colors p-1">
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                  <button onClick={fetchProjects} title="Refresh history" className="text-gray-500 hover:text-blue-400 transition-colors p-1">
                    <RefreshCcw className={`h-3.5 w-3.5 ${loadingList ? 'animate-spin' : ''}`} />
                  </button>
                </div>
              </div>

              <div className="flex-1 overflow-y-auto flex flex-col gap-2 pr-1">
                {loadingList && !projectsList.length ? (
                  <div className="h-full flex items-center justify-center text-gray-500 text-xs">
                    <span className="animate-spin h-4 w-4 border-2 border-blue-500 border-t-transparent rounded-full mr-2" />
                    Loading…
                  </div>
                ) : !projectsList.length ? (
                  <div className="h-full flex flex-col items-center justify-center text-gray-600 text-xs text-center p-6 border border-dashed border-gray-900 rounded-xl">
                    <FolderLock className="h-8 w-8 text-gray-700 mb-2" />
                    <span>No models yet.</span>
                    <span className="text-[10px] text-gray-600 mt-1">Upload a file above to start.</span>
                  </div>
                ) : projectsList.map(proj => (
                  <button key={proj.id} onClick={() => handleLoadProject(proj.id, proj.filename)}
                    className="w-full text-left p-3 rounded-xl bg-gray-950/20 hover:bg-gray-950/60 border border-gray-900 hover:border-gray-800 transition-all flex items-center justify-between group">
                    <div className="flex flex-col gap-1 min-w-0 pr-2">
                      <span className="text-xs font-semibold text-gray-200 group-hover:text-white truncate">{proj.filename}</span>
                      <div className="flex items-center gap-2 text-[9px] text-gray-500">
                        <span>{new Date(proj.created_at).toLocaleDateString()}</span>
                        <span>·</span>
                        <span className={`font-semibold ${
                          proj.status === 'COMPLETED' ? 'text-emerald-400' :
                          proj.status === 'FAILED' ? 'text-rose-400' : 'text-amber-400 animate-pulse'
                        }`}>{proj.status}</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-1 shrink-0">
                      <span className={`text-[8px] font-bold px-1.5 py-0.5 rounded border ${FORMAT_BADGE[proj.source_format] ?? FORMAT_BADGE.json} uppercase`}>{proj.source_format}</span>
                      {proj.has_dxf && <span className="text-[8px] font-bold px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/10">DXF</span>}
                      {proj.has_dwg && <span className="text-[8px] font-bold px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/10">DWG</span>}
                      {proj.has_ai && <Brain className="h-3 w-3 text-purple-400" title="AI detected" />}
                      <ChevronRight className="h-4 w-4 text-gray-600 group-hover:text-gray-400 group-hover:translate-x-0.5 transition-all" />
                    </div>
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      ) : (
        /* Editor */
        <div className="flex-1 w-full flex overflow-hidden relative">
          {/* Loading overlay */}
          {isLoading && (
            <div className="absolute inset-0 bg-[#0d0e12] z-50 flex flex-col items-center justify-center">
              <span className="animate-spin h-10 w-10 border-4 border-blue-500 border-t-transparent rounded-full mb-4" />
              <h3 className="text-sm font-semibold text-white">Reconstructing CAD Workspace</h3>
              <p className="text-xs text-gray-500 mt-1">Running AI pipeline and rendering floor plan…</p>
            </div>
          )}

          {/* Error overlay */}
          {error && !isLoading && (
            <div className="absolute inset-0 bg-[#0d0e12] z-50 flex flex-col items-center justify-center p-6">
              <AlertCircle className="h-12 w-12 text-rose-500 mb-4 animate-bounce" />
              <h3 className="text-lg font-bold text-white">Error</h3>
              <p className="text-xs text-gray-400 max-w-sm text-center mt-2 mb-6">{error}</p>
              <button onClick={() => setActiveProjectId(null)}
                className="px-5 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold shadow-lg transition-colors">
                Return to Dashboard
              </button>
            </div>
          )}

          {/* 2D view */}
          {viewMode === '2d' && (
            <>
              <Toolbar />
              <LayerPanel />
              <StatusBar cursorPos={cursorPos} snapActive={snapActive} />
              <div className="flex-1 h-full">
                <FloorPlanViewer onCursorChange={setCursorPos} onSnapChange={setSnapActive} />
              </div>
            </>
          )}

          {/* 3D view */}
          {viewMode === '3d' && (
            <div className="flex-1 h-full">
              <Viewer3D />
            </div>
          )}

          {/* AI Review view */}
          {viewMode === 'ai' && (
            <div className="flex-1 h-full flex overflow-hidden">
              {/* AI review shows 2D canvas with AI overlay + review panel */}
              <div className="flex-1 h-full relative">
                <Toolbar />
                <StatusBar cursorPos={cursorPos} snapActive={snapActive} />
                <FloorPlanViewer onCursorChange={setCursorPos} onSnapChange={setSnapActive} />
              </div>
              {/* AI Review side panel */}
              <div className="w-72 h-full overflow-y-auto border-l border-gray-900 bg-[#0d0e12] p-3 flex flex-col gap-3">
                <h3 className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-2">
                  <Brain className="h-4 w-4 text-purple-400" />AI Detection Review
                </h3>
                <AIReviewPanel />
              </div>
            </div>
          )}

          {/* Right sidebar — always visible */}
          <EditorSidebar onBackToUpload={() => setActiveProjectId(null)} />
        </div>
      )}
    </div>
  )
}

export default App
