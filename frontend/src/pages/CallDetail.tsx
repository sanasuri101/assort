import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { useParams, useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
    ArrowLeft,
    User,
    Bot,
    Wrench,
    ShieldCheck,
    PhoneCall,
    Info
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Separator } from '@/components/ui/separator';

export default function CallDetail() {
    const { callId } = useParams();
    const navigate = useNavigate();

    const { data: call, isLoading } = useQuery({
        queryKey: ['call', callId],
        queryFn: async () => {
            const res = await axios.get(`http://localhost:8000/api/dashboard/calls/${callId}`);
            return res.data;
        },
    });

    if (isLoading) return <div className="p-8">Loading call details...</div>;

    return (
        <div className="max-w-4xl mx-auto space-y-6 animate-in slide-in-from-bottom-4 duration-500">
            <div className="flex items-center justify-between">
                <Button variant="ghost" className="gap-2" onClick={() => navigate('/calls')}>
                    <ArrowLeft className="h-4 w-4" /> Back to History
                </Button>
                <div className="flex gap-2">
                    <Button variant="outline" size="sm">Download Transcript</Button>
                    <Button variant="outline" size="sm">Play Recording</Button>
                </div>
            </div>

            <div className="grid gap-6 md:grid-cols-3">
                {/* Metadata Card */}
                <Card className="md:col-span-1 h-fit sticky top-6">
                    <CardHeader>
                        <CardTitle className="text-sm font-medium flex items-center gap-2">
                            <Info className="h-4 w-4 text-blue-500" /> Call Metadata
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="space-y-1">
                            <label className="text-xs text-muted-foreground uppercase font-bold">Patient</label>
                            <p className="font-medium">{call.patient_name || "Unknown"}</p>
                        </div>
                        <div className="space-y-1">
                            <label className="text-xs text-muted-foreground uppercase font-bold">Outcome</label>
                            <div>
                                <Badge className="bg-emerald-100 text-emerald-700 border-emerald-200">
                                    {call.outcome}
                                </Badge>
                            </div>
                        </div>
                        <div className="space-y-1">
                            <label className="text-xs text-muted-foreground uppercase font-bold">Started At</label>
                            <p className="text-sm">{new Date(call.started_at).toLocaleString()}</p>
                        </div>
                        <div className="space-y-1">
                            <label className="text-xs text-muted-foreground uppercase font-bold">Duration</label>
                            <p className="text-sm">{Math.floor(call.duration_sec / 60)}m {call.duration_sec % 60}s</p>
                        </div>
                        <Separator />
                        <div className="pt-2">
                            <label className="text-xs text-muted-foreground uppercase font-bold">AI Summary</label>
                            <p className="text-sm text-muted-foreground mt-1 leading-relaxed italic">
                                "{call.summary}"
                            </p>
                        </div>
                    </CardContent>
                </Card>

                {/* Visual Flow Transcript */}
                <Card className="md:col-span-2">
                    <CardHeader className="border-b bg-muted/30">
                        <CardTitle className="text-lg flex items-center gap-2">
                            <PhoneCall className="h-5 w-5 text-indigo-500" /> Conversation Flow
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="p-0 pt-6">
                        <div className="relative px-6 pb-8 space-y-8">
                            {/* Timeline Connector */}
                            <div className="absolute left-[39px] top-6 bottom-8 w-0.5 bg-muted" />

                            {call.transcript.map((segment: any, index: number) => {
                                const isBot = segment.role === 'assistant';
                                const isUser = segment.role === 'user';
                                const isTool = segment.role === 'tool';

                                if (isTool) {
                                    const args = JSON.parse(segment.tool_args || '{}');
                                    const result = JSON.parse(segment.tool_result || '{}');
                                    const isVerify = segment.tool_name === 'verify_patient';

                                    return (
                                        <div key={index} className="relative z-10 flex flex-col gap-3 pl-12">
                                            <div className="absolute left-[-11px] top-2 h-6 w-6 rounded-full bg-indigo-600 flex items-center justify-center text-white ring-4 ring-background">
                                                <Wrench className="h-3.5 w-3.5" />
                                            </div>
                                            <div className="bg-indigo-50/50 border border-indigo-100 rounded-xl p-4 shadow-sm">
                                                <div className="flex items-center justify-between mb-3">
                                                    <div className="flex items-center gap-2">
                                                        {isVerify ? <ShieldCheck className="h-4 w-4 text-indigo-600" /> : <Wrench className="h-4 w-4 text-indigo-600" />}
                                                        <span className="text-sm font-bold text-indigo-900 uppercase tracking-tight">
                                                            {segment.tool_name.replace('_', ' ')}
                                                        </span>
                                                    </div>
                                                    <Badge variant="outline" className="bg-white/80 text-[10px] font-mono border-indigo-200">
                                                        SUCCESS
                                                    </Badge>
                                                </div>

                                                <div className="grid grid-cols-2 gap-4 text-xs">
                                                    <div className="space-y-1.5">
                                                        <p className="text-indigo-700 font-semibold uppercase opacity-70">Input</p>
                                                        <div className="bg-white/80 p-2 rounded-md border border-indigo-100 font-mono">
                                                            {Object.entries(args).map(([k, v]) => (
                                                                <div key={k} className="flex justify-between gap-2">
                                                                    <span className="opacity-50">{k}:</span>
                                                                    <span className="truncate">{String(v)}</span>
                                                                </div>
                                                            ))}
                                                        </div>
                                                    </div>
                                                    <div className="space-y-1.5">
                                                        <p className="text-emerald-700 font-semibold uppercase opacity-70">Result</p>
                                                        <div className="bg-emerald-50/80 p-2 rounded-md border border-emerald-100 font-mono text-emerald-800">
                                                            {Object.entries(result).map(([k, v]) => (
                                                                <div key={k} className="flex justify-between gap-2">
                                                                    <span className="opacity-50">{k}:</span>
                                                                    <span className="truncate">{String(v)}</span>
                                                                </div>
                                                            ))}
                                                        </div>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    );
                                }

                                return (
                                    <div key={index} className={cn(
                                        "relative z-10 flex gap-4",
                                        isUser ? "flex-row-reverse" : "flex-row"
                                    )}>
                                        {/* Avatar */}
                                        <div className={cn(
                                            "h-8 w-8 rounded-full flex items-center justify-center ring-4 ring-background shrink-0",
                                            isBot ? "bg-indigo-100 text-indigo-600" : "bg-emerald-100 text-emerald-600"
                                        )}>
                                            {isBot ? <Bot className="h-4 w-4" /> : <User className="h-4 w-4" />}
                                        </div>

                                        {/* Bubble */}
                                        <div className={cn(
                                            "max-w-[80%] rounded-2xl px-4 py-3 text-sm shadow-sm",
                                            isBot
                                                ? "bg-indigo-600 text-white rounded-tl-none"
                                                : "bg-white border border-slate-200 text-slate-900 rounded-tr-none"
                                        )}>
                                            <p className="leading-relaxed">{segment.content}</p>
                                            <div className={cn(
                                                "text-[10px] mt-2 opacity-60",
                                                isBot ? "text-indigo-100" : "text-slate-400"
                                            )}>
                                                {segment.timestamp.toFixed(1)}s
                                            </div>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
