import React, { memo, useState, useEffect, useCallback } from 'react';
import { DollarSign, Store, Info, CheckCircle, AlertCircle, ExternalLink, Globe, Tag } from 'lucide-react';
import { sellers as sellerApi } from '../../../services/api';
import Spinner from '../../Spinner';
import SellerOnboarding from '../../SellerOnboarding';

const Step5Monetization = memo(({
    project,
    configData,
    setConfigData,
    onConfigSave
}) => {
    const [sellerProfile, setSellerProfile] = useState(null);
    const [loading, setLoading] = useState(true);
    const [isSaving, setIsSaving] = useState(false);
    const [showOnboarding, setShowOnboarding] = useState(false);

    const fetchSellerProfile = useCallback(async () => {
        setLoading(true);
        try {
            const profile = await sellerApi.getProfile();
            setSellerProfile(profile);
        } catch (err) {
            console.error('Failed to fetch seller profile:', err);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchSellerProfile();
    }, [fetchSellerProfile]);

    // Initialize monetization fields from project data when loaded
    useEffect(() => {
        if (project && !configData.price_cents && project.price_cents) {
            setConfigData(prev => ({
                ...prev,
                is_public_store: project.is_public_store || false,
                price_cents: project.price_cents || 0,
                short_description: project.short_description || '',
                long_description: project.long_description || '',
                category: project.category || 'automation',
                dodo_product_id: project.dodo_product_id || null
            }));
        }
    }, [project, configData.price_cents, setConfigData]);

    const handleTogglePublic = (enabled) => {
        setConfigData(prev => ({ ...prev, is_public_store: enabled }));
    };

    const handleInputChange = (field, value) => {
        setConfigData(prev => ({ ...prev, [field]: value }));
    };

    const handleSave = async () => {
        setIsSaving(true);
        try {
            await sellerApi.updateMonetization(project.id, {
                is_public_store: configData.is_public_store,
                price_cents: parseInt(configData.price_cents || 0),
                short_description: configData.short_description || '',
                long_description: configData.long_description || '',
                category: configData.category || 'automation'
            });
            // Also call the standard config save to keep everything in sync
            await onConfigSave(true);
        } catch (err) {
            console.error('Failed to update monetization:', err);
            if (window.showToast) window.showToast('Failed to save monetization settings', 'error');
        } finally {
            setIsSaving(false);
        }
    };

    if (loading) {
        return (
            <div className="flex flex-col items-center justify-center py-20">
                <Spinner size="lg" />
                <p className="mt-4 text-slate-400">Verifying merchant status...</p>
            </div>
        );
    }

    if (!sellerProfile || !sellerProfile.is_seller) {
        return (
            <div className="max-w-2xl mx-auto text-center space-y-6 py-10 animate-in fade-in duration-500">
                <div className="w-20 h-20 bg-indigo-500/10 text-indigo-400 rounded-3xl flex items-center justify-center mx-auto mb-6">
                    <Store size={40} />
                </div>
                <h2 className="text-3xl font-bold text-white">Start Selling Your Software</h2>
                <p className="text-slate-400 text-lg">
                    Turn your project into a recurring revenue stream. Enable the marketplace to allow others to purchase licenses directly through CodeVault.
                </p>
                
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-left py-6">
                    <div className="p-4 bg-white/5 rounded-xl border border-white/10">
                        <DollarSign className="text-emerald-400 mb-2" size={20} />
                        <h4 className="font-bold text-white text-sm">Automatic Payouts</h4>
                        <p className="text-xs text-slate-500">Receive earnings directly to your bank or UPI.</p>
                    </div>
                    <div className="p-4 bg-white/5 rounded-xl border border-white/10">
                        <Globe className="text-blue-400 mb-2" size={20} />
                        <h4 className="font-bold text-white text-sm">Global Storefront</h4>
                        <p className="text-xs text-slate-500">Your project gets its own SEO-optimized landing page.</p>
                    </div>
                    <div className="p-4 bg-white/5 rounded-xl border border-white/10">
                        <CheckCircle className="text-indigo-400 mb-2" size={20} />
                        <h4 className="font-bold text-white text-sm">License Fulfillment</h4>
                        <p className="text-xs text-slate-500">We handle payment and key delivery automatically.</p>
                    </div>
                </div>

                <button 
                    onClick={() => setShowOnboarding(true)}
                    className="px-8 py-4 bg-indigo-600 hover:bg-indigo-500 text-white rounded-2xl font-bold text-lg shadow-xl shadow-indigo-500/20 transition-all hover:-translate-y-1"
                >
                    Setup Seller Profile
                </button>

                <SellerOnboarding 
                    isOpen={showOnboarding} 
                    onClose={() => setShowOnboarding(false)} 
                    onSuccess={() => {
                        setShowOnboarding(false);
                        fetchSellerProfile();
                    }}
                />
            </div>
        );
    }

    return (
        <div className="space-y-8 animate-in fade-in duration-500 max-w-5xl mx-auto">
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-2xl font-bold text-white mb-1 tracking-tight">Marketplace Settings</h2>
                    <p className="text-slate-400">Configure how your project appears on the public store.</p>
                </div>
                <div className="flex items-center gap-3">
                    <span className={`px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider ${sellerProfile.is_verified ? 'bg-emerald-500/20 text-emerald-400' : 'bg-amber-500/20 text-amber-400'}`}>
                        {sellerProfile.is_verified ? 'Verified Seller' : 'Pending Verification'}
                    </span>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Left Column: Form */}
                <div className="lg:col-span-2 space-y-6">
                    <div className="glass-card p-6 space-y-6">
                        {/* Toggle */}
                        <div className="flex items-center justify-between p-4 bg-white/5 rounded-2xl border border-white/10">
                            <div className="flex items-center gap-4">
                                <div className={`p-3 rounded-xl ${configData.is_public_store ? 'bg-emerald-500/20 text-emerald-400' : 'bg-slate-800 text-slate-500'}`}>
                                    <Globe size={24} />
                                </div>
                                <div>
                                    <h3 className="font-bold text-white">Public Storefront</h3>
                                    <p className="text-sm text-slate-500">Enable this to list your project on the marketplace.</p>
                                </div>
                            </div>
                            <button
                                onClick={() => handleTogglePublic(!configData.is_public_store)}
                                className={`relative inline-flex h-7 w-12 items-center rounded-full transition-colors focus:outline-none ${configData.is_public_store ? 'bg-emerald-500' : 'bg-slate-700'}`}
                            >
                                <span className={`inline-block h-5 w-5 transform rounded-full bg-white transition-transform ${configData.is_public_store ? 'translate-x-6' : 'translate-x-1'}`} />
                            </button>
                        </div>

                        {configData.is_public_store && (
                            <div className="space-y-6 animate-in slide-in-from-top-4 duration-300">
                                {/* Price & Category */}
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                    <div className="space-y-2">
                                        <label className="text-sm font-bold text-slate-400 uppercase tracking-wider">Price (Cents)</label>
                                        <div className="relative">
                                            <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" size={18} />
                                            <input 
                                                type="number"
                                                value={configData.price_cents || ''}
                                                onChange={(e) => handleInputChange('price_cents', e.target.value)}
                                                placeholder="e.g. 1000 for $10.00"
                                                className="w-full bg-black/40 border border-white/10 rounded-xl py-3 pl-10 pr-4 text-white focus:outline-none focus:border-indigo-500 transition-colors"
                                            />
                                        </div>
                                        <p className="text-xs text-slate-500">Current: ${((parseInt(configData.price_cents) || 0) / 100).toFixed(2)} USD</p>
                                    </div>
                                    <div className="space-y-2">
                                        <label className="text-sm font-bold text-slate-400 uppercase tracking-wider">Category</label>
                                        <div className="relative">
                                            <Tag className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" size={18} />
                                            <select 
                                                value={configData.category || 'automation'}
                                                onChange={(e) => handleInputChange('category', e.target.value)}
                                                className="w-full bg-black/40 border border-white/10 rounded-xl py-3 pl-10 pr-4 text-white focus:outline-none focus:border-indigo-500 transition-colors appearance-none"
                                            >
                                                <option value="automation">Automation</option>
                                                <option value="scraper">Web Scraper</option>
                                                <option value="bot">Social Bot</option>
                                                <option value="utility">Utility</option>
                                                <option value="trading">Trading/Finance</option>
                                            </select>
                                        </div>
                                    </div>
                                </div>

                                {/* Descriptions */}
                                <div className="space-y-2">
                                    <label className="text-sm font-bold text-slate-400 uppercase tracking-wider">Short Description</label>
                                    <textarea 
                                        value={configData.short_description || ''}
                                        onChange={(e) => handleInputChange('short_description', e.target.value)}
                                        placeholder="A punchy 1-sentence description for the search results."
                                        rows={2}
                                        className="w-full bg-black/40 border border-white/10 rounded-xl p-4 text-white focus:outline-none focus:border-indigo-500 transition-colors resize-none"
                                    />
                                </div>

                                <div className="space-y-2">
                                    <label className="text-sm font-bold text-slate-400 uppercase tracking-wider">Long Description (Markdown)</label>
                                    <textarea 
                                        value={configData.long_description || ''}
                                        onChange={(e) => handleInputChange('long_description', e.target.value)}
                                        placeholder="Explain features, usage, and why people should buy it."
                                        rows={6}
                                        className="w-full bg-black/40 border border-white/10 rounded-xl p-4 text-white focus:outline-none focus:border-indigo-500 transition-colors font-mono text-sm"
                                    />
                                </div>
                            </div>
                        )}

                        <button
                            onClick={handleSave}
                            disabled={isSaving}
                            className={`w-full py-4 rounded-2xl font-bold flex items-center justify-center gap-2 transition-all ${isSaving ? 'bg-slate-800 text-slate-500' : 'bg-indigo-600 text-white hover:bg-indigo-500 shadow-lg shadow-indigo-500/20'}`}
                        >
                            {isSaving ? <Spinner size="sm" /> : <Store size={20} />}
                            {isSaving ? 'Saving...' : 'Save Monetization Settings'}
                        </button>
                    </div>
                </div>

                {/* Right Column: Info/Status */}
                <div className="space-y-6">
                    <div className="glass-card p-6 bg-indigo-500/5 border-indigo-500/20">
                        <h4 className="font-bold text-white mb-4 flex items-center gap-2">
                            <Info size={18} className="text-indigo-400" />
                            How it works
                        </h4>
                        <ul className="space-y-4 text-sm text-slate-400">
                            <li className="flex gap-3">
                                <div className="w-5 h-5 rounded-full bg-indigo-500/20 text-indigo-400 flex items-center justify-center text-[10px] font-bold shrink-0 mt-0.5">1</div>
                                <p>Once published, your project gets a public URL on <code className="text-indigo-300">codevault.io/store</code>.</p>
                            </li>
                            <li className="flex gap-3">
                                <div className="w-5 h-5 rounded-full bg-indigo-500/20 text-indigo-400 flex items-center justify-center text-[10px] font-bold shrink-0 mt-0.5">2</div>
                                <p>Customers pay via Dodo Payments. We handle the taxes and processing.</p>
                            </li>
                            <li className="flex gap-3">
                                <div className="w-5 h-5 rounded-full bg-indigo-500/20 text-indigo-400 flex items-center justify-center text-[10px] font-bold shrink-0 mt-0.5">3</div>
                                <p>Upon successful payment, a unique license key is generated and emailed to the buyer.</p>
                            </li>
                            <li className="flex gap-3">
                                <div className="w-5 h-5 rounded-full bg-indigo-500/20 text-indigo-400 flex items-center justify-center text-[10px] font-bold shrink-0 mt-0.5">4</div>
                                <p>Earnings are added to your balance. Payouts are processed every 7 days.</p>
                            </li>
                        </ul>
                    </div>

                    {configData.is_public_store && configData.dodo_product_id && (
                        <div className="glass-card p-6 border-emerald-500/20">
                            <h4 className="font-bold text-white mb-2">Active Listing</h4>
                            <p className="text-sm text-slate-500 mb-4">Your project is linked to Dodo Product:</p>
                            <code className="block p-2 bg-black/40 rounded border border-white/5 text-xs text-emerald-400 mb-4 truncate">
                                {configData.dodo_product_id}
                            </code>
                            <button className="w-full py-2 bg-white/5 hover:bg-white/10 text-white rounded-lg text-sm font-medium flex items-center justify-center gap-2 transition-all">
                                <ExternalLink size={14} />
                                View Public Page
                            </button>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
});

Step5Monetization.displayName = 'Step5Monetization';

export default Step5Monetization;
