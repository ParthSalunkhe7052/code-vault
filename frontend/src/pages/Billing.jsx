import React, { useState, useEffect } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import {
    CreditCard,
    Calendar,
    TrendingUp,
    ExternalLink,
    AlertTriangle,
    CheckCircle,
    XCircle,
    Loader2,
    RefreshCw,
    Zap,
    Crown,
    Sparkles
} from 'lucide-react';
import { subscription, auth } from '../services/api';

const PlanBadge = ({ tier }) => {
    const config = {
        free: { icon: Sparkles, color: 'from-slate-500 to-slate-600', label: 'Free' },
        pro: { icon: Zap, color: 'from-violet-500 to-indigo-500', label: 'Pro' },
        enterprise: { icon: Crown, color: 'from-amber-500 to-orange-500', label: 'Enterprise' },
    };

    const { icon: Icon, color, label } = config[tier] || config.free;

    return (
        <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-gradient-to-r ${color}`}>
            <Icon size={16} className="text-white" />
            <span className="text-sm font-semibold text-white">{label}</span>
        </div>
    );
};

const StatusBadge = ({ status }) => {
    const config = {
        active: { icon: CheckCircle, color: 'text-emerald-400 bg-emerald-400/10', label: 'Active' },
        past_due: { icon: AlertTriangle, color: 'text-amber-400 bg-amber-400/10', label: 'Past Due' },
        canceled: { icon: XCircle, color: 'text-red-400 bg-red-400/10', label: 'Canceled' },
        trialing: { icon: Zap, color: 'text-blue-400 bg-blue-400/10', label: 'Trial' },
    };

    const { icon: Icon, color, label } = config[status] || config.active;

    return (
        <div className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full ${color}`}>
            <Icon size={14} />
            <span className="text-xs font-medium">{label}</span>
        </div>
    );
};

const UsageBar = ({ used, max, label }) => {
    const percentage = max === -1 ? 0 : Math.min((used / max) * 100, 100);
    const isUnlimited = max === -1;

    return (
        <div className="space-y-2">
            <div className="flex justify-between text-sm">
                <span className="text-slate-400">{label}</span>
                <span className="text-white font-medium">
                    {used} / {isUnlimited ? '∞' : max}
                </span>
            </div>
            <div className="h-2 bg-white/5 rounded-full overflow-hidden">
                <div
                    className={`h-full rounded-full transition-all ${percentage > 90 ? 'bg-red-500' : percentage > 70 ? 'bg-amber-500' : 'bg-violet-500'
                        }`}
                    style={{ width: isUnlimited ? '10%' : `${percentage}%` }}
                />
            </div>
        </div>
    );
};

const Billing = () => {
    const [searchParams] = useSearchParams();
    const [subscriptionData, setSubscriptionData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [portalLoading, setPortalLoading] = useState(false);
    const [successMessage, setSuccessMessage] = useState('');
    const [errorMessage, setErrorMessage] = useState('');

    useEffect(() => {
        // Check for success query param
        if (searchParams.get('success') === 'true') {
            setSuccessMessage('🎉 Your subscription has been updated successfully!');
            // Refresh user profile to update sidebar/navbar immediately
            auth.refreshUser().then(() => {
                // Force reload after a short delay to reflect changes in Layout (sidebar badge)
                setTimeout(() => {
                    window.location.href = window.location.pathname;
                }, 1500);
            }).catch(err => console.error("Failed to refresh user profile", err));
        }

        fetchSubscriptionData();
    }, [searchParams]);

    const fetchSubscriptionData = async () => {
        setLoading(true);
        try {
            const data = await subscription.getStatus();
            setSubscriptionData(data);
        } catch (error) {
            console.error('Failed to fetch subscription:', error);
            setErrorMessage('Failed to load subscription data. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    const handleManageSubscription = async () => {
        setPortalLoading(true);
        setErrorMessage('');

        try {
            const { portal_url } = await subscription.createCustomerPortal(
                `${window.location.origin}/billing`
            );
            window.location.href = portal_url;
        } catch (error) {
            console.error('Portal error:', error);
            if (error.response?.status === 400) {
                setErrorMessage('No active subscription found. Subscribe to a paid plan first.');
            } else {
                setErrorMessage('Failed to open billing portal. Please try again.');
            }
            setPortalLoading(false);
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-[400px]">
                <Loader2 size={32} className="animate-spin text-violet-400" />
            </div>
        );
    }

    const { plan_tier, status, current_period_end, cancel_at_period_end, limits, usage } = subscriptionData || {};
    const isFree = plan_tier === 'free';

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-end justify-between border-b border-white/10 pb-6">
                <div>
                    <h1 className="text-2xl font-bold text-white mb-1">Billing</h1>
                    <p className="text-slate-400 text-sm">Manage your subscription and billing</p>
                </div>
                <button
                    onClick={fetchSubscriptionData}
                    className="btn-secondary flex items-center gap-2"
                >
                    <RefreshCw size={16} />
                    Refresh
                </button>
            </div>

            {/* Messages */}
            {successMessage && (
                <div className="p-4 bg-emerald-500/10 border border-emerald-500/20 rounded-lg">
                    <p className="text-emerald-400">{successMessage}</p>
                </div>
            )}

            {errorMessage && (
                <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-lg">
                    <p className="text-red-400">{errorMessage}</p>
                </div>
            )}

            {/* Subscription Status Card */}
            <div className="glass-card p-6">
                <div className="flex items-start justify-between mb-6">
                    <div>
                        <h2 className="text-lg font-semibold text-white mb-2">Current Plan</h2>
                        <div className="flex items-center gap-3">
                            <PlanBadge tier={plan_tier} />
                            <StatusBadge status={status} />
                        </div>
                    </div>

                    <div className="flex gap-3">
                        {!isFree && (
                            <button
                                onClick={handleManageSubscription}
                                disabled={portalLoading}
                                className="btn-secondary flex items-center gap-2"
                            >
                                {portalLoading ? (
                                    <Loader2 size={16} className="animate-spin" />
                                ) : (
                                    <ExternalLink size={16} />
                                )}
                                Manage Subscription
                            </button>
                        )}
                        <Link to="/pricing" className="btn-primary flex items-center gap-2">
                            <TrendingUp size={16} />
                            {isFree ? 'Upgrade' : 'Change Plan'}
                        </Link>
                    </div>
                </div>

                {/* Billing Details */}
                {!isFree && current_period_end && (
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 p-4 bg-white/5 rounded-lg mb-6">
                        <div className="flex items-center gap-3">
                            <Calendar size={20} className="text-slate-400" />
                            <div>
                                <p className="text-xs text-slate-400">Next billing date</p>
                                <p className="text-white font-medium">
                                    {new Date(current_period_end).toLocaleDateString('en-US', {
                                        year: 'numeric',
                                        month: 'long',
                                        day: 'numeric'
                                    })}
                                </p>
                            </div>
                        </div>

                        <div className="flex items-center gap-3">
                            <CreditCard size={20} className="text-slate-400" />
                            <div>
                                <p className="text-xs text-slate-400">Payment method</p>
                                <p className="text-white font-medium">
                                    Managed via Stripe
                                </p>
                            </div>
                        </div>

                        <div className="flex items-center gap-3">
                            <TrendingUp size={20} className="text-slate-400" />
                            <div>
                                <p className="text-xs text-slate-400">Amount</p>
                                <p className="text-white font-medium">
                                    ${plan_tier === 'pro' ? '20' : '50'}/month
                                </p>
                            </div>
                        </div>
                    </div>
                )}

                {/* Cancellation Warning */}
                {cancel_at_period_end && (
                    <div className="p-4 bg-amber-500/10 border border-amber-500/20 rounded-lg mb-6">
                        <div className="flex items-center gap-2 text-amber-400">
                            <AlertTriangle size={18} />
                            <p className="font-medium">Your subscription will cancel at the end of the billing period</p>
                        </div>
                        <p className="text-sm text-slate-400 mt-1">
                            You'll retain access until {new Date(current_period_end).toLocaleDateString()}.
                            To keep your subscription, click "Manage Subscription" and reactivate.
                        </p>
                    </div>
                )}

                {/* Free Plan Upsell */}
                {isFree && (
                    <div className="p-6 bg-gradient-to-br from-violet-500/10 to-indigo-500/10 border border-violet-500/20 rounded-lg">
                        <h3 className="text-lg font-semibold text-white mb-2">
                            Unlock More with Pro
                        </h3>
                        <p className="text-slate-400 text-sm mb-4">
                            Get 10x more projects, 20x more licenses, cloud compilation,
                            and the ability to sell licenses to your customers.
                        </p>
                        <Link to="/pricing" className="btn-primary inline-flex items-center gap-2">
                            <Zap size={16} />
                            Upgrade to Pro - $20/month
                        </Link>
                    </div>
                )}
            </div>

            {/* Usage Section */}
            <div className="glass-card p-6">
                <h2 className="text-lg font-semibold text-white mb-4">Usage</h2>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <UsageBar
                        used={usage?.projects || 0}
                        max={limits?.max_projects || 1}
                        label="Projects"
                    />
                </div>

                <div className="mt-6 p-4 bg-white/5 rounded-lg">
                    <h3 className="text-sm font-semibold text-white mb-3">Plan Features</h3>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                        <div className="flex items-center gap-2">
                            {limits?.can_sell_licenses ? (
                                <CheckCircle size={16} className="text-emerald-400" />
                            ) : (
                                <XCircle size={16} className="text-slate-500" />
                            )}
                            <span className={limits?.can_sell_licenses ? 'text-slate-300' : 'text-slate-500'}>
                                Sell Licenses
                            </span>
                        </div>
                        <div className="flex items-center gap-2">
                            {limits?.cloud_compilation ? (
                                <CheckCircle size={16} className="text-emerald-400" />
                            ) : (
                                <XCircle size={16} className="text-slate-500" />
                            )}
                            <span className={limits?.cloud_compilation ? 'text-slate-300' : 'text-slate-500'}>
                                Cloud Compilation
                            </span>
                        </div>
                        <div className="flex items-center gap-2">
                            {limits?.analytics ? (
                                <CheckCircle size={16} className="text-emerald-400" />
                            ) : (
                                <XCircle size={16} className="text-slate-500" />
                            )}
                            <span className={limits?.analytics ? 'text-slate-300' : 'text-slate-500'}>
                                Analytics
                            </span>
                        </div>
                        <div className="flex items-center gap-2">
                            {limits?.team_seats > 1 ? (
                                <CheckCircle size={16} className="text-emerald-400" />
                            ) : (
                                <XCircle size={16} className="text-slate-500" />
                            )}
                            <span className={limits?.team_seats > 1 ? 'text-slate-300' : 'text-slate-500'}>
                                Team Seats
                            </span>
                        </div>
                    </div>
                </div>
            </div>

            {/* Help Section */}
            <div className="glass-card p-6">
                <h2 className="text-lg font-semibold text-white mb-4">Need Help?</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                    <div className="p-4 bg-white/5 rounded-lg">
                        <h3 className="font-semibold text-white mb-1">Change Payment Method</h3>
                        <p className="text-slate-400">
                            Click "Manage Subscription" to update your payment method,
                            view invoices, or download receipts.
                        </p>
                    </div>
                    <div className="p-4 bg-white/5 rounded-lg">
                        <h3 className="font-semibold text-white mb-1">Cancel Subscription</h3>
                        <p className="text-slate-400">
                            You can cancel anytime through the billing portal.
                            You'll keep access until the end of your billing period.
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default Billing;
