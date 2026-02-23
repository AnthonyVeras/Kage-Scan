/**
 * Kage Scan — Settings Page
 * Configure AI provider: OpenRouter (API key) or GitHub Copilot (Device Flow OAuth).
 */

import { useEffect, useState } from "react";
import {
    Settings,
    Key,
    Github,
    Loader2,
    CheckCircle2,
    AlertCircle,
    Copy,
    ExternalLink,
    Cpu,
    Sparkles,
} from "lucide-react";
import useSettingsStore from "../stores/settingsStore";

export default function SettingsPage() {
    const {
        provider,
        openrouterKey,
        openrouterModel,
        copilotModel,
        copilotAuthenticated,
        isLoading,
        isSaving,
        error,
        success,
        userCode,
        verificationUri,
        isPolling,
        pollMessage,
        fetchSettings,
        saveOpenRouter,
        saveCopilotModel,
        startCopilotFlow,
        cancelCopilotFlow,
        clearMessages,
    } = useSettingsStore();

    const [activeTab, setActiveTab] = useState("openrouter");
    const [keyInput, setKeyInput] = useState("");
    const [modelInput, setModelInput] = useState("");
    const [copilotModelInput, setCopilotModelInput] = useState("");
    const [copied, setCopied] = useState(false);

    // Load settings on mount
    useEffect(() => {
        fetchSettings();
    }, [fetchSettings]);

    // Initialize inputs when settings load
    useEffect(() => {
        setModelInput(openrouterModel);
        setCopilotModelInput(copilotModel);
        if (provider === "copilot") setActiveTab("copilot");
    }, [openrouterModel, copilotModel, provider]);

    const handleSaveOpenRouter = () => {
        const key = keyInput || undefined;
        saveOpenRouter(key, modelInput);
    };

    const copyCode = async () => {
        if (!userCode) return;
        await navigator.clipboard.writeText(userCode);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    if (isLoading) {
        return (
            <div className="flex items-center justify-center min-h-[calc(100vh-8rem)]">
                <Loader2 size={24} className="animate-spin text-sakura-400" />
            </div>
        );
    }

    const tabs = [
        { id: "openrouter", label: "OpenRouter", icon: Key },
        { id: "copilot", label: "GitHub Copilot", icon: Github },
    ];

    return (
        <div className="max-w-2xl mx-auto py-8 animate-fade-in">
            {/* Header */}
            <div className="flex items-center gap-3 mb-8">
                <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-sakura-400/10 text-sakura-400">
                    <Settings size={20} strokeWidth={1.5} />
                </div>
                <div>
                    <h2 className="text-lg font-display font-bold text-neutral-200">
                        Configurações
                    </h2>
                    <p className="text-xs text-neutral-600">
                        Configure o motor de IA para tradução
                    </p>
                </div>
            </div>

            {/* Status Messages */}
            {error && (
                <div className="flex items-center gap-2 mb-4 px-4 py-2.5 rounded-xl bg-red-400/10 border border-red-400/20 text-red-400 text-xs">
                    <AlertCircle size={14} />
                    {error}
                    <button
                        onClick={clearMessages}
                        className="ml-auto text-red-400/60 hover:text-red-400"
                    >
                        ✕
                    </button>
                </div>
            )}
            {success && (
                <div className="flex items-center gap-2 mb-4 px-4 py-2.5 rounded-xl bg-emerald-400/10 border border-emerald-400/20 text-emerald-400 text-xs">
                    <CheckCircle2 size={14} />
                    {success}
                </div>
            )}

            {/* Active Provider Badge */}
            <div className="flex items-center gap-2 mb-6 px-3 py-2 rounded-xl glass-surface">
                <Cpu size={13} className="text-neutral-600" />
                <span className="text-[11px] text-neutral-500">Provider ativo:</span>
                <span
                    className={`text-[11px] font-medium ${provider === "none"
                            ? "text-neutral-600"
                            : "text-sakura-300"
                        }`}
                >
                    {provider === "openrouter"
                        ? "OpenRouter"
                        : provider === "copilot"
                            ? "GitHub Copilot"
                            : "Nenhum configurado"}
                </span>
            </div>

            {/* Tab Switcher */}
            <div className="flex gap-1 mb-6 p-1 rounded-xl glass-surface">
                {tabs.map((tab) => {
                    const Icon = tab.icon;
                    const isActive = activeTab === tab.id;
                    return (
                        <button
                            key={tab.id}
                            onClick={() => setActiveTab(tab.id)}
                            className={`
                flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg text-xs font-medium
                transition-all duration-200
                ${isActive
                                    ? "bg-sakura-400/15 text-sakura-300 border border-sakura-400/20"
                                    : "text-neutral-600 hover:text-neutral-400"
                                }
              `}
                        >
                            <Icon size={14} />
                            {tab.label}
                        </button>
                    );
                })}
            </div>

            {/* ── OpenRouter Tab ────────────────────────────────────── */}
            {activeTab === "openrouter" && (
                <div className="card p-6 space-y-5 animate-fade-in">
                    <div className="flex items-center gap-2 mb-1">
                        <Sparkles size={14} className="text-sakura-400" />
                        <h3 className="text-sm font-medium text-neutral-300">
                            OpenRouter API
                        </h3>
                    </div>
                    <p className="text-[11px] text-neutral-600 leading-relaxed">
                        Use qualquer modelo via OpenRouter (Claude, GPT-4, Gemini, Llama, etc.).
                        Crie uma conta em{" "}
                        <a
                            href="https://openrouter.ai"
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-sakura-400 hover:underline"
                        >
                            openrouter.ai
                        </a>{" "}
                        e copie sua API key.
                    </p>

                    {/* API Key */}
                    <div>
                        <label className="block text-[11px] font-medium text-neutral-500 mb-1.5">
                            API Key
                        </label>
                        <input
                            type="password"
                            value={keyInput}
                            onChange={(e) => setKeyInput(e.target.value)}
                            placeholder={openrouterKey || "sk-or-v1-..."}
                            className="w-full rounded-xl border border-white/[0.06] bg-ink-600 px-4 py-2.5 text-sm text-neutral-200 placeholder:text-neutral-700 outline-none focus:border-sakura-400/30 focus:shadow-sakura-sm transition-all font-mono"
                        />
                        {openrouterKey && !keyInput && (
                            <p className="text-[10px] text-neutral-600 mt-1">
                                Key salva: {openrouterKey}
                            </p>
                        )}
                    </div>

                    {/* Model Name */}
                    <div>
                        <label className="block text-[11px] font-medium text-neutral-500 mb-1.5">
                            Modelo
                        </label>
                        <input
                            type="text"
                            value={modelInput}
                            onChange={(e) => setModelInput(e.target.value)}
                            placeholder="anthropic/claude-3.5-sonnet"
                            className="w-full rounded-xl border border-white/[0.06] bg-ink-600 px-4 py-2.5 text-sm text-neutral-200 placeholder:text-neutral-700 outline-none focus:border-sakura-400/30 focus:shadow-sakura-sm transition-all font-mono"
                        />
                        <p className="text-[10px] text-neutral-600 mt-1">
                            Ex: anthropic/claude-3.5-sonnet, google/gemini-2.0-flash, openai/gpt-4o
                        </p>
                    </div>

                    {/* Save Button */}
                    <button
                        onClick={handleSaveOpenRouter}
                        disabled={isSaving}
                        className="btn-sakura w-full flex items-center justify-center gap-2 py-2.5"
                    >
                        {isSaving ? (
                            <Loader2 size={14} className="animate-spin" />
                        ) : (
                            <Key size={14} />
                        )}
                        {isSaving ? "Salvando..." : "Salvar Configuração"}
                    </button>
                </div>
            )}

            {/* ── Copilot Tab ───────────────────────────────────────── */}
            {activeTab === "copilot" && (
                <div className="card p-6 space-y-5 animate-fade-in">
                    <div className="flex items-center gap-2 mb-1">
                        <Github size={14} className="text-sakura-400" />
                        <h3 className="text-sm font-medium text-neutral-300">
                            GitHub Copilot
                        </h3>
                    </div>
                    <p className="text-[11px] text-neutral-600 leading-relaxed">
                        Use sua assinatura do GitHub Copilot como motor de tradução.
                        Grátis se você já tem Copilot ativo na sua conta GitHub.
                    </p>

                    {/* Already authenticated */}
                    {copilotAuthenticated && !isPolling && (
                        <div className="space-y-4">
                            <div className="flex items-center gap-2 px-3 py-2.5 rounded-xl bg-emerald-400/10 border border-emerald-400/20">
                                <CheckCircle2 size={14} className="text-emerald-400" />
                                <span className="text-xs text-emerald-400 font-medium">
                                    Autenticado via GitHub Copilot
                                </span>
                            </div>

                            {/* Model selector */}
                            <div>
                                <label className="block text-[11px] font-medium text-neutral-500 mb-1.5">
                                    Modelo do Copilot
                                </label>
                                <div className="flex gap-2">
                                    <input
                                        type="text"
                                        value={copilotModelInput}
                                        onChange={(e) => setCopilotModelInput(e.target.value)}
                                        placeholder="gpt-4o"
                                        className="flex-1 rounded-xl border border-white/[0.06] bg-ink-600 px-4 py-2.5 text-sm text-neutral-200 placeholder:text-neutral-700 outline-none focus:border-sakura-400/30 focus:shadow-sakura-sm transition-all font-mono"
                                    />
                                    <button
                                        onClick={() => saveCopilotModel(copilotModelInput)}
                                        disabled={isSaving}
                                        className="btn-sakura px-4"
                                    >
                                        {isSaving ? (
                                            <Loader2 size={14} className="animate-spin" />
                                        ) : (
                                            "Salvar"
                                        )}
                                    </button>
                                </div>
                                <p className="text-[10px] text-neutral-600 mt-1">
                                    Ex: gpt-4o, claude-3.5-sonnet, o1-mini
                                </p>
                            </div>
                        </div>
                    )}

                    {/* Device flow: show user code */}
                    {isPolling && userCode && (
                        <div className="space-y-4">
                            <div className="text-center py-4 px-6 rounded-xl bg-ink-600/60 border border-white/[0.04]">
                                <p className="text-[11px] text-neutral-500 mb-3">
                                    Cole este código no GitHub:
                                </p>
                                <div className="flex items-center justify-center gap-3 mb-3">
                                    <span className="text-3xl font-mono font-bold text-sakura-300 tracking-[0.3em]">
                                        {userCode}
                                    </span>
                                    <button
                                        onClick={copyCode}
                                        className="p-2 rounded-lg hover:bg-white/[0.05] text-neutral-500 hover:text-sakura-400 transition-all"
                                        title="Copiar código"
                                    >
                                        {copied ? (
                                            <CheckCircle2 size={16} className="text-emerald-400" />
                                        ) : (
                                            <Copy size={16} />
                                        )}
                                    </button>
                                </div>

                                <a
                                    href={verificationUri}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-sakura-400/10 text-sakura-300 text-xs font-medium hover:bg-sakura-400/15 transition-all"
                                >
                                    <ExternalLink size={12} />
                                    Abrir GitHub para autorizar
                                </a>
                            </div>

                            <div className="flex items-center justify-center gap-2 text-xs text-neutral-500">
                                <Loader2 size={12} className="animate-spin text-sakura-400" />
                                {pollMessage || "Aguardando autorização..."}
                            </div>

                            <button
                                onClick={cancelCopilotFlow}
                                className="btn-ghost w-full text-xs"
                            >
                                Cancelar
                            </button>
                        </div>
                    )}

                    {/* Not authenticated, not polling */}
                    {!copilotAuthenticated && !isPolling && (
                        <button
                            onClick={startCopilotFlow}
                            className="btn-sakura w-full flex items-center justify-center gap-2 py-3"
                        >
                            <Github size={16} />
                            Ligar com GitHub Copilot
                        </button>
                    )}
                </div>
            )}
        </div>
    );
}
