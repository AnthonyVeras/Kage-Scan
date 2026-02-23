/**
 * Kage Scan — API Client
 * Axios wrapper for all backend communication.
 */

import axios from "axios";

const api = axios.create({
    baseURL: "/api",
    timeout: 120_000, // 2 min — some AI operations are slow
});

/**
 * Upload a project (ZIP or images) with progress tracking.
 * @param {string} name - Project name
 * @param {File} file - ZIP or image file
 * @param {string} sourceLang - Source language (ja|ko|zh|en)
 * @param {string} targetLang - Target language
 * @param {function} onProgress - Progress callback (0-100)
 * @returns {Promise<object>} Created project data
 */
export async function uploadProject(
    name,
    file,
    sourceLang = "ja",
    targetLang = "pt-br",
    onProgress = () => { }
) {
    const formData = new FormData();
    formData.append("name", name);
    formData.append("source_language", sourceLang);
    formData.append("target_language", targetLang);
    formData.append("file", file);

    const { data } = await api.post("/projects/", formData, {
        headers: { "Content-Type": "multipart/form-data" },
        onUploadProgress: (e) => {
            const pct = Math.round((e.loaded * 100) / (e.total || 1));
            onProgress(pct);
        },
    });

    return data;
}

/**
 * List all projects.
 * @returns {Promise<object[]>}
 */
export async function listProjects() {
    const { data } = await api.get("/projects/");
    return data;
}

/**
 * Get full project details (with pages + text blocks).
 * @param {string} id - Project UUID
 * @returns {Promise<object>}
 */
export async function getProject(id) {
    const { data } = await api.get(`/projects/${id}`);
    return data;
}

/**
 * Start the AI pipeline (detect → OCR → translate).
 * Returns 202 immediately — processing happens in background.
 * @param {string} id - Project UUID
 * @returns {Promise<object>}
 */
export async function startPipeline(id) {
    const { data } = await api.post(`/pipeline/${id}/start`);
    return data;
}

/**
 * Poll pipeline status for a project.
 * @param {string} id - Project UUID
 * @returns {Promise<object>}
 */
export async function getPipelineStatus(id) {
    const { data } = await api.get(`/pipeline/${id}/status`);
    return data;
}

/**
 * Export translated project as ZIP download.
 * @param {string} id - Project UUID
 * @param {string} projectName - For the filename
 */
export async function exportProject(id, projectName = "project") {
    const response = await api.get(`/export/projects/${id}/export`, {
        responseType: "blob",
    });

    // Trigger browser download
    const url = window.URL.createObjectURL(response.data);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${projectName}_translated.zip`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
}

export default api;
