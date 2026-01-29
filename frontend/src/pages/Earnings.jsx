import { useState, useEffect } from 'react';
import { DollarSign, TrendingUp, Clock, AlertCircle } from 'lucide-react';
import { api } from '../services/api';
import { useToast } from '../components/Toast';
import Spinner from '../components/Spinner';

export default function Earnings() {
    const [stats, setStats] = useState(null);
    const [loading, setLoading] = useState(true);
    const [processing, setProcessing] = useState(false);
    const { showToast } = useToast();

    useEffect(() => {
        fetchStats();
    }, []);

    const fetchStats = async () => {
        try {
            const data = await api.get('/payouts/stats');
            setStats(data);
        } catch (error) {
            console.error('Failed to fetch earnings:', error);
            showToast('Failed to load earnings data', 'error');
        } finally {
            setLoading(false);
        }
    };

    const handlePayoutRequest = async () => {
        if (!confirm('Are you sure you want to request a payout for your entire balance?')) return;
        
        setProcessing(true);
        try {
            await api.post('/payouts/request');
            showToast('Payout requested successfully', 'success');
            fetchStats(); // Refresh data
        } catch (error) {
            console.error('Payout failed:', error);
            showToast(error.response?.data?.detail || 'Failed to request payout', 'error');
        } finally {
            setProcessing(false);
        }
    };

    if (loading) return <div className="p-8 flex justify-center"><Spinner /></div>;

    // Convert cents to dollars
    const balance = (stats?.balance_cents || 0) / 100;
    const total = (stats?.total_earnings_cents || 0) / 100;
    const pending = (stats?.pending_payouts_cents || 0) / 100;

    return (
        <div className="space-y-6">
            <h1 className="text-2xl font-bold text-white">Earnings & Payouts</h1>

            {/* Stats Grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="bg-slate-800 p-6 rounded-xl border border-slate-700">
                    <div className="flex items-center justify-between mb-4">
                        <div className="text-slate-400">Available Balance</div>
                        <div className="bg-emerald-500/10 p-2 rounded-lg">
                            <DollarSign className="w-6 h-6 text-emerald-500" />
                        </div>
                    </div>
                    <div className="text-3xl font-bold text-white"></div>
                    <button 
                        onClick={handlePayoutRequest}
                        disabled={balance < 50 || processing}
                        className={mt-4 w-full py-2 px-4 rounded-lg font-medium transition-colors }
                    >
                        {processing ? 'Processing...' : 'Request Payout'}
                    </button>
                    <div className="mt-2 text-xs text-slate-500 text-center">
                        Minimum payout: .00
                    </div>
                </div>

                <div className="bg-slate-800 p-6 rounded-xl border border-slate-700">
                    <div className="flex items-center justify-between mb-4">
                        <div className="text-slate-400">Total Earnings</div>
                        <div className="bg-blue-500/10 p-2 rounded-lg">
                            <TrendingUp className="w-6 h-6 text-blue-500" />
                        </div>
                    </div>
                    <div className="text-3xl font-bold text-white"></div>
                    <div className="mt-4 text-sm text-slate-400">
                        Lifetime earnings from marketplace sales.
                    </div>
                </div>

                <div className="bg-slate-800 p-6 rounded-xl border border-slate-700">
                    <div className="flex items-center justify-between mb-4">
                        <div className="text-slate-400">Pending Payouts</div>
                        <div className="bg-amber-500/10 p-2 rounded-lg">
                            <Clock className="w-6 h-6 text-amber-500" />
                        </div>
                    </div>
                    <div className="text-3xl font-bold text-white"></div>
                    <div className="mt-4 text-sm text-slate-400">
                        Processing time: 3-5 business days.
                    </div>
                </div>
            </div>

            {/* Info Box */}
            <div className="bg-slate-900/50 border border-slate-800 rounded-lg p-4 flex items-start gap-3">
                <AlertCircle className="w-5 h-5 text-cyan-500 mt-0.5" />
                <div className="text-sm text-slate-400">
                    <p className="font-medium text-slate-200 mb-1">How payouts work</p>
                    <p>
                        Payouts are processed via Dodo Payments directly to your linked bank account or UPI.
                        Platform fees (10%) and payment processing fees are deducted automatically at the time of sale.
                        The amount shown in "Available Balance" is your net take-home earnings.
                    </p>
                </div>
            </div>
        </div>
    );
}
