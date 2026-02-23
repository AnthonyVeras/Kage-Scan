import { Outlet, NavLink, useLocation } from "react-router-dom";
import {
    Upload,
    Layers,
    Settings,
    BookOpen,
    Sparkles,
    Download,
} from "lucide-react";

/* ── Sidebar Navigation Items ─────────────────────────────── */
const NAV_ITEMS = [
    { to: "/", icon: Upload, label: "Upload" },
    { to: "/projects", icon: Layers, label: "Projects" },
    { to: "/settings", icon: Settings, label: "Settings" },
];

/* ── Sidebar ──────────────────────────────────────────────── */
function Sidebar() {
    return (
        <aside className="fixed left-0 top-0 z-40 flex h-screen w-[72px] flex-col items-center gap-1 border-r border-white/[0.04] bg-ink-900/90 backdrop-blur-xl py-6">
            {/* Logo mark */}
            <div className="mb-8 flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-sakura-400 to-sakura-600 shadow-sakura-md">
                <BookOpen size={20} className="text-white" />
            </div>

            {/* Nav icons */}
            <nav className="flex flex-1 flex-col items-center gap-1">
                {NAV_ITEMS.map(({ to, icon: Icon, label }) => (
                    <NavLink
                        key={to}
                        to={to}
                        className={({ isActive }) =>
                            `icon-btn group relative ${isActive ? "active" : ""}`
                        }
                        title={label}
                    >
                        <Icon size={20} strokeWidth={1.8} />

                        {/* Tooltip */}
                        <span className="pointer-events-none absolute left-full ml-3 whitespace-nowrap rounded-lg bg-ink-500 px-2.5 py-1 text-xs font-medium text-neutral-300 opacity-0 shadow-lg transition-all duration-200 group-hover:opacity-100 group-hover:translate-x-0 -translate-x-1">
                            {label}
                        </span>
                    </NavLink>
                ))}
            </nav>

            {/* Bottom: decorative spark */}
            <div className="mt-auto">
                <Sparkles size={16} className="text-sakura-400/30 animate-pulse-slow" />
            </div>
        </aside>
    );
}

/* ── Navbar (Top Bar) ─────────────────────────────────────── */
function Navbar() {
    const location = useLocation();

    const pageTitle = () => {
        if (location.pathname.startsWith("/project/")) return "Editor";
        if (location.pathname === "/projects") return "Projects";
        if (location.pathname === "/settings") return "Settings";
        return "Upload";
    };

    return (
        <header className="glass-surface-strong sticky top-0 z-30 flex h-14 items-center justify-between border-b border-white/[0.04] px-6">
            {/* Left: Logo + Page Title */}
            <div className="flex items-center gap-4">
                <h1 className="font-display text-lg font-bold tracking-tight">
                    <span className="text-sakura-gradient">Kage</span>
                    <span className="text-neutral-400 font-medium ml-1">Scan</span>
                </h1>

                <div className="divider-v h-5" />

                <span className="text-sm font-medium text-neutral-500">
                    {pageTitle()}
                </span>
            </div>

            {/* Right: Action bar */}
            <div className="flex items-center gap-2">
                <button className="btn-ghost flex items-center gap-2">
                    <Download size={15} />
                    <span>Export</span>
                </button>
            </div>
        </header>
    );
}

/* ── Layout Shell ─────────────────────────────────────────── */
export default function Layout() {
    return (
        <div className="flex min-h-screen bg-ink-900">
            <Sidebar />

            {/* Main area — offset by sidebar width */}
            <div className="ml-[72px] flex flex-1 flex-col">
                <Navbar />

                <main className="flex-1 p-6 animate-fade-in">
                    <Outlet />
                </main>
            </div>
        </div>
    );
}
