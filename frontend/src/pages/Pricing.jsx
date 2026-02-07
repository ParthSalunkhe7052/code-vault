import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Check, X, Sparkles, Zap, Crown, ArrowRight, Loader2 } from 'lucide-react';
import { usePricing, TIERS } from '../contexts/PricingContext';
import { auth } from '../services/api';

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
    buttonText,
    isContact
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
            <span className="text-4xl font-bold text-white">
                {typeof price === 'number' ? `$${price}` : price}
            </span>
            {period && <span className="text-slate-400">/{period}</span>}
        </div>

        <div className="flex-1 space-y-3 mb-6">
            {features.map((feature, i) => (
                <div key={i} className="flex items-start gap-2">
                    <Check size={18} className="text-emerald-400 mt-0.5 flex-shrink-0" />
                    <span className="text-sm text-slate-300">{feature}</span>
                </div>
            ))}

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
                    {!current && !isContact && <ArrowRight size={18} />}
                </>
            )}
        </button>
    </div>
);

const Pricing = () => {
    const navigate = useNavigate();
    const { tier: currentPlan, createCheckout } = usePricing();
    const [loading, setLoading] = useState('');
    const [errorMessage, setErrorMessage] = useState('');

    const isAuthenticated = auth.isAuthenticated();

    const handleSubscribe = async (targetTier) => {
        if (!isAuthenticated) {
            navigate('/login?redirect=/pricing');
            return;
        }

        if (targetTier === TIERS.FREE) {
            // Can't "subscribe" to free — they'd need to cancel via Polar portal
            return;
        }

        if (targetTier === TIERS.ENTERPRISE) {
            window.location.href = 'mailto:sales@codevault.com?subject=CodeVault Enterprise';
            return;
        }

        setLoading(targetTier);
        setErrorMessage('');

        try {
            await createCheckout(targetTier);
            // User will be redirected to Polar checkout
        } catch (err) {
            console.error('Checkout error:', err);
            setErrorMessage('Failed to start checkout. Please try again.');
        } finally {
            setLoading('');
        }
    };

    const tiers = [
        {
            name: 'Free',
            price: 0,
            period: 'forever',
            description: 'For testing and small tools',
            icon: Sparkles,
            iconColor: 'from-slate-500 to-slate-600',
            features: [
                '1 Project',
                '50 Active Licenses',
                'Local Builds Only',
                'Community Support',
            ],
            limitations: [
                'No Cloud Builds',
                'No Node.js Support',
                'No Analytics or Webhooks',
            ],
            tier: TIERS.FREE,
        },
        {
            name: 'Pro',
            price: 15,
            period: 'month',
            description: 'For indie developers shipping apps',
            icon: Zap,
            iconColor: 'from-violet-500 to-indigo-500',
            popular: true,
            features: [
                'Unlimited Projects',
                '500 Active Licenses',
                '25 Cloud Builds / month',
                'Offline Leases',
                'Node.js Support',
                'Analytics & Webhooks',
                'No Branding / Splash Screen',
            ],
            tier: TIERS.PRO,
        },
        {
            name: 'Business',
            price: 39,
            period: 'month',
            description: 'For teams and studios at scale',
            icon: Crown,
            iconColor: 'from-amber-500 to-orange-500',
            features: [
                'Unlimited Projects',
                '5,000 Active Licenses',
                '100 Cloud Builds / month',
                '10 Team Seats',
                'White Label Branding',
                'Priority Support',
            ],
            tier: TIERS.BUSINESS,
        },
        {
            name: 'Enterprise',
            price: 'Custom',
            period: '',
            description: 'For regulated and high-volume deployments',
            icon: Crown,
            iconColor: 'from-slate-500 to-slate-700',
            features: [
                'Unlimited Projects & Licenses',
                'Unlimited Cloud Builds',
                'Unlimited Team Seats',
                'Dedicated Build Runners',
                'Custom SLAs & Security Reviews',
                'Priority Support',
            ],
            tier: TIERS.ENTERPRISE,
        },
    ];

    return (
        <div className="min-h-screen py-12">
            <div className="max-w-6xl mx-auto px-6">
                <div className="text-center mb-12">
                    <h1 className="text-4xl font-bold text-white mb-4">
                        Simple, Transparent Pricing
                    </h1>
                    <p className="text-lg text-slate-400 max-w-2xl mx-auto">
                        Build once, distribute unlimited times with different license keys. Start free, scale when you ship.
                    </p>
                </div>

                {errorMessage && (
                    <div className="mb-8 p-4 bg-red-500/10 border border-red-500/20 rounded-lg text-center">
                        <p className="text-red-400">{errorMessage}</p>
                    </div>
                )}

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
                                    : tier.tier === TIERS.FREE
                                        ? 'Free Forever'
                                        : tier.tier === TIERS.ENTERPRISE
                                            ? 'Contact Sales'
                                        : 'Upgrade'
                            }
                            isContact={tier.tier === TIERS.ENTERPRISE}
                        />
                    ))}
                </div>

                <div className="glass-card p-8">
                    <h2 className="text-2xl font-bold text-white mb-6 text-center">
                        Frequently Asked Questions
                    </h2>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div>
                            <h3 className="text-lg font-semibold text-white mb-2">How does the Free tier work?</h3>
                            <p className="text-slate-400 text-sm">You get 1 project and 50 licenses forever. Perfect for testing CodeVault before committing.</p>
                        </div>
                        <div>
                            <h3 className="text-lg font-semibold text-white mb-2">What are Cloud Builds?</h3>
                            <p className="text-slate-400 text-sm">Cloud builds compile your project on our servers so you don't need local compilers. Pro gets 25/month, Business gets 100/month.</p>
                        </div>
                        <div>
                            <h3 className="text-lg font-semibold text-white mb-2">Can I cancel anytime?</h3>
                            <p className="text-slate-400 text-sm">Yes. You can cancel from your Polar billing portal at any time. You'll keep access until the end of your billing period.</p>
                        </div>
                        <div>
                            <h3 className="text-lg font-semibold text-white mb-2">What does "build once, distribute unlimited" mean?</h3>
                            <p className="text-slate-400 text-sm">One cloud build produces a protected executable. You can then issue as many unique license keys as your plan allows to distribute it to different users.</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default Pricing;
