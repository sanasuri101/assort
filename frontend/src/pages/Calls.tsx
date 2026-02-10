import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Search, ExternalLink, Calendar as CalendarIcon, Clock } from 'lucide-react';

const outcomeStyles: Record<string, string> = {
    scheduled: "bg-emerald-100 text-emerald-700 hover:bg-emerald-100 border-emerald-200",
    answered: "bg-blue-100 text-blue-700 hover:bg-blue-100 border-blue-200",
    transferred: "bg-amber-100 text-amber-700 hover:bg-amber-100 border-amber-200",
    abandoned: "bg-slate-100 text-slate-700 hover:bg-slate-100 border-slate-200",
    emergency: "bg-red-100 text-red-700 hover:bg-red-100 border-red-200",
};

export default function Calls() {
    const navigate = useNavigate();
    const { data: calls, isLoading } = useQuery({
        queryKey: ['calls'],
        queryFn: async () => {
            const res = await axios.get('http://localhost:8000/api/dashboard/calls');
            return res.data;
        },
    });

    if (isLoading) return <div className="p-8">Loading calls...</div>;

    return (
        <div className="space-y-6 animate-in fade-in duration-500">
            <div>
                <h1 className="text-3xl font-bold tracking-tight">Call History</h1>
                <p className="text-muted-foreground mt-1">Review and audit all patient interactions.</p>
            </div>

            <div className="flex items-center gap-4">
                <div className="relative flex-1 max-w-sm">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                    <Input placeholder="Search by patient name or summary..." className="pl-9" />
                </div>
                <Button variant="outline" className="gap-2">
                    <CalendarIcon className="h-4 w-4" /> Last 7 Days
                </Button>
            </div>

            <div className="rounded-xl border bg-card overflow-hidden">
                <Table>
                    <TableHeader>
                        <TableRow className="bg-muted/50 hover:bg-muted/50">
                            <TableHead className="w-[180px]">Date & Time</TableHead>
                            <TableHead>Patient</TableHead>
                            <TableHead>Outcome</TableHead>
                            <TableHead>Duration</TableHead>
                            <TableHead className="max-w-[300px]">Summary</TableHead>
                            <TableHead className="text-right">Actions</TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {calls?.map((call: any) => (
                            <TableRow key={call.call_id} className="hover:bg-muted/30 transition-colors">
                                <TableCell className="font-medium">
                                    <div className="flex flex-col">
                                        <span>{new Date(call.started_at).toLocaleDateString()}</span>
                                        <span className="text-xs text-muted-foreground">
                                            {new Date(call.started_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                        </span>
                                    </div>
                                </TableCell>
                                <TableCell>{call.patient_name || "Unknown Caller"}</TableCell>
                                <TableCell>
                                    <Badge variant="outline" className={outcomeStyles[call.outcome]}>
                                        {call.outcome.charAt(0).toUpperCase() + call.outcome.slice(1)}
                                    </Badge>
                                </TableCell>
                                <TableCell>
                                    <div className="flex items-center gap-1.5 text-muted-foreground">
                                        <Clock className="h-3 w-3" />
                                        {Math.floor(call.duration_sec / 60)}m {call.duration_sec % 60}s
                                    </div>
                                </TableCell>
                                <TableCell className="max-w-[300px] truncate text-muted-foreground italic">
                                    "{call.summary}"
                                </TableCell>
                                <TableCell className="text-right">
                                    <Button
                                        variant="ghost"
                                        size="sm"
                                        className="gap-2 text-blue-600 hover:text-blue-700 hover:bg-blue-50"
                                        onClick={() => navigate(`/calls/${call.call_id}`)}
                                    >
                                        Details <ExternalLink className="h-3 w-3" />
                                    </Button>
                                </TableCell>
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            </div>
        </div>
    );
}
