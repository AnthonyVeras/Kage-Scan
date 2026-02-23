/**
 * Kage Scan — Home Page
 * Landing page with upload zone. Redirects to editor after successful upload.
 */

import { useNavigate } from "react-router-dom";
import { Sparkles } from "lucide-react";
import UploadZone from "../components/Upload/UploadZone";
import useProjectStore from "../stores/projectStore";

export default function HomePage() {
    const navigate = useNavigate();
    const setProject = useProjectStore((s) => s.setProject);

    const handleProjectCreated = (project) => {
        setProject(project);
        navigate(`/project/${project.id}`);
    };

    return (
        <div className="flex flex-col items-center justify-center min-h-[calc(100vh-8rem)] animate-fade-in">
            {/* Hero */}
            <div className="text-center mb-10">
                <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-sakura-400/20 bg-sakura-400/5 text-sakura-300 text-xs font-medium mb-6 animate-fade-in">
                    <Sparkles size={12} />
                    AI-Powered Manga Translation
                </div>

                <h2 className="font-display text-4xl font-bold tracking-tight mb-3">
                    <span className="text-sakura-gradient">Translate</span>
                    <span className="text-neutral-200"> your manga</span>
                </h2>

                <p className="text-neutral-500 text-sm max-w-md mx-auto leading-relaxed">
                    Envie um ZIP com páginas de mangá e deixe a IA detectar, extrair,
                    traduzir e compor — tudo em um pipeline automatizado.
                </p>
            </div>

            {/* Upload Zone */}
            <UploadZone onProjectCreated={handleProjectCreated} />
        </div>
    );
}
