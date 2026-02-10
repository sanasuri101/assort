import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import {
    Plus,
    Trash2,
    Search,
    BookOpen,
    HelpCircle,
    AlertCircle
} from 'lucide-react';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from "@/components/ui/dialog";

export default function Knowledge() {
    const queryClient = useQueryClient();
    const [search, setSearch] = useState('');
    const [isAddOpen, setIsAddOpen] = useState(false);
    const [newKey, setNewKey] = useState('');
    const [newContent, setNewContent] = useState('');

    const { data: items, isLoading } = useQuery({
        queryKey: ['knowledge'],
        queryFn: async () => {
            const res = await axios.get('http://localhost:8000/api/dashboard/knowledge');
            return res.data;
        },
    });

    const addMutation = useMutation({
        mutationFn: async (item: { key: string; content: string }) => {
            await axios.post('http://localhost:8000/api/dashboard/knowledge', item);
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['knowledge'] });
            setIsAddOpen(false);
            setNewKey('');
            setNewContent('');
        },
    });

    const deleteMutation = useMutation({
        mutationFn: async (key: string) => {
            await axios.delete(`http://localhost:8000/api/dashboard/knowledge/${key}`);
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['knowledge'] });
        },
    });

    const filteredItems = items?.filter((i: any) =>
        i.key.toLowerCase().includes(search.toLowerCase()) ||
        i.content.toLowerCase().includes(search.toLowerCase())
    );

    if (isLoading) return <div className="p-8">Loading knowledge base...</div>;

    return (
        <div className="space-y-6 animate-in fade-in duration-500">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Knowledge Base</h1>
                    <p className="text-muted-foreground mt-1">Manage the office FAQs that power the voice AI.</p>
                </div>

                <Dialog open={isAddOpen} onOpenChange={setIsAddOpen}>
                    <DialogTrigger asChild>
                        <Button className="gap-2">
                            <Plus className="h-4 w-4" /> Add FAQ Entry
                        </Button>
                    </DialogTrigger>
                    <DialogContent>
                        <DialogHeader>
                            <DialogTitle>Add FAQ Entry</DialogTitle>
                            <DialogDescription>
                                Note: Saving will trigger AI re-embedding. This item will be used by the bot immediately.
                            </DialogDescription>
                        </DialogHeader>
                        <div className="space-y-4 py-4">
                            <div className="space-y-2">
                                <label className="text-sm font-medium">Topic Key (e.g., insurance, hours)</label>
                                <Input value={newKey} onChange={e => setNewKey(e.target.value)} placeholder="e.g. holiday_hours" />
                            </div>
                            <div className="space-y-2">
                                <label className="text-sm font-medium">Answer Content</label>
                                <Textarea
                                    value={newContent}
                                    onChange={e => setNewContent(e.target.value)}
                                    placeholder="Provide the exact information the bot should say..."
                                    className="min-h-[100px]"
                                />
                            </div>
                        </div>
                        <DialogFooter>
                            <Button variant="outline" onClick={() => setIsAddOpen(false)}>Cancel</Button>
                            <Button onClick={() => addMutation.mutate({ key: newKey, content: newContent })} disabled={!newKey || !newContent}>
                                {addMutation.isPending ? "Generating Embedding..." : "Save Entry"}
                            </Button>
                        </DialogFooter>
                    </DialogContent>
                </Dialog>
            </div>

            <div className="flex items-center gap-4">
                <div className="relative flex-1 max-w-sm">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                    <Input
                        placeholder="Search FAQs..."
                        className="pl-9"
                        value={search}
                        onChange={e => setSearch(e.target.value)}
                    />
                </div>
            </div>

            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                {filteredItems?.map((item: any) => (
                    <Card key={item.key} className="group hover:border-blue-200 transition-colors">
                        <CardHeader className="pb-3">
                            <div className="flex items-start justify-between gap-2">
                                <div className="flex items-center gap-2">
                                    <div className="p-1.5 bg-blue-50 text-blue-600 rounded">
                                        <HelpCircle className="h-4 w-4" />
                                    </div>
                                    <CardTitle className="text-base capitalize">{item.key.replace('_', ' ')}</CardTitle>
                                </div>
                                <Button
                                    variant="ghost"
                                    size="icon"
                                    className="text-muted-foreground hover:text-red-600 opacity-0 group-hover:opacity-100 transition-opacity"
                                    onClick={() => deleteMutation.mutate(item.key)}
                                >
                                    <Trash2 className="h-4 w-4" />
                                </Button>
                            </div>
                        </CardHeader>
                        <CardContent>
                            <p className="text-sm text-muted-foreground leading-relaxed">
                                {item.content}
                            </p>
                        </CardContent>
                    </Card>
                ))}

                {filteredItems?.length === 0 && (
                    <div className="col-span-full py-12 text-center border-2 border-dashed rounded-xl">
                        <BookOpen className="h-10 w-10 text-muted-foreground mx-auto mb-4 opacity-20" />
                        <p className="text-muted-foreground">No FAQ entries found matching "{search}"</p>
                    </div>
                )}
            </div>

            <Card className="bg-blue-50/50 border-blue-100">
                <CardContent className="p-6">
                    <div className="flex gap-4">
                        <AlertCircle className="h-5 w-5 text-blue-600 mt-0.5" />
                        <div className="space-y-1">
                            <h4 className="font-semibold text-blue-900 text-sm">Advanced Tips</h4>
                            <p className="text-sm text-blue-800 opacity-80 leading-relaxed">
                                The voice AI uses these entries via vector similarity. For best results, keep each entry focused on a single topic. If you find the bot is confusing two topics, try combining them into one entry or differentiating the keywords.
                            </p>
                        </div>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}
