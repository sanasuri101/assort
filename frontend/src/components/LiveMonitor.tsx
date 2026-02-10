import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import {
    Activity,
    Circle,
    User,
    MoreVertical
} from 'lucide-react';
import { cn } from '@/lib/utils';

export function LiveMonitor() {
    const { data: activeCalls, isLoading } = useQuery({
        queryKey: ['live-calls'],
        queryFn: async () => {
            const res = await axios.get('http://localhost:8000/api/dashboard/live');
            return res.data;
        },
        refetchInterval: 5000, // Poll every 5s for demo
    });

    if (isLoading || !activeCalls) return null;

    return (
        <div className="space-y-4">
            <div className="flex items-center justify-between px-2">
                <div className="flex items-center gap-2">
                    <Activity className="h-4 w-4 text-emerald-500 animate-pulse" />
                    <span className="text-xs font-bold uppercase tracking-widest text-[#94a3b8]">Live Activity</span>
                </div>
                <Badge className="bg-emerald-500/10 text-emerald-400 border-emerald-500/20 text-[10px]">
                    {activeCalls.length} Active
                </Badge>
            </div>

            <div className="space-y-2">
                {activeCalls.map((call: any) => (
                    <div key={call.call_id} className="group relative bg-white/5 border border-white/5 rounded-lg p-3 shadow-sm hover:border-blue-500/30 transition-all cursor-pointer">
                        <div className="flex items-center justify-between">
                            <div className="flex items-center gap-3">
                                <div className="relative">
                                    <div className="h-8 w-8 rounded-full bg-white/5 flex items-center justify-center text-slate-400">
                                        <User className="h-4 w-4" />
                                    </div>
                                    <Circle className="absolute -bottom-0.5 -right-0.5 h-2.5 w-2.5 fill-emerald-500 stroke-[#0a192f] stroke-2" />
                                </div>
                                <div>
                                    <p className="text-xs font-bold text-slate-200">{call.patient_name}</p>
                                    <p className="text-[10px] text-slate-500 flex items-center gap-1 capitalize">
                                        {call.status} • {Math.floor(call.duration_sec / 60)}:{(call.duration_sec % 60).toString().padStart(2, '0')}
                                    </p>
                                </div>
                            </div>
                            <Button className="h-6 w-6 opacity-0 group-hover:opacity-100 text-slate-500">
                                <MoreVertical className="h-3 w-3" />
                            </Button>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}

// Minimal Badge shim if ui/badge not accessible/defined in this file
function Badge({ children, className }: any) {
    return (
        <span className={cn("px-2 py-0.5 rounded-full text-[10px] font-medium border", className)}>
            {children}
        </span>
    );
}

// Minimal Button shim
function Button({ children, className, onClick }: any) {
    return (
        <button onClick={onClick} className={cn("inline-flex items-center justify-center rounded transition-colors", className)}>
            {children}
        </button>
    );
}
