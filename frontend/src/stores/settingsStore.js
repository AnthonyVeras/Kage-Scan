/**
 * Kage Scan — Settings Store (Zustand)
 * Manages AI provider config and GitHub Copilot device flow.
 */

import { create } from "zustand";
import {
    getSettings,
    updateSettings as apiUpdateSettings,
    startCopilotAuth,
    pollCopilotAuth,
} from "../api/client";

const useSettingsStore = create((set, get) => ({
    // ── State ──────────────────────────────────────────────────
    provider: "none",
    openrouterKey: "",
    openrouterModel: "anthropic/claude-3.5-sonnet",
    copilotModel: "gpt-4o",
    copilotAuthenticated: false,

    // UI state
    isLoading: false,
    isSaving: false,
    error: null,
    success: null,

    // Copilot device flow state
    deviceCode: null,
    userCode: null,
    verificationUri: null,
    isPolling: false,
    pollMessage: null,

    // ── Load Settings ──────────────────────────────────────────
    fetchSettings: async () => {
        try {
            set({ isLoading: true, error: null });
            const data = await getSettings();
            set({
                provider: data.provider,
                openrouterKey: data.openrouter_key || "",
                openrouterModel: data.openrouter_model,
                copilotModel: data.copilot_model,
                copilotAuthenticated: data.copilot_authenticated,
                isLoading: false,
            });
        } catch (err) {
            set({ isLoading: false, error: "Failed to load settings" });
        }
    },

    // ── Save OpenRouter Config ─────────────────────────────────
    saveOpenRouter: async (key, model) => {
        try {
            set({ isSaving: true, error: null, success: null });
            await apiUpdateSettings({
                provider: "openrouter",
                openrouter_key: key,
                openrouter_model: model,
            });
            set({
                provider: "openrouter",
                openrouterKey: "•".repeat(12) + key.slice(-4),
                openrouterModel: model,
                isSaving: false,
                success: "OpenRouter configurado com sucesso!",
            });
            setTimeout(() => set({ success: null }), 3000);
        } catch (err) {
            set({
                isSaving: false,
                error: err?.response?.data?.detail || "Failed to save OpenRouter settings",
            });
        }
    },

    // ── Save Copilot Model ─────────────────────────────────────
    saveCopilotModel: async (model) => {
        try {
            set({ isSaving: true, error: null });
            await apiUpdateSettings({ copilot_model: model });
            set({ copilotModel: model, isSaving: false, success: "Modelo atualizado!" });
            setTimeout(() => set({ success: null }), 3000);
        } catch (err) {
            set({ isSaving: false, error: "Failed to update model" });
        }
    },

    // ── Copilot Device Flow ────────────────────────────────────
    startCopilotFlow: async () => {
        try {
            set({ error: null, isPolling: false, pollMessage: null });
            const data = await startCopilotAuth();
            set({
                deviceCode: data.device_code,
                userCode: data.user_code,
                verificationUri: data.verification_uri,
                isPolling: true,
                pollMessage: "Aguardando autorização...",
            });

            // Start polling every 5 seconds
            const interval = data.interval || 5;
            get()._pollForAuth(data.device_code, interval);
        } catch (err) {
            set({ error: "Failed to start Copilot auth flow" });
        }
    },

    _pollForAuth: (deviceCode, intervalSec) => {
        let currentInterval = intervalSec;

        const poll = async () => {
            // Check if polling was cancelled
            if (!get().isPolling) return;

            try {
                const result = await pollCopilotAuth(deviceCode);

                if (result.status === "authenticated") {
                    set({
                        isPolling: false,
                        copilotAuthenticated: true,
                        provider: "copilot",
                        deviceCode: null,
                        userCode: null,
                        verificationUri: null,
                        pollMessage: null,
                        success: "Copilot conectado com sucesso!",
                        _pollTimer: null,
                    });
                    setTimeout(() => set({ success: null }), 3000);
                    return;
                }

                if (result.status === "error") {
                    set({
                        isPolling: false,
                        error: result.message || "Auth failed",
                        deviceCode: null,
                        userCode: null,
                        _pollTimer: null,
                    });
                    return;
                }

                // "pending" — schedule next poll
                // If GitHub says "slow_down", add 5 seconds per spec
                if (result.message && result.message.toLowerCase().includes("slow down")) {
                    currentInterval += 5;
                }

                set({ pollMessage: result.message || "Aguardando..." });
                const timer = setTimeout(poll, currentInterval * 1000);
                set({ _pollTimer: timer });
            } catch {
                set({
                    isPolling: false,
                    error: "Polling failed",
                    _pollTimer: null,
                });
            }
        };

        // First poll after the interval
        const timer = setTimeout(poll, currentInterval * 1000);
        set({ _pollTimer: timer });
    },

    cancelCopilotFlow: () => {
        const timer = get()._pollTimer;
        if (timer) clearTimeout(timer);
        set({
            isPolling: false,
            deviceCode: null,
            userCode: null,
            verificationUri: null,
            pollMessage: null,
            _pollTimer: null,
        });
    },

    // ── Clear Messages ─────────────────────────────────────────
    clearMessages: () => set({ error: null, success: null }),
}));

export default useSettingsStore;
