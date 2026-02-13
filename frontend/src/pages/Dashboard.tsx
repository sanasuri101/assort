import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
    Phone,
    CheckCircle2,
    Clock,
    TrendingUp,
    PhoneIncoming,
    AlertCircle,
    Play
} from 'lucide-react';
import {
    AreaChart,
    Area,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    BarChart,
    Bar,
} from 'recharts';

const chartData = [
    { time: '08:00', calls: 5 },
    { time: '09:00', calls: 12 },
    { time: '10:00', calls: 18 },
    { time: '11:00', calls: 15 },
    { time: '12:00', calls: 10 },
    { time: '13:00', calls: 22 },
    { time: '14:00', calls: 25 },
    { time: '15:00', calls: 18 },
    { time: '16:00', calls: 12 },
    { time: '17:00', calls: 8 },
];

const outcomeData = [
    { name: 'Scheduled', count: 45, color: '#3b82f6' },
    { name: 'Answered', count: 32, color: '#10b981' },
    { name: 'Transferred', count: 18, color: '#f59e0b' },
    { name: 'Abandoned', count: 12, color: '#ef4444' },
];

export default function Dashboard() {
    const { data: stats, isLoading } = useQuery({
        queryKey: ['dashboard-stats'],
        queryFn: async () => {
            const res = await axios.get('http://localhost:8000/api/dashboard/stats');
            return res.data;
        },
    });

    if (isLoading) return <div className="p-8">Loading dashboard stats...</div>;

    return (
        <div className="space-y-8 animate-in fade-in duration-500">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Practice Overview</h1>
                    <p className="text-muted-foreground mt-1">Real-time performance metrics for Valley Family Medicine.</p>
                </div>

                <Card className="bg-blue-600 text-white shadow-blue-500/20 border-none">
                    <CardContent className="p-4 flex items-center gap-4">
                        <div className="h-10 w-10 bg-white/20 rounded-lg flex items-center justify-center">
                            <Phone className="h-5 w-5 text-white" />
                        </div>
                        <div className="flex-1">
                            <p className="text-sm font-bold opacity-90">Developer Test Mode</p>
                            <p className="text-[10px] opacity-70">Simulate a patient call via WebRTC</p>
                        </div>
                        <Button
                            className="bg-white text-blue-600 hover:bg-white/90 gap-2 h-9 text-xs font-bold"
                            onClick={async () => {
                                try {
                                    // 1. Create the call
                                    const createRes = await axios.post('http://localhost:8000/voice/create', {
                                        provider_id: 'provider-1'
                                    });
                                    const { call_id, room_url } = createRes.data;

                                    // 2. Trigger the agent
                                    await axios.post(`http://localhost:8000/voice/${call_id}/join-agent`);

                                    // 3. Join as user in new tab
                                    window.open(room_url, '_blank');
                                } catch (err) {
                                    console.error("Failed to start test call:", err);
                                    alert("Check console - is backend running?");
                                }
                            }}
                        >
                            <Play className="h-3.5 w-3.5 fill-current" /> Start Simulator
                        </Button>
                    </CardContent>
                </Card>
            </div>

            {/* Stats Grid */}
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                <Card className="hover:shadow-md transition-shadow">
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Total Calls Today</CardTitle>
                        <Phone className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{stats?.total_calls}</div>
                        <p className="text-xs text-muted-foreground mt-1">
                            <span className="text-emerald-500 font-medium inline-flex items-center gap-1">
                                <TrendingUp className="h-3 w-3" /> +12%
                            </span>{" "}
                            from yesterday
                        </p>
                    </CardContent>
                </Card>
                <Card className="hover:shadow-md transition-shadow">
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Resolution Rate</CardTitle>
                        <CheckCircle2 className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">
                            {Math.round((stats?.resolved_calls / stats?.total_calls) * 100)}%
                        </div>
                        <p className="text-xs text-muted-foreground mt-1">
                            Target: 85%
                        </p>
                    </CardContent>
                </Card>
                <Card className="hover:shadow-md transition-shadow">
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Avg duration</CardTitle>
                        <Clock className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{Math.floor(stats?.avg_duration_sec / 60)}m {Math.round(stats?.avg_duration_sec % 60)}s</div>
                        <p className="text-xs text-muted-foreground mt-1">
                            -15s vs last week
                        </p>
                    </CardContent>
                </Card>
                <Card className="hover:shadow-md transition-shadow">
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Sentiment Score</CardTitle>
                        <TrendingUp className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{stats?.sentiment_score * 100}%</div>
                        <p className="text-xs text-muted-foreground mt-1">
                            Positive/Neutral
                        </p>
                    </CardContent>
                </Card>
            </div>

            {/* Charts */}
            <div className="grid gap-4 md:grid-cols-7">
                <Card className="md:col-span-4">
                    <CardHeader>
                        <CardTitle className="text-base font-medium">Call Volume</CardTitle>
                    </CardHeader>
                    <CardContent className="h-[300px]">
                        <ResponsiveContainer width="100%" height="100%">
                            <AreaChart data={chartData}>
                                <defs>
                                    <linearGradient id="colorCalls" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.1} />
                                        <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                                    </linearGradient>
                                </defs>
                                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                                <XAxis dataKey="time" axisLine={false} tickLine={false} tick={{ fontSize: 12 }} dy={10} />
                                <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12 }} />
                                <Tooltip
                                    contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                                />
                                <Area
                                    type="monotone"
                                    dataKey="calls"
                                    stroke="#3b82f6"
                                    strokeWidth={2}
                                    fillOpacity={1}
                                    fill="url(#colorCalls)"
                                />
                            </AreaChart>
                        </ResponsiveContainer>
                    </CardContent>
                </Card>

                <Card className="md:col-span-3">
                    <CardHeader>
                        <CardTitle className="text-base font-medium">Outcome Distribution</CardTitle>
                    </CardHeader>
                    <CardContent className="h-[300px]">
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={outcomeData} layout="vertical">
                                <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#f1f5f9" />
                                <XAxis type="number" hide />
                                <YAxis dataKey="name" type="category" axisLine={false} tickLine={false} width={100} tick={{ fontSize: 12 }} />
                                <Tooltip cursor={{ fill: 'transparent' }} />
                                <Bar dataKey="count" radius={[0, 4, 4, 0]} barSize={32}>
                                    {outcomeData.map((entry, index) => (
                                        <Area key={index} fill={entry.color} dataKey="count" />
                                    ))}
                                </Bar>
                            </BarChart>
                        </ResponsiveContainer>
                    </CardContent>
                </Card>
            </div>

            {/* Active Alerts / Feedback */}
            <div className="grid gap-4 md:grid-cols-2">
                <Card>
                    <CardHeader className="flex flex-row items-center gap-2">
                        <AlertCircle className="h-5 w-5 text-amber-500" />
                        <CardTitle className="text-sm font-medium">Knowledge Gaps Detected</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-4">
                            <div className="flex items-center justify-between text-sm">
                                <span className="text-muted-foreground">"Do you accept Blue Cross PPO?"</span>
                                <span className="font-medium text-amber-600">3 occurrences</span>
                            </div>
                            <div className="flex items-center justify-between text-sm">
                                <span className="text-muted-foreground">"When is Dr. Sarah back from leave?"</span>
                                <span className="font-medium text-amber-600">2 occurrences</span>
                            </div>
                            <p className="text-xs text-muted-foreground mt-4">
                                Review these in the <span className="font-medium text-blue-600 underline">Learning Loop</span>
                            </p>
                        </div>
                    </CardContent>
                </Card>
                <Card>
                    <CardHeader className="flex flex-row items-center gap-2">
                        <PhoneIncoming className="h-5 w-5 text-blue-500" />
                        <CardTitle className="text-sm font-medium">Recent Successes</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-4">
                            <div className="flex items-center gap-3">
                                <div className="h-8 w-8 rounded-full bg-emerald-100 flex items-center justify-center text-emerald-600">
                                    <CheckCircle2 className="h-4 w-4" />
                                </div>
                                <div className="text-sm">
                                    <p className="font-medium">Appointment Scheduled</p>
                                    <p className="text-xs text-muted-foreground">New patient: Sarah Johnson</p>
                                </div>
                            </div>
                            <div className="flex items-center gap-3">
                                <div className="h-8 w-8 rounded-full bg-emerald-100 flex items-center justify-center text-emerald-600">
                                    <CheckCircle2 className="h-4 w-4" />
                                </div>
                                <div className="text-sm">
                                    <p className="font-medium">Insurance Verified</p>
                                    <p className="text-xs text-muted-foreground">Patient: Mark Wilson</p>
                                </div>
                            </div>
                        </div>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
