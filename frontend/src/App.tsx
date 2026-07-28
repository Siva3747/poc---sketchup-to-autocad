import React, { useEffect, useState } from 'react'
import { 
  Building2, 
  Upload, 
  HelpCircle, 
  FolderLock, 
  Clock, 
  ChevronRight, 
  RefreshCcw,
  CheckCircle,
  AlertCircle
} from 'lucide-react'
import { UploadZone } from './components/UploadZone'
import { Toolbar } from './components/Toolbar'
import { LayerPanel } from './components/LayerPanel'
import { StatusBar } from './components/StatusBar'
import { EditorSidebar } from './components/EditorSidebar'
import { FloorPlanViewer } from './viewer/FloorPlanViewer'
import { useViewerStore, Point } from './store/viewerStore'
import { apiService, ProjectListResponse } from './services/api'

const App: React.FC = () => {
  const [activeProjectId, setActiveProjectId] = useState<string | null>(null)
  const [cursorPos, setCursorPos] = useState<Point | null>(null)
  const [snapActive, setSnapActive] = useState<boolean>(false)
  const [projectsList, setProjectsList] = useState<ProjectListResponse[]>([])
  const [loadingList, setLoadingList] = useState<boolean>(false)

  const { 
    setProject, 
    isLoading, 
    setLoading, 
    error, 
    setError 
  } = useViewerStore()

  // Fetch recent projects list for dashboard
  const fetchProjects = async () => {
    setLoadingList(true)
    try {
      const data = await apiService.listProjects()
      setProjectsList(data)
    } catch (err) {
      console.error("Failed to load projects list", err)
    } finally {
      setLoadingList(false)
    }
  }

  useEffect(() => {
    if (!activeProjectId) {
      fetchProjects()
    }
  }, [activeProjectId])

  // Load a project into Zustand and activate editor
  const handleLoadProject = async (id: string, name: string) => {
    setLoading(true)
    setError(null)
    setActiveProjectId(id)
    try {
      const data = await apiService.getProjectData(id)
      setProject(id, name, data.floorplan)
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to load project details.")
    } finally {
      setLoading(false)
    }
  }

  // Triggered after successful file upload
  const handleUploadSuccess = (projectId: string) => {
    // Find project filename from list or default to uploaded
    handleLoadProject(projectId, "Processing Model...")
  }

  const handleBackToUpload = () => {
    setActiveProjectId(null)
  }

  return (
    <div className="h-full w-full flex flex-col select-none overflow-hidden text-gray-200">
      
      {/* 1. TOP NAVBAR */}
      <header className="h-14 border-b border-gray-900 bg-card/60 backdrop-blur-md flex items-center justify-between px-6 z-30 shrink-0">
        <div className="flex items-center gap-3">
          <div className="h-8 w-8 rounded-lg bg-blue-600 flex items-center justify-center shadow-[0_0_15px_rgba(37,99,235,0.4)]">
            <Building2 className="h-5 w-5 text-white" />
          </div>
          <div>
            <h1 className="text-sm font-extrabold text-white tracking-wider uppercase font-display">
              SketchUp CAD Pipeline
            </h1>
            <p className="text-[9px] text-gray-500 font-medium tracking-widest uppercase -mt-0.5">
              SKP ➔ JSON ➔ DXF/DWG engine
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {activeProjectId && (
            <button
              onClick={handleBackToUpload}
              className="text-xs px-3.5 py-1.5 rounded-xl border border-gray-800 hover:border-gray-700 bg-gray-950/40 hover:bg-gray-950/80 transition-colors"
            >
              Back to Dashboard
            </button>
          )}
          <a
            href="https://github.com/iamahsanmehmood/openskp"
            target="_blank"
            rel="noreferrer"
            className="h-8 w-8 rounded-full border border-gray-800 flex items-center justify-center hover:bg-gray-800/30 transition-colors text-gray-400 hover:text-white"
            title="Help & documentation"
          >
            <HelpCircle className="h-4 w-4" />
          </a>
        </div>
      </header>

      {/* 2. DYNAMIC CONTENT AREA */}
      {!activeProjectId ? (
        
        /* DASHBOARD & UPLOAD VIEW */
        <div className="flex-1 w-full overflow-y-auto px-6 py-10 flex flex-col items-center">
          
          {/* Headline */}
          <div className="text-center max-w-2xl mb-12">
            <span className="text-xs font-bold text-blue-500 uppercase tracking-widest bg-blue-500/10 px-3.5 py-1 rounded-full border border-blue-500/10">
              CAD Engineering Console
            </span>
            <h2 className="text-3xl md:text-4xl font-extrabold text-white tracking-tight font-display mt-4 mb-4">
              Convert SketchUp into CAD Deliverables
            </h2>
            <p className="text-sm text-gray-400 leading-relaxed">
              Upload your SketchUp project. Our geometric engine detects building structures, segments rooms, labels centerlines, and outputs production-grade DXF and DWG formats instantly.
            </p>
          </div>

          <div className="w-full max-w-5xl grid grid-cols-1 md:grid-cols-2 gap-8 items-start">
            {/* Uploader Box */}
            <div className="flex justify-center md:sticky md:top-4">
              <UploadZone onUploadSuccess={handleUploadSuccess} />
            </div>

            {/* Recent Conversions list */}
            <div className="flex flex-col gap-4 bg-card/40 border border-gray-900/60 rounded-2xl p-5 h-[400px] overflow-hidden flex-1">
              <div className="flex items-center justify-between border-b border-gray-800/60 pb-3 mb-2">
                <div className="flex items-center gap-2 text-white font-bold text-xs uppercase tracking-wider">
                  <Clock className="h-4 w-4 text-blue-400" />
                  <span>Recent Conversions</span>
                </div>
                <button
                  onClick={fetchProjects}
                  className="text-gray-500 hover:text-blue-400 transition-colors p-1"
                  title="Refresh Projects"
                >
                  <RefreshCcw className={`h-3.5 w-3.5 ${loadingList && 'animate-spin'}`} />
                </button>
              </div>

              <div className="flex-1 overflow-y-auto flex flex-col gap-2 pr-1">
                {loadingList && projectsList.length === 0 ? (
                  <div className="h-full flex items-center justify-center text-gray-500 text-xs">
                    <span className="animate-spin h-4 w-4 border-2 border-blue-500 border-t-transparent rounded-full mr-2" />
                    Loading recent projects...
                  </div>
                ) : projectsList.length === 0 ? (
                  <div className="h-full flex flex-col items-center justify-center text-gray-600 text-xs text-center p-6 border border-dashed border-gray-900 rounded-xl">
                    <FolderLock className="h-8 w-8 text-gray-700 mb-2" />
                    <span>No models processed yet.</span>
                    <span className="text-[10px] text-gray-600 mt-1">Upload a SketchUp (.skp) file to begin.</span>
                  </div>
                ) : (
                  projectsList.map((proj) => (
                    <button
                      key={proj.id}
                      onClick={() => handleLoadProject(proj.id, proj.filename)}
                      className="w-full text-left p-3 rounded-xl bg-gray-950/20 hover:bg-gray-950/60 border border-gray-900 hover:border-gray-800 transition-all duration-200 flex items-center justify-between group"
                    >
                      <div className="flex flex-col gap-1 min-w-0 pr-2">
                        <span className="text-xs font-semibold text-gray-200 group-hover:text-white truncate">
                          {proj.filename}
                        </span>
                        <div className="flex items-center gap-2 text-[9px] text-gray-500">
                          <span>{new Date(proj.created_at).toLocaleDateString()}</span>
                          <span>•</span>
                          <span className={`font-semibold ${
                            proj.status === 'COMPLETED' ? 'text-accent-emerald' : 
                            proj.status === 'FAILED' ? 'text-accent-rose' : 'text-accent-amber animate-pulse'
                          }`}>
                            {proj.status}
                          </span>
                        </div>
                      </div>
                      <div className="flex items-center gap-1 shrink-0">
                        {proj.has_dxf && <span className="text-[8px] font-bold px-1.5 py-0.5 rounded bg-amber-500/10 text-accent-amber border border-amber-500/10">DXF</span>}
                        {proj.has_dwg && <span className="text-[8px] font-bold px-1.5 py-0.5 rounded bg-emerald-500/10 text-accent-emerald border border-emerald-500/10">DWG</span>}
                        <ChevronRight className="h-4 w-4 text-gray-600 group-hover:text-gray-400 group-hover:translate-x-0.5 transition-all" />
                      </div>
                    </button>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>

      ) : (

        /* INTERACTIVE 2D CANVAS EDITOR VIEW */
        <div className="flex-1 w-full flex overflow-hidden relative">
          {isLoading ? (
            <div className="absolute inset-0 bg-[#0d0e12] z-50 flex flex-col items-center justify-center">
              <span className="animate-spin h-10 w-10 border-4 border-blue-500 border-t-transparent rounded-full mb-4 shadow-[0_0_15px_rgba(59,130,246,0.3)]" />
              <h3 className="text-sm font-semibold text-white">Reconstructing CAD Workspace</h3>
              <p className="text-xs text-gray-500 mt-1">Generating vector maps and rendering floor plan...</p>
            </div>
          ) : error ? (
            <div className="absolute inset-0 bg-[#0d0e12] z-50 flex flex-col items-center justify-center p-6">
              <AlertCircle className="h-12 w-12 text-rose-500 mb-4 animate-bounce" />
              <h3 className="text-lg font-bold text-white">Initialization Error</h3>
              <p className="text-xs text-gray-400 max-w-sm text-center mt-2 mb-6">{error}</p>
              <button 
                onClick={handleBackToUpload}
                className="px-5 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold shadow-lg transition-colors"
              >
                Return to Dashboard
              </button>
            </div>
          ) : null}

          {/* Floaters on Canvas */}
          <Toolbar />
          <LayerPanel />
          <StatusBar cursorPos={cursorPos} snapActive={snapActive} />

          {/* Interactive Canvas */}
          <div className="flex-1 h-full">
            <FloorPlanViewer 
              onCursorChange={setCursorPos}
              onSnapChange={setSnapActive}
            />
          </div>

          {/* Sidebar Properties Inspector */}
          <EditorSidebar onBackToUpload={handleBackToUpload} />
        </div>
      )}
    </div>
  )
}

export default App
