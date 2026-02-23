/**
 * Kage Scan — Editor Page
 * Three-panel layout: Page List | Canvas + ToolBar | Text Block Panel
 */

import { useEffect } from "react";
import { useParams } from "react-router-dom";
import { FileImage, Loader2 } from "lucide-react";
import useProjectStore from "../stores/projectStore";
import Canvas from "../components/Editor/Canvas";
import ToolBar from "../components/Editor/ToolBar";
import TextBlockPanel from "../components/Editor/TextBlockPanel";

export default function EditorPage() {
    const { id } = useParams();
    const project = useProjectStore((s) => s.project);
    const activePage = useProjectStore((s) => s.activePage);
    const activePageIndex = useProjectStore((s) => s.activePageIndex);
    const setActivePage = useProjectStore((s) => s.setActivePage);
    const fetchProject = useProjectStore((s) => s.fetchProject);
    const error = useProjectStore((s) => s.error);

    // Load project on mount (if not already loaded or ID changed)
    useEffect(() => {
        if (!project || project.id !== id) {
            fetchProject(id);
        }
    }, [id, project, fetchProject]);

    // Loading state
    if (!project) {
        return (
            <div className="flex items-center justify-center min-h-[calc(100vh-8rem)]">
                {error ? (
                    <div className="card p-8 text-center max-w-sm">
                        <p className="text-red-400 text-sm mb-2">Erro ao carregar projeto</p>
                        <p className="text-neutral-600 text-xs">{error}</p>
                    </div>
                ) : (
                    <div className="flex items-center gap-3 text-neutral-500">
                        <Loader2 size={20} className="animate-spin text-sakura-400" />
                        <span className="text-sm">Carregando projeto...</span>
                    </div>
                )}
            </div>
        );
    }

    const pages = project.pages || [];

    return (
        <div className="flex gap-3 h-[calc(100vh-8rem)] animate-fade-in">
            {/* ── Left Sidebar: Page List ──────────────────────────── */}
            <div className="w-48 shrink-0 flex flex-col glass-surface rounded-xl overflow-hidden">
                {/* Header */}
                <div className="px-3 py-2.5 border-b border-white/[0.04]">
                    <h3 className="text-[11px] font-medium text-neutral-500 uppercase tracking-wider">
                        Páginas ({pages.length})
                    </h3>
                </div>

                {/* Page list */}
                <div className="flex-1 overflow-y-auto p-1.5 space-y-1">
                    {pages.map((page, idx) => {
                        const isActive = idx === activePageIndex;
                        const blockCount = page.text_blocks?.length || 0;

                        return (
                            <button
                                key={page.id}
                                onClick={() => setActivePage(page, idx)}
                                className={`
                  w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-left
                  transition-all duration-200 group
                  ${isActive
                                        ? "bg-sakura-400/10 border border-sakura-400/20 text-sakura-300"
                                        : "border border-transparent text-neutral-500 hover:bg-white/[0.02] hover:text-neutral-300"
                                    }
                `}
                            >
                                {/* Page number */}
                                <span
                                    className={`
                    flex h-6 w-6 shrink-0 items-center justify-center rounded-md text-[10px] font-mono font-medium
                    ${isActive
                                            ? "bg-sakura-400/20 text-sakura-300"
                                            : "bg-white/[0.03] text-neutral-600 group-hover:text-neutral-400"
                                        }
                  `}
                                >
                                    {idx + 1}
                                </span>

                                {/* Info */}
                                <div className="min-w-0 flex-1">
                                    <p className="text-[11px] font-medium truncate">
                                        {page.filename}
                                    </p>
                                    <div className="flex items-center gap-2 mt-0.5">
                                        <StatusDot status={page.status} />
                                        {blockCount > 0 && (
                                            <span className="text-[9px] text-neutral-600">
                                                {blockCount} blocos
                                            </span>
                                        )}
                                    </div>
                                </div>
                            </button>
                        );
                    })}

                    {pages.length === 0 && (
                        <div className="flex flex-col items-center gap-2 py-8 text-neutral-700">
                            <FileImage size={20} />
                            <span className="text-[10px]">Nenhuma página</span>
                        </div>
                    )}
                </div>
            </div>

            {/* ── Center: Canvas + Toolbar ─────────────────────────── */}
            <div className="flex-1 flex flex-col min-w-0">
                <ToolBar />
                <Canvas />
            </div>

            {/* ── Right Sidebar: Text Block Panel ──────────────────── */}
            <div className="w-64 shrink-0 glass-surface rounded-xl overflow-hidden">
                <TextBlockPanel />
            </div>
        </div>
    );
}

/* ── Status Indicator Dot ─────────────────────────────────── */
function StatusDot({ status }) {
    const colors = {
        pending: "bg-neutral-600",
        processing: "bg-amber-400 animate-pulse",
        ocr_done: "bg-blue-400",
        translated: "bg-emerald-400",
        done: "bg-emerald-400",
    };

    return (
        <span
            className={`inline-block w-1.5 h-1.5 rounded-full ${colors[status] || "bg-neutral-700"}`}
            title={status}
        />
    );
}
