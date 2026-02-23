/**
 * Kage Scan — Upload Drop Zone
 * Drag-and-drop area using react-dropzone with sakura glow effects.
 */

import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { Upload, FileArchive, Image, Loader2 } from "lucide-react";
import useProjectStore from "../../stores/projectStore";
import { uploadProject } from "../../api/client";

export default function UploadZone({ onProjectCreated }) {
    const { isUploading, uploadProgress, setUploading, setUploadProgress } =
        useProjectStore();
    const [projectName, setProjectName] = useState("");
    const [sourceLang, setSourceLang] = useState("ja");
    const [droppedFile, setDroppedFile] = useState(null);
    const [error, setError] = useState(null);

    const onDrop = useCallback((acceptedFiles) => {
        if (acceptedFiles.length > 0) {
            const file = acceptedFiles[0];
            setDroppedFile(file);
            setError(null);

            // Auto-generate project name from filename
            if (!projectName) {
                const name = file.name.replace(/\.[^/.]+$/, "").replace(/[_-]/g, " ");
                setProjectName(name);
            }
        }
    }, [projectName]);

    const { getRootProps, getInputProps, isDragActive } = useDropzone({
        onDrop,
        accept: {
            "application/zip": [".zip"],
            "image/*": [".png", ".jpg", ".jpeg", ".webp", ".bmp"],
        },
        multiple: false,
        disabled: isUploading,
    });

    const handleUpload = async () => {
        if (!droppedFile) return;
        if (!projectName.trim()) {
            setError("Dê um nome ao projeto.");
            return;
        }

        try {
            setError(null);
            setUploading(true);
            setUploadProgress(0);

            const project = await uploadProject(
                projectName.trim(),
                droppedFile,
                sourceLang,
                "pt-br",
                (pct) => setUploadProgress(pct)
            );

            setUploading(false);
            setUploadProgress(100);
            onProjectCreated?.(project);
        } catch (err) {
            setUploading(false);
            setUploadProgress(0);
            setError(err?.response?.data?.detail || "Upload failed. Try again.");
        }
    };

    const langOptions = [
        { value: "ja", label: "🇯🇵 Japonês" },
        { value: "ko", label: "🇰🇷 Coreano" },
        { value: "zh", label: "🇨🇳 Chinês" },
        { value: "en", label: "🇬🇧 Inglês" },
    ];

    return (
        <div className="w-full max-w-lg space-y-5 animate-fade-in">
            {/* Drop Area */}
            <div
                {...getRootProps()}
                className={`
          card group cursor-pointer p-10 text-center
          transition-all duration-500 ease-out
          ${isDragActive
                        ? "border-sakura-400/40 shadow-sakura-glow scale-[1.02] bg-sakura-400/5"
                        : "hover:border-sakura-400/15 hover:shadow-sakura-sm"
                    }
          ${isUploading ? "pointer-events-none opacity-60" : ""}
        `}
            >
                <input {...getInputProps()} />

                <div className="flex flex-col items-center gap-4">
                    {/* Icon */}
                    <div
                        className={`
              flex h-16 w-16 items-center justify-center rounded-2xl
              transition-all duration-300
              ${isDragActive
                                ? "bg-sakura-400/20 text-sakura-300 shadow-sakura-md scale-110"
                                : "bg-sakura-400/10 text-sakura-400 group-hover:bg-sakura-400/15"
                            }
            `}
                    >
                        {isUploading ? (
                            <Loader2 size={28} strokeWidth={1.5} className="animate-spin" />
                        ) : droppedFile ? (
                            droppedFile.name.endsWith(".zip") ? (
                                <FileArchive size={28} strokeWidth={1.5} />
                            ) : (
                                <Image size={28} strokeWidth={1.5} />
                            )
                        ) : (
                            <Upload size={28} strokeWidth={1.5} />
                        )}
                    </div>

                    {/* Text */}
                    {isDragActive ? (
                        <p className="text-sm font-medium text-sakura-300 text-glow-sakura">
                            Solte o arquivo aqui...
                        </p>
                    ) : droppedFile ? (
                        <div>
                            <p className="text-sm font-medium text-neutral-200">
                                {droppedFile.name}
                            </p>
                            <p className="text-xs text-neutral-500 mt-1">
                                {(droppedFile.size / (1024 * 1024)).toFixed(1)} MB — Clique para
                                trocar
                            </p>
                        </div>
                    ) : (
                        <div>
                            <p className="text-sm font-medium text-neutral-300">
                                Arraste seu ZIP ou imagens aqui
                            </p>
                            <p className="text-xs text-neutral-600 mt-1">
                                .zip, .png, .jpg, .webp — até 500MB
                            </p>
                        </div>
                    )}
                </div>

                {/* Progress bar */}
                {isUploading && (
                    <div className="mt-6 w-full">
                        <div className="h-1.5 w-full rounded-full bg-ink-50/30 overflow-hidden">
                            <div
                                className="h-full rounded-full bg-gradient-to-r from-sakura-400 to-sakura-500 transition-all duration-300"
                                style={{ width: `${uploadProgress}%` }}
                            />
                        </div>
                        <p className="text-xs text-neutral-500 mt-2">
                            Enviando... {uploadProgress}%
                        </p>
                    </div>
                )}
            </div>

            {/* Config Fields (shown after file selection) */}
            {droppedFile && !isUploading && (
                <div className="space-y-3 animate-fade-in">
                    {/* Project Name */}
                    <div>
                        <label className="block text-xs font-medium text-neutral-500 mb-1.5">
                            Nome do Projeto
                        </label>
                        <input
                            type="text"
                            value={projectName}
                            onChange={(e) => setProjectName(e.target.value)}
                            placeholder="Ex: One Piece Cap. 1"
                            className="w-full rounded-xl border border-white/[0.06] bg-ink-600 px-4 py-2.5 text-sm text-neutral-200 placeholder:text-neutral-600 outline-none focus:border-sakura-400/30 focus:shadow-sakura-sm transition-all"
                        />
                    </div>

                    {/* Language Selector */}
                    <div>
                        <label className="block text-xs font-medium text-neutral-500 mb-1.5">
                            Idioma Original
                        </label>
                        <div className="flex gap-2">
                            {langOptions.map((opt) => (
                                <button
                                    key={opt.value}
                                    onClick={() => setSourceLang(opt.value)}
                                    className={`
                    flex-1 rounded-xl border px-3 py-2 text-xs font-medium transition-all duration-200
                    ${sourceLang === opt.value
                                            ? "border-sakura-400/30 bg-sakura-400/10 text-sakura-300"
                                            : "border-white/[0.04] bg-ink-600 text-neutral-500 hover:text-neutral-300 hover:border-white/[0.08]"
                                        }
                  `}
                                >
                                    {opt.label}
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Error */}
                    {error && (
                        <p className="text-xs text-red-400 bg-red-400/10 rounded-lg px-3 py-2">
                            {error}
                        </p>
                    )}

                    {/* Upload Button */}
                    <button
                        onClick={handleUpload}
                        className="btn-sakura w-full flex items-center justify-center gap-2 py-3"
                    >
                        <Upload size={16} />
                        Criar Projeto e Enviar
                    </button>
                </div>
            )}
        </div>
    );
}
