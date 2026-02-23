/**
 * Kage Scan — Text Block Edit Panel (Right Sidebar)
 * Shows OCR text, translated text, and typesetting controls for the selected block.
 */

import { Type, Trash2, Languages, AlignCenter } from "lucide-react";
import useProjectStore from "../../stores/projectStore";

export default function TextBlockPanel() {
    const selectedBlockId = useProjectStore((s) => s.selectedBlockId);
    const activePage = useProjectStore((s) => s.activePage);
    const updateTextBlock = useProjectStore((s) => s.updateTextBlock);
    const deleteTextBlock = useProjectStore((s) => s.deleteTextBlock);

    // Find the selected block
    const block = activePage?.text_blocks?.find((b) => b.id === selectedBlockId);

    if (!block) {
        return (
            <div className="flex flex-col items-center justify-center h-full text-center px-4 gap-3">
                <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-white/[0.03] text-neutral-700">
                    <Type size={22} strokeWidth={1.5} />
                </div>
                <p className="text-xs text-neutral-600 leading-relaxed max-w-[160px]">
                    Selecione um balão de texto na imagem para editar
                </p>
            </div>
        );
    }

    const handleChange = (field, value) => {
        updateTextBlock(block.id, { [field]: value });
    };

    return (
        <div className="flex flex-col h-full animate-fade-in">
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-white/[0.04]">
                <div className="flex items-center gap-2">
                    <Languages size={14} className="text-sakura-400" />
                    <span className="text-xs font-medium text-neutral-400">
                        Text Block
                    </span>
                </div>
                <button
                    onClick={() => deleteTextBlock(block.id)}
                    className="p-1.5 rounded-lg text-neutral-600 hover:text-red-400 hover:bg-red-400/10 transition-all"
                    title="Deletar bloco"
                >
                    <Trash2 size={13} />
                </button>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-4 space-y-5">
                {/* Position info */}
                <div className="grid grid-cols-2 gap-2">
                    {[
                        { label: "X", value: Math.round(block.box_x) },
                        { label: "Y", value: Math.round(block.box_y) },
                        { label: "W", value: Math.round(block.box_width) },
                        { label: "H", value: Math.round(block.box_height) },
                    ].map(({ label, value }) => (
                        <div
                            key={label}
                            className="flex items-center gap-2 rounded-lg bg-ink-600/60 px-2.5 py-1.5"
                        >
                            <span className="text-[10px] font-mono text-neutral-600 w-3">
                                {label}
                            </span>
                            <span className="text-[11px] font-mono text-neutral-400">
                                {value}
                            </span>
                        </div>
                    ))}
                </div>

                {/* Original Text (OCR) */}
                <div>
                    <label className="flex items-center gap-1.5 text-[11px] font-medium text-neutral-500 mb-1.5">
                        <span className="w-1.5 h-1.5 rounded-full bg-neutral-600" />
                        Texto Original (OCR)
                    </label>
                    <textarea
                        value={block.text_original || ""}
                        onChange={(e) => handleChange("text_original", e.target.value)}
                        rows={3}
                        className="w-full rounded-xl border border-white/[0.04] bg-ink-600/60 px-3 py-2.5 text-xs text-neutral-300 font-mono placeholder:text-neutral-700 outline-none focus:border-sakura-400/20 focus:shadow-sakura-sm resize-none transition-all"
                        placeholder="Texto detectado pelo OCR..."
                    />
                </div>

                {/* Translated Text */}
                <div>
                    <label className="flex items-center gap-1.5 text-[11px] font-medium text-sakura-400/80 mb-1.5">
                        <span className="w-1.5 h-1.5 rounded-full bg-sakura-400" />
                        Tradução (PT-BR)
                    </label>
                    <textarea
                        value={block.text_translated || ""}
                        onChange={(e) => handleChange("text_translated", e.target.value)}
                        rows={4}
                        className="w-full rounded-xl border border-sakura-400/10 bg-sakura-400/[0.03] px-3 py-2.5 text-xs text-neutral-200 placeholder:text-neutral-700 outline-none focus:border-sakura-400/30 focus:shadow-sakura-sm resize-none transition-all"
                        placeholder="Tradução para português..."
                    />
                </div>

                <div className="divider-h" />

                {/* Typography Controls */}
                <div className="space-y-3">
                    <p className="text-[11px] font-medium text-neutral-500 flex items-center gap-1.5">
                        <AlignCenter size={11} />
                        Tipografia
                    </p>

                    {/* Font Size */}
                    <div className="flex items-center gap-3">
                        <label className="text-[10px] text-neutral-600 w-12 shrink-0">
                            Tamanho
                        </label>
                        <input
                            type="range"
                            min={8}
                            max={48}
                            value={block.font_size || 18}
                            onChange={(e) =>
                                handleChange("font_size", parseInt(e.target.value, 10))
                            }
                            className="flex-1 h-1 bg-ink-50/30 rounded-full appearance-none cursor-pointer accent-sakura-400"
                        />
                        <span className="text-[11px] font-mono text-neutral-400 w-6 text-right">
                            {block.font_size || 18}
                        </span>
                    </div>

                    {/* Text Alignment */}
                    <div className="flex items-center gap-3">
                        <label className="text-[10px] text-neutral-600 w-12 shrink-0">
                            Alinhamento
                        </label>
                        <div className="flex gap-1">
                            {["left", "center", "right"].map((align) => (
                                <button
                                    key={align}
                                    onClick={() => handleChange("text_alignment", align)}
                                    className={`
                    px-2.5 py-1 rounded-lg text-[10px] font-medium transition-all
                    ${(block.text_alignment || "center") === align
                                            ? "bg-sakura-400/15 text-sakura-300 border border-sakura-400/20"
                                            : "bg-ink-600/60 text-neutral-600 border border-transparent hover:text-neutral-400"
                                        }
                  `}
                                >
                                    {align === "left" ? "←" : align === "center" ? "↔" : "→"}
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Text Color */}
                    <div className="flex items-center gap-3">
                        <label className="text-[10px] text-neutral-600 w-12 shrink-0">
                            Cor
                        </label>
                        <input
                            type="color"
                            value={block.text_color || "#000000"}
                            onChange={(e) => handleChange("text_color", e.target.value)}
                            className="w-7 h-7 rounded-lg border border-white/[0.06] bg-transparent cursor-pointer"
                        />
                        <span className="text-[10px] font-mono text-neutral-500">
                            {block.text_color || "#000000"}
                        </span>
                    </div>
                </div>
            </div>

            {/* Edited indicator */}
            {block.is_edited && (
                <div className="px-4 py-2 border-t border-white/[0.04]">
                    <span className="text-[10px] text-sakura-400/60">● Editado</span>
                </div>
            )}
        </div>
    );
}
