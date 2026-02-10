import { useLocation, NavLink } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import {
    LayoutDashboard,
    PhoneCall,
    BookOpen,
    BrainCircuit,
    Settings as SettingsIcon,
    LogOut,
    ChevronRight
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { Outlet } from 'react-router-dom';
import { LiveMonitor } from '@/components/LiveMonitor';

export default function DashboardLayout() {
    const { user, providers, login, logout } = useAuth();
    const { pathname } = useLocation();


    return (
        <div className="flex h-screen bg-[#f8fafc] text-slate-900 font-sans selection:bg-blue-100">
            {/* Sidebar */}
            <aside className="w-72 bg-[#0a192f] text-white flex flex-col shadow-xl z-30">
                <div className="p-8 pb-4">
                    <div className="flex items-center gap-3 mb-8">
                        <div className="h-10 w-10 bg-blue-600 rounded-xl flex items-center justify-center shadow-lg shadow-blue-500/20">
                            <PhoneCall className="h-6 w-6 text-white" />
                        </div>
                        <h1 className="text-xl font-bold tracking-tight">Assort Health</h1>
                    </div>

                    <nav className="space-y-1">
                        <SidebarLink
                            to="/"
                            icon={LayoutDashboard}
                            label="Dashboard"
                            active={pathname === '/'}
                        />
                        <SidebarLink
                            to="/calls"
                            icon={PhoneCall}
                            label="Call History"
                            active={pathname.startsWith('/calls')}
                        />
                        <SidebarLink
                            to="/knowledge"
                            icon={BookOpen}
                            label="Knowledge Base"
                            active={pathname === '/knowledge'}
                        />
                        <SidebarLink
                            to="/learning"
                            icon={BrainCircuit}
                            label="Learning Loop"
                            active={pathname === '/learning'}
                        />
                        <SidebarLink
                            to="/settings"
                            icon={SettingsIcon}
                            label="Settings"
                            active={pathname === '/settings'}
                        />
                    </nav>
                </div>

                <div className="flex-1 px-4 py-8 border-t border-white/5">
                    <LiveMonitor />
                </div>

                <div className="p-6 border-t border-white/5">
                    <Button
                        variant="ghost"
                        className="w-full justify-start gap-3 text-slate-400 hover:text-white hover:bg-white/5"
                        onClick={logout}
                    >
                        <LogOut className="h-4 w-4" />
                        Sign Out
                    </Button>
                </div>
            </aside>

            {/* Main Content Area */}
            <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
                {/* Header */}
                <header className="h-16 bg-white border-b border-slate-200 flex items-center justify-between px-8 sticky top-0 z-20 shadow-sm">
                    <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-slate-500">Practice:</span>
                        <h2 className="text-sm font-bold text-slate-800 uppercase tracking-wide">
                            Valley Family Medicine
                        </h2>
                    </div>

                    <div className="flex items-center gap-4">
                        <div className="flex items-center gap-3 bg-slate-50 px-3 py-1.5 rounded-lg border border-slate-100">
                            <span className="text-xs font-semibold text-slate-500 uppercase tracking-tighter">Acting as:</span>
                            <Select value={user?.id} onValueChange={(val) => {
                                login(val);
                            }}>
                                <SelectTrigger className="h-8 border-none bg-transparent font-bold text-slate-900 focus:ring-0 w-[180px]">
                                    <SelectValue placeholder="Select Provider" />
                                </SelectTrigger>
                                <SelectContent>
                                    {providers.map((p) => (
                                        <SelectItem key={p.id} value={p.id}>
                                            {p.name}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                    </div>
                </header>

                {/* Page Content */}
                <main className="flex-1 overflow-y-auto p-8 custom-scrollbar">
                    <Outlet />
                </main>
            </div>
        </div>
    );
}

function SidebarLink({ to, icon: Icon, label, active }: any) {
    return (
        <NavLink
            to={to}
            className={cn(
                "flex items-center justify-between px-4 py-3 rounded-xl text-sm font-medium transition-all duration-200 group",
                active
                    ? "bg-blue-600 text-white shadow-lg shadow-blue-600/20"
                    : "text-slate-400 hover:text-white hover:bg-white/5"
            )}
        >
            <div className="flex items-center gap-3">
                <Icon className={cn("h-5 w-5", active ? "text-white" : "group-hover:text-blue-400")} />
                {label}
            </div>
            {active && <ChevronRight className="h-4 w-4 opacity-50" />}
        </NavLink>
    );
}
