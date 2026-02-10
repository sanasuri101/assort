import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
    Sparkles,
    ThumbsUp,
    ThumbsDown,
    ExternalLink,
    BrainCircuit,
    AlertCircle
} from 'lucide-react';
import { cn } from '@/lib/utils';

export default function LearningLoop() {
    const queryClient = useQueryClient();

    const { data: candidates, isLoading } = useQuery({
        queryKey: ['candidates'],
        queryFn: async () => {
            const res = await axios.get('http://localhost:8000/api/dashboard/learning/candidates');
            return res.data;
        },
    });

    const approveMutation = useMutation({
        mutationFn: async (id: string) => {
            await axios.post(`http://localhost:8000/api/dashboard/learning/approve/${id}`);
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['candidates'] });
        },
    });

    const rejectMutation = useMutation({
        mutationFn: async (id: string) => {
            await axios.delete(`http://localhost:8000/api/dashboard/learning/reject/${id}`);
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['candidates'] });
        },
    });

    if (isLoading) return <div className="p-8">Loading learning candidates...</div>;

    return (
        <div className="space-y-6 animate-in fade-in duration-500">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Learning Loop</h1>
                    <p className="text-muted-foreground mt-1">Review knowledge extracted by AI from recent patient interactions.</p>
                </div>
            </div>

            <div className="grid gap-6">
                {candidates?.map((cand: any) => (
                    <Card key={cand.id} className="overflow-hidden border-2 border-indigo-50 hover:border-indigo-100 transition-all shadow-sm hover:shadow-md">
                        <div className="flex flex-col md:flex-row">
                            <div className="p-6 flex-1 space-y-4">
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-2">
                                        <Badge variant="outline" className="bg-indigo-50 text-indigo-700 border-indigo-100 px-2 py-0.5">
                                            <Sparkles className="h-3 w-3 mr-1" /> AI Suggestion
                                        </Badge>
                                        <Badge variant="outline" className={cn(
                                            "px-2 py-0.5",
                                            cand.confidence > 0.8 ? "bg-emerald-50 text-emerald-700 border-emerald-100" : "bg-amber-50 text-amber-700 border-amber-100"
                                        )}>
                                            {Math.round(cand.confidence * 100)}% Confidence
                                        </Badge>
                                    </div>
                                    <span className="text-xs text-muted-foreground">Source: {cand.source_call_id}</span>
                                </div>

                                <div className="space-y-3">
                                    <div className="space-y-1">
                                        <label className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">Detected Question</label>
                                        <p className="text-base font-semibold text-slate-900 leading-tight">
                                            {cand.question}
                                        </p>
                                    </div>
                                    <div className="space-y-1">
                                        <label className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">Proposed Answer</label>
                                        <div className="bg-slate-50 p-3 rounded-lg border border-slate-100 text-sm text-slate-700 italic">
                                            "{cand.answer}"
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <div className="bg-slate-50/50 border-t md:border-t-0 md:border-l p-6 md:w-64 flex flex-col justify-center gap-3">
                                <Button
                                    className="w-full gap-2 bg-emerald-600 hover:bg-emerald-700"
                                    onClick={() => approveMutation.mutate(cand.id)}
                                    disabled={approveMutation.isPending}
                                >
                                    <ThumbsUp className="h-4 w-4" /> Approve & Add
                                </Button>
                                <Button
                                    variant="outline"
                                    className="w-full gap-2 text-red-600 hover:text-red-700 hover:bg-red-50 border-red-100"
                                    onClick={() => rejectMutation.mutate(cand.id)}
                                >
                                    <ThumbsDown className="h-4 w-4" /> Dismiss
                                </Button>
                                <Button variant="ghost" size="sm" className="w-full text-xs gap-1 text-muted-foreground">
                                    View Source Call <ExternalLink className="h-3 w-3" />
                                </Button>
                            </div>
                        </div>
                    </Card>
                ))}

                {candidates?.length === 0 && (
                    <div className="flex flex-col items-center justify-center py-20 bg-muted/20 rounded-2xl border-2 border-dashed">
                        <BrainCircuit className="h-12 w-12 text-muted-foreground mb-4 opacity-20" />
                        <h3 className="text-lg font-medium text-muted-foreground">Queue is empty</h3>
                        <p className="text-sm text-muted-foreground text-center max-w-xs mt-2">
                            AI is constantly analyzing new calls. Check back soon for more suggestions!
                        </p>
                    </div>
                )}
            </div>

            <div className="flex items-center gap-3 p-4 rounded-xl bg-amber-50 border border-amber-100 text-amber-900">
                <AlertCircle className="h-5 w-5 shrink-0" />
                <p className="text-sm">
                    <strong>Important:</strong> Approving a suggestion will immediately add it to your Knowledge Base and re-calculate AI vectors. The bot will begin using this information for all future calls.
                </p>
            </div>
        </div>
    );
}
