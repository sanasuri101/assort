import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
    Building2,
    Clock,
    ShieldCheck,
    Save,
    X,
    Plus
} from 'lucide-react';

export default function Settings() {
    const queryClient = useQueryClient();
    const [practiceName, setPracticeName] = useState('');
    const [officeHours, setOfficeHours] = useState('');
    const [insurancePlans, setInsurancePlans] = useState<string[]>([]);
    const [newPlan, setNewPlan] = useState('');

    const { data: settings, isLoading } = useQuery({
        queryKey: ['settings'],
        queryFn: async () => {
            const res = await axios.get('http://localhost:8000/api/dashboard/settings');
            return res.data;
        },
    });

    useEffect(() => {
        if (settings) {
            setPracticeName(settings.practice_name);
            setOfficeHours(settings.office_hours);
            setInsurancePlans(settings.insurance_plans);
        }
    }, [settings]);

    const saveMutation = useMutation({
        mutationFn: async (updated: any) => {
            await axios.post('http://localhost:8000/api/dashboard/settings', updated);
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['settings'] });
            // Show success notification (toast) if available, or just log
        },
    });

    const addPlan = () => {
        if (newPlan && !insurancePlans.includes(newPlan)) {
            setInsurancePlans([...insurancePlans, newPlan]);
            setNewPlan('');
        }
    };

    const removePlan = (plan: string) => {
        setInsurancePlans(insurancePlans.filter(p => p !== plan));
    };

    if (isLoading) return <div className="p-8">Loading settings...</div>;

    return (
        <div className="max-w-2xl mx-auto space-y-8 animate-in fade-in duration-500">
            <div>
                <h1 className="text-3xl font-bold tracking-tight text-[#0a192f]">General Settings</h1>
                <p className="text-muted-foreground mt-1">Configure global parameters for your AI agent.</p>
            </div>

            <div className="grid gap-6">
                {/* Practice Identity */}
                <Card>
                    <CardHeader>
                        <CardTitle className="text-lg flex items-center gap-2">
                            <Building2 className="h-5 w-5 text-blue-600" /> Practice Identity
                        </CardTitle>
                        <CardDescription>How the bot identifies your office to patients.</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="space-y-2">
                            <label className="text-sm font-medium">Official Practice Name</label>
                            <Input
                                value={practiceName}
                                onChange={e => setPracticeName(e.target.value)}
                                placeholder="e.g. Valley Family Medicine"
                            />
                        </div>
                    </CardContent>
                </Card>

                {/* Operational Hours */}
                <Card>
                    <CardHeader>
                        <CardTitle className="text-lg flex items-center gap-2">
                            <Clock className="h-5 w-5 text-indigo-600" /> Operational Hours
                        </CardTitle>
                        <CardDescription>The bot uses this to determine if the office is currently open.</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="space-y-2">
                            <label className="text-sm font-medium">Standard Hours Description</label>
                            <Input
                                value={officeHours}
                                onChange={e => setOfficeHours(e.target.value)}
                                placeholder="e.g. Mon-Fri 8am-5pm"
                            />
                            <p className="text-xs text-muted-foreground italic">
                                Example: "Mon-Fri 8:00 AM - 5:00 PM, Saturday 9:00 AM - 1:00 PM"
                            </p>
                        </div>
                    </CardContent>
                </Card>

                {/* Clinical Config (Insurance) */}
                <Card>
                    <CardHeader>
                        <CardTitle className="text-lg flex items-center gap-2">
                            <ShieldCheck className="h-5 w-5 text-emerald-600" /> Insurance Verification
                        </CardTitle>
                        <CardDescription>List of supported insurance networks the bot can confirm.</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="space-y-4">
                            <label className="text-sm font-medium">Accepted Networks</label>
                            <div className="flex flex-wrap gap-2">
                                {insurancePlans.map(plan => (
                                    <Badge key={plan} variant="secondary" className="px-3 py-1 bg-blue-50 text-blue-700 hover:bg-blue-100 border-blue-200">
                                        {plan}
                                        <button onClick={() => removePlan(plan)} className="ml-2 hover:text-red-600">
                                            <X className="h-3 w-3" />
                                        </button>
                                    </Badge>
                                ))}
                            </div>

                            <div className="flex gap-2">
                                <Input
                                    value={newPlan}
                                    onChange={e => setNewPlan(e.target.value)}
                                    placeholder="Add network (e.g. Kaiser Permanente)"
                                    onKeyDown={e => e.key === 'Enter' && addPlan()}
                                />
                                <Button variant="outline" size="icon" onClick={addPlan}>
                                    <Plus className="h-4 w-4" />
                                </Button>
                            </div>
                        </div>
                    </CardContent>
                </Card>
            </div>

            <div className="flex items-center justify-end gap-3 pt-4 border-t">
                <Button variant="ghost">Revert Changes</Button>
                <Button
                    className="gap-2 bg-[#1a73e8] hover:bg-[#1557b0]"
                    disabled={saveMutation.isPending}
                    onClick={() => saveMutation.mutate({
                        practice_name: practiceName,
                        office_hours: officeHours,
                        insurance_plans: insurancePlans
                    })}
                >
                    <Save className="h-4 w-4" /> {saveMutation.isPending ? "Saving..." : "Save Settings"}
                </Button>
            </div>
        </div>
    );
}
