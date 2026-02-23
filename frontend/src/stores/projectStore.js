/**
 * Kage Scan — Global State (Zustand)
 * Manages project, pages, text blocks, and async operations.
 */

import { create } from "zustand";
import {
    getProject,
    startPipeline,
    getPipelineStatus,
    exportProject,
} from "../api/client";

const useProjectStore = create((set, get) => ({
    // ── State ──────────────────────────────────────────────────
    project: null,
    activePage: null,
    activePageIndex: 0,
    selectedBlockId: null,
    isUploading: false,
    uploadProgress: 0,
    isProcessing: false,
    isExporting: false,
    pipelineStatus: null,
    error: null,

    // ── Project Actions ────────────────────────────────────────

    setProject: (project) => {
        const firstPage = project?.pages?.[0] || null;
        set({
            project,
            activePage: firstPage,
            activePageIndex: 0,
            selectedBlockId: null,
            error: null,
        });
    },

    fetchProject: async (id) => {
        try {
            set({ error: null });
            const project = await getProject(id);
            get().setProject(project);
        } catch (err) {
            set({ error: err.message || "Failed to load project" });
        }
    },

    // ── Upload ─────────────────────────────────────────────────

    setUploading: (isUploading) => set({ isUploading }),
    setUploadProgress: (uploadProgress) => set({ uploadProgress }),

    // ── Page Navigation ────────────────────────────────────────

    setActivePage: (page, index) => {
        set({
            activePage: page,
            activePageIndex: index,
            selectedBlockId: null,
        });
    },

    nextPage: () => {
        const { project, activePageIndex } = get();
        if (!project?.pages) return;
        const nextIdx = Math.min(activePageIndex + 1, project.pages.length - 1);
        set({
            activePage: project.pages[nextIdx],
            activePageIndex: nextIdx,
            selectedBlockId: null,
        });
    },

    prevPage: () => {
        const { project, activePageIndex } = get();
        if (!project?.pages) return;
        const prevIdx = Math.max(activePageIndex - 1, 0);
        set({
            activePage: project.pages[prevIdx],
            activePageIndex: prevIdx,
            selectedBlockId: null,
        });
    },

    // ── Text Block Selection & Editing ─────────────────────────

    selectTextBlock: (blockId) => set({ selectedBlockId: blockId }),

    getSelectedBlock: () => {
        const { activePage, selectedBlockId } = get();
        if (!activePage?.text_blocks || !selectedBlockId) return null;
        return activePage.text_blocks.find((b) => b.id === selectedBlockId) || null;
    },

    updateTextBlock: (blockId, updates) => {
        const { project, activePage, activePageIndex } = get();
        if (!project || !activePage) return;

        // Update the text block in the active page
        const updatedBlocks = activePage.text_blocks.map((block) =>
            block.id === blockId ? { ...block, ...updates, is_edited: true } : block
        );

        const updatedPage = { ...activePage, text_blocks: updatedBlocks };

        // Update in the project pages array too
        const updatedPages = project.pages.map((p, i) =>
            i === activePageIndex ? updatedPage : p
        );

        set({
            activePage: updatedPage,
            project: { ...project, pages: updatedPages },
        });
    },

    deleteTextBlock: (blockId) => {
        const { project, activePage, activePageIndex, selectedBlockId } = get();
        if (!project || !activePage) return;

        const updatedBlocks = activePage.text_blocks.filter((b) => b.id !== blockId);
        const updatedPage = { ...activePage, text_blocks: updatedBlocks };
        const updatedPages = project.pages.map((p, i) =>
            i === activePageIndex ? updatedPage : p
        );

        set({
            activePage: updatedPage,
            project: { ...project, pages: updatedPages },
            selectedBlockId: selectedBlockId === blockId ? null : selectedBlockId,
        });
    },

    // ── Pipeline ───────────────────────────────────────────────

    runPipeline: async () => {
        const { project } = get();
        if (!project) return;

        try {
            set({ isProcessing: true, error: null });
            await startPipeline(project.id);

            // Poll status every 3 seconds
            const pollInterval = setInterval(async () => {
                try {
                    const status = await getPipelineStatus(project.id);
                    set({ pipelineStatus: status });

                    if (
                        status.project_status === "ready" ||
                        status.project_status === "error"
                    ) {
                        clearInterval(pollInterval);
                        set({ isProcessing: false });

                        // Reload project to get updated text blocks
                        await get().fetchProject(project.id);
                    }
                } catch {
                    clearInterval(pollInterval);
                    set({ isProcessing: false, error: "Failed to check pipeline status" });
                }
            }, 3000);
        } catch (err) {
            set({
                isProcessing: false,
                error: err?.response?.data?.detail || "Failed to start pipeline",
            });
        }
    },

    // ── Export ─────────────────────────────────────────────────

    runExport: async () => {
        const { project } = get();
        if (!project) return;

        try {
            set({ isExporting: true, error: null });
            await exportProject(project.id, project.name);
            set({ isExporting: false });

            // Reload to get updated status
            await get().fetchProject(project.id);
        } catch (err) {
            set({
                isExporting: false,
                error: err?.response?.data?.detail || "Export failed",
            });
        }
    },

    // ── Reset ──────────────────────────────────────────────────
    reset: () =>
        set({
            project: null,
            activePage: null,
            activePageIndex: 0,
            selectedBlockId: null,
            isUploading: false,
            uploadProgress: 0,
            isProcessing: false,
            isExporting: false,
            pipelineStatus: null,
            error: null,
        }),
}));

export default useProjectStore;
