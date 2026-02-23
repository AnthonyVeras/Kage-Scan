/**
 * Kage Scan — Editor Toolbar
 * Top bar with pipeline controls, status display, and export button.
 */

import {
    Wand2,
    Download,
    Loader2,
    CheckCircle2,
    AlertCircle,
    ChevronLeft,
    ChevronRight,
    Zap,
} from "lucide-react";
import useProjectStore from "../../stores/projectStore";

export default function ToolBar() {
    const project = useProjectStore((s) => s.project);
    const activePage = useProjectStore((s) => s.activePage);
    const activePageIndex = useProjectStore((s) => s.activePageIndex);
    const isProcessing = useProjectStore((s) => s.isProcessing);
    const isExporting = useProjectStore((s) => s.isExporting);
    const pipelineStatus = useProjectStore((s) => s.pipelineStatus);
    const error = useProjectStore((s) => s.error);
    const runPipeline = useProjectStore((s) => s.runPipeline);
    const runExport = useProjectStore((s) => s.runExport);
    const nextPage = useProjectStore((s) => s.nextPage);
    const prevPage = useProjectStore((s) => s.prevPage);

    const totalPages = project?.pages?.length || 0;
    const blockCount = activePage?.text_blocks?.length || 0;
    const status = project?.status || "unknown";

    const statusConfig = {
        processing: {
            icon: Loader2,
            text: "Processando...",
            color: "text-amber-400",
            spin: true,
        },
        ready: {
            icon: CheckCircle2,
            text: "Pronto",
            color: "text-emerald-400",
            spin: false,
        },
        exported: {
            icon: CheckCircle2,
            text: "Exportado",
            color: "text-emerald-400",
            spin: false,
        },
        error: {
            icon: AlertCircle,
            text: "Erro",
            color: "text-red-400",
            spin: false,
        },
    };

    const currentStatus = statusConfig[status] || {
        icon: Zap,
        text: status,
        color: "text-neutral-500",
        spin: false,
    };

    const StatusIcon = currentStatus.icon;

    return (
        <div className="glass-surface flex items-center justify-between px-4 py-2.5 rounded-xl mb-3">
            {/* Left: Page Navigation */}
            <div className="flex items-center gap-3">
                <div className="flex items-center gap-1">
                    <button
                        onClick={prevPage}
                        disabled={activePageIndex <= 0}
                        className="icon-btn !p-1.5 disabled:opacity-20 disabled:cursor-not-allowed"
                    >
                        <ChevronLeft size={16} />
                    </button>

                    <span className="text-xs font-mono text-neutral-400 min-w-[60px] text-center">
                        {totalPages > 0
                            ? `${activePageIndex + 1} / ${totalPages}`
                            : "—"
                        }
                    </span>

                    <button
                        onClick={nextPage}
                        disabled={activePageIndex >= totalPages - 1}
                        className="icon-btn !p-1.5 disabled:opacity-20 disabled:cursor-not-allowed"
                    >
                        <ChevronRight size={16} />
                    </button>
                </div>

                <div className="divider-v h-5" />

                {/* Block count */}
                <span className="text-[11px] text-neutral-600">
                    {blockCount} {blockCount === 1 ? "bloco" : "blocos"}
                </span>

                <div className="divider-v h-5" />

                {/* Status Badge */}
                <div className={`flex items-center gap-1.5 ${currentStatus.color}`}>
                    <StatusIcon
                        size={13}
                        className={currentStatus.spin ? "animate-spin" : ""}
                    />
                    <span className="text-[11px] font-medium">{currentStatus.text}</span>
                </div>

                {/* Pipeline progress */}
                {isProcessing && pipelineStatus && (
                    <span className="text-[10px] text-neutral-600 font-mono">
                        ({Object.entries(pipelineStatus.page_statuses || {})
                            .map(([k, v]) => `${k}:${v}`)
                            .join(" ")}
                        )
                    </span>
                )}
            </div>

            {/* Right: Actions */}
            <div className="flex items-center gap-2">
                {/* Error display */}
                {error && (
                    <span className="text-[10px] text-red-400 max-w-[200px] truncate mr-2">
                        {error}
                    </span>
                )}

                {/* Run Pipeline */}
                <button
                    onClick={runPipeline}
                    disabled={isProcessing || isExporting}
                    className={`
            flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-medium
            transition-all duration-300
            ${isProcessing
                            ? "bg-sakura-400/10 text-sakura-300 cursor-wait"
                            : "btn-sakura"
                        }
            disabled:opacity-50
          `}
                >
                    {isProcessing ? (
                        <>
                            <Loader2 size={14} className="animate-spin" />
                            Processando...
                        </>
                    ) : (
                        <>
                            <Wand2 size={14} />
                            Rodar IA
                        </>
                    )}
                </button>

                {/* Export */}
                <button
                    onClick={runExport}
                    disabled={isExporting || isProcessing || status === "processing"}
                    className="btn-ghost flex items-center gap-2 disabled:opacity-30"
                >
                    {isExporting ? (
                        <>
                            <Loader2 size={14} className="animate-spin" />
                            Exportando...
                        </>
                    ) : (
                        <>
                            <Download size={14} />
                            Exportar ZIP
                        </>
                    )}
                </button>
            </div>
        </div>
    );
}
