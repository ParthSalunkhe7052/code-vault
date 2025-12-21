import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Check, X, Sparkles, Zap, Crown, ArrowRight, Loader2, AlertCircle } from 'lucide-react';
import { subscription, auth } from '../services/api';
import { pricingService } from '../services/pricingService';

const PricingTier = ({
    name,
    price,
    period,
    description,
    features,
    limitations,
    icon: Icon,
    iconColor,
    popular,
    current,
    onSubscribe,
    loading,
    buttonText
}) => (
    <div className={`relative glass-card p-6 flex flex-col ${popular ? 'ring-2 ring-violet-500 scale-105' : ''}`}>
        {popular && (
            <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                <span className="px-3 py-1 text-xs font-semibold bg-gradient-to-r from-violet-500 to-indigo-500 text-white rounded-full">
                    Most Popular
                </span>
            </div>
        )}

        {current && (
            <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                <span className="px-3 py-1 text-xs font-semibold bg-emerald-500 text-white rounded-full">
                    Current Plan
                </span>
            </div>
        )}

        <div className="flex items-center gap-3 mb-4">
            <div className={`p-2 rounded-lg bg-gradient-to-br ${iconColor}`}>
                <Icon size={24} className="text-white" />
            </div>
            <div>
                <h3 className="text-xl font-bold text-white">{name}</h3>
                <p className="text-sm text-slate-400">{description}</p>
            </div>
        </div>

        <div className="mb-6">
            <span className="text-4xl font-bold text-white">${price}</span>
            <span className="text-slate-400">/{period}</span>
        </div>

        <div className="flex-1 space-y-3 mb-6">
            {features.map((feature, i) => {
                const isComingSoon = feature.toLowerCase().includes('cloud compilation');
                return (
                    <div key={i} className="flex items-start gap-2">
                        <Check size={18} className="text-emerald-400 mt-0.5 flex-shrink-0" />
                        <span className="text-sm text-slate-300">
                            {feature}
                            {isComingSoon && (
                                <span className="ml-2 px-1.5 py-0.5 text-xs bg-purple-500/20 text-purple-300 rounded">
                                    Coming Soon
                                </span>
                            )}
                        </span>
                    </div>
                );
            })}

            {limitations?.map((limitation, i) => (
                <div key={i} className="flex items-start gap-2">
                    <X size={18} className="text-slate-500 mt-0.5 flex-shrink-0" />
                    <span className="text-sm text-slate-500">{limitation}</span>
                </div>
            ))}
        </div>

        <button
            onClick={onSubscribe}
            disabled={loading || current}
            className={`w-full py-3 px-4 rounded-lg font-semibold transition-all flex items-center justify-center gap-2 ${current
                ? 'bg-slate-600 text-slate-400 cursor-not-allowed'
                : popular
                    ? 'bg-gradient-to-r from-violet-500 to-indigo-500 text-white hover:from-violet-600 hover:to-indigo-600'
                    : 'bg-white/10 text-white hover:bg-white/20'
                }`}
        >
            {loading ? (
                <Loader2 size={18} className="animate-spin" />
            ) : (
                <>
                    {buttonText}
                    {!current && <ArrowRight size={18} />}
                </>
            )}
        </button>
    </div>
);

const Pricing = () => {
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();
    const [currentPlan, setCurrentPlan] = useState('free');
    const [loading, setLoading] = useState('');
    const [successMessage, setSuccessMessage] = useState('');
    const [errorMessage, setErrorMessage] = useState('');
    const [pricingConfig, setPricingConfig] = useState(null);

    const isAuthenticated = auth.isAuthenticated();

    useEffect(() => {
        const loadData = async () => {
            try {
                // Load pricing config
                const config = await pricingService.getConfig();
                setPricingConfig(config);

                // Fetch current subscription status if logged in
                if (isAuthenticated) {
                    const status = await subscription.getStatus();
                    setCurrentPlan(status.plan_tier || 'free');
                }
            } catch (error) {
                console.error('Failed to load data:', error);
            }
        };

        // Check for success/canceled query params
        if (searchParams.get('success') === 'true') {
            setSuccessMessage('🎉 Payment successful! Welcome to your new plan.');
        } else if (searchParams.get('canceled') === 'true') {
            setErrorMessage('Payment was canceled. You can try again when ready.');
        }

        loadData();
    }, [searchParams, isAuthenticated]);


    const handleSubscribe = async (tier) => {
        if (!isAuthenticated) {
            navigate('/login?redirect=/pricing');
            return;
        }

        if (tier === 'free') return;

        setLoading(tier);
        setErrorMessage('');

        try {
            const priceId = pricingConfig?.[tier]?.price_id;
            if (!priceId) {
                throw new Error('Price not configured');
            }

            const { checkout_url } = await subscription.createCheckoutSession(
                priceId,
                `${window.location.origin}/billing?success=true`,
                `${window.location.origin}/pricing?canceled=true`
            );

            // Redirect to Stripe Checkout
            window.location.href = checkout_url;
        } catch (error) {
            console.error('Checkout error:', error);
            const msg = error.response?.data?.detail || 'Connection failed.';
            setErrorMessage(`${msg} Please check your connection and try again.`);
            setLoading('');
        }
    };

    const tiers = [
        {
            name: pricingConfig?.free?.name || 'Free',
            price: pricingConfig?.free?.price ?? 0,
            period: 'forever',
            description: 'Get started with basics',
            icon: Sparkles,
            iconColor: 'from-slate-500 to-slate-600',
            features: pricingConfig?.free?.features || [
                '1 project',
                '5 licenses per project',
                'Local compilation only',
                'Python support',
            ],
            limitations: [
                'Cannot sell licenses',
                'No cloud compilation',
                'No analytics',
            ],
            tier: 'free',
        },
        {
            name: pricingConfig?.pro?.name || 'Pro',
            price: pricingConfig?.pro?.price ?? 20,
            period: 'month',
            description: 'For indie developers',
            icon: Zap,
            iconColor: 'from-violet-500 to-indigo-500',
            popular: true,
            features: pricingConfig?.pro?.features || [
                '10 projects',
                '100 licenses per project',
                'Cloud compilation',
                'Python + Node.js support',
                'Sell licenses to customers',
                'Analytics dashboard',
            ],
            tier: 'pro',
        },
        {
            name: pricingConfig?.enterprise?.name || 'Enterprise',
            price: pricingConfig?.enterprise?.price ?? 50,
            period: 'month',
            description: 'For teams & agencies',
            icon: Crown,
            iconColor: 'from-amber-500 to-orange-500',
            features: pricingConfig?.enterprise?.features || [
                'Unlimited projects',
                'Unlimited licenses',
                'Cloud compilation',
                'Python + Node.js support',
                'Sell licenses to customers',
                'Team collaboration (5 seats)',
                'Priority support',
            ],
            tier: 'enterprise',
        },
    ];

    return (
        <div className="min-h-screen py-12">
            <div className="max-w-6xl mx-auto px-6">
                {/* Header */}
                <div className="text-center mb-12">
                    <h1 className="text-4xl font-bold text-white mb-4">
                        Simple, Transparent Pricing
                    </h1>
                    <p className="text-lg text-slate-400 max-w-2xl mx-auto">
                        Choose the plan that fits your needs. Upgrade or downgrade anytime.
                        All plans include our core license protection features.
                    </p>
                </div>

                {/* Messages */}
                {successMessage && (
                    <div className="mb-8 p-4 bg-emerald-500/10 border border-emerald-500/20 rounded-lg text-center">
                        <p className="text-emerald-400">{successMessage}</p>
                    </div>
                )}

                {errorMessage && (
                    <div className="mb-8 p-4 bg-red-500/10 border border-red-500/20 rounded-lg flex items-center justify-center gap-2 animate-in fade-in slide-in-from-top-4 duration-300">
                        <AlertCircle className="text-red-400" size={20} />
                        <p className="text-red-400 font-medium">{errorMessage}</p>
                    </div>
                )}

                {/* Pricing Grid */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-12">
                    {tiers.map((tier) => (
                        <PricingTier
                            key={tier.name}
                            {...tier}
                            current={currentPlan === tier.tier}
                            loading={loading === tier.tier}
                            onSubscribe={() => handleSubscribe(tier.tier)}
                            buttonText={
                                currentPlan === tier.tier
                                    ? 'Current Plan'
                                    : tier.tier === 'free'
                                        ? 'Free Forever'
                                        : 'Subscribe'
                            }
                        />
                    ))}
                </div>

                {/* FAQ */}
                <div className="glass-card p-8">
                    <h2 className="text-2xl font-bold text-white mb-6 text-center">
                        Frequently Asked Questions
                    </h2>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div>
                            <h3 className="text-lg font-semibold text-white mb-2">
                                Can I upgrade or downgrade anytime?
                            </h3>
                            <p className="text-slate-400 text-sm">
                                Yes! You can change your plan at any time. When upgrading, you'll be
                                charged the prorated amount. When downgrading, the change takes effect
                                at the end of your billing period.
                            </p>
                        </div>

                        <div>
                            <h3 className="text-lg font-semibold text-white mb-2">
                                What payment methods do you accept?
                            </h3>
                            <p className="text-slate-400 text-sm">
                                We accept all major credit cards (Visa, Mastercard, American Express),
                                as well as Apple Pay and Google Pay for convenient mobile payments.
                            </p>
                        </div>

                        <div>
                            <h3 className="text-lg font-semibold text-white mb-2">
                                What happens to my projects if I downgrade?
                            </h3>
                            <p className="text-slate-400 text-sm">
                                Your projects and licenses remain intact. However, you won't be able
                                to create new projects beyond your plan's limit until you upgrade again.
                            </p>
                        </div>

                        <div>
                            <h3 className="text-lg font-semibold text-white mb-2">
                                Is there a money-back guarantee?
                            </h3>
                            <p className="text-slate-400 text-sm">
                                Yes! If you're not satisfied within the first 7 days, contact us and
                                we'll provide a full refund, no questions asked.
                            </p>
                        </div>
                    </div>
                </div>

                {/* CTA */}
                {!isAuthenticated && (
                    <div className="text-center mt-12">
                        <p className="text-slate-400 mb-4">
                            Ready to get started? Create a free account first.
                        </p>
                        <button
                            onClick={() => navigate('/login')}
                            className="btn-primary px-8 py-3"
                        >
                            Create Free Account
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
};

export default Pricing;
