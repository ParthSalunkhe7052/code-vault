import React, { useState } from 'react';
import { X, Landmark, CreditCard, ShieldCheck, AlertCircle } from 'lucide-react';
import { sellers as sellerApi } from '../services/api';
import Spinner from './Spinner';

const SellerOnboarding = ({ isOpen, onClose, onSuccess }) => {
    const [loading, setLoading] = useState(false);
    const [payoutMethod, setPayoutMethod] = useState('upi'); // 'upi' or 'bank'
    const [details, setDetails] = useState({
        upi_id: '',
        account_name: '',
        account_number: '',
        ifsc_code: '',
        bank_name: ''
    });

    const handleInputChange = (e) => {
        const { name, value } = e.target;
        setDetails(prev => ({ ...prev, [name]: value }));
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);

        // Filter details based on method
        const payoutDetails = payoutMethod === 'upi' 
            ? { method: 'upi', upi_id: details.upi_id }
            : { 
                method: 'bank', 
                account_name: details.account_name,
                account_number: details.account_number,
                ifsc_code: details.ifsc_code,
                bank_name: details.bank_name
              };

        try {
            await sellerApi.onboard({ payout_details: payoutDetails });
            if (onSuccess) onSuccess();
            onClose();
        } catch (err) {
            console.error('Onboarding failed:', err);
            if (window.showToast) window.showToast('Failed to save payout details', 'error');
        } finally {
            setLoading(false);
        }
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-[60] flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
            <div className="bg-slate-900 border border-white/10 rounded-3xl w-full max-w-md overflow-hidden shadow-2xl animate-in zoom-in-95 duration-200">
                <div className="p-6 border-b border-white/5 flex items-center justify-between">
                    <h3 className="text-xl font-bold text-white flex items-center gap-2">
                        <Landmark size={20} className="text-indigo-400" />
                        Seller Onboarding
                    </h3>
                    <button onClick={onClose} className="text-slate-500 hover:text-white transition-colors">
                        <X size={20} />
                    </button>
                </div>

                <form onSubmit={handleSubmit} className="p-6 space-y-6">
                    <div className="bg-indigo-500/10 rounded-2xl p-4 flex gap-3">
                        <ShieldCheck className="text-indigo-400 shrink-0" size={20} />
                        <p className="text-xs text-slate-400">
                            We use Dodo Payments for merchant services. Your payout details are encrypted and stored securely.
                        </p>
                    </div>

                    <div className="space-y-4">
                        <label className="text-sm font-bold text-slate-400 uppercase tracking-wider">Payout Method</label>
                        <div className="grid grid-cols-2 gap-3">
                            <button
                                type="button"
                                onClick={() => setPayoutMethod('upi')}
                                className={`p-3 rounded-xl border-2 transition-all flex flex-col items-center gap-2 ${payoutMethod === 'upi' ? 'border-indigo-500 bg-indigo-500/10 text-white' : 'border-white/5 bg-white/5 text-slate-500 hover:border-white/10'}`}
                            >
                                <CreditCard size={20} />
                                <span className="text-xs font-bold uppercase tracking-tight">UPI ID</span>
                            </button>
                            <button
                                type="button"
                                onClick={() => setPayoutMethod('bank')}
                                className={`p-3 rounded-xl border-2 transition-all flex flex-col items-center gap-2 ${payoutMethod === 'bank' ? 'border-indigo-500 bg-indigo-500/10 text-white' : 'border-white/5 bg-white/5 text-slate-500 hover:border-white/10'}`}
                            >
                                <Landmark size={20} />
                                <span className="text-xs font-bold uppercase tracking-tight">Bank Account</span>
                            </button>
                        </div>
                    </div>

                    {payoutMethod === 'upi' ? (
                        <div className="space-y-2 animate-in slide-in-from-left-4">
                            <label className="text-xs font-bold text-slate-500 uppercase tracking-wider">VPA / UPI ID</label>
                            <input
                                required
                                name="upi_id"
                                value={details.upi_id}
                                onChange={handleInputChange}
                                placeholder="e.g. username@upi"
                                className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-indigo-500"
                            />
                        </div>
                    ) : (
                        <div className="space-y-4 animate-in slide-in-from-right-4">
                            <div className="space-y-2">
                                <label className="text-xs font-bold text-slate-500 uppercase tracking-wider">Account Holder Name</label>
                                <input
                                    required
                                    name="account_name"
                                    value={details.account_name}
                                    onChange={handleInputChange}
                                    className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-indigo-500"
                                />
                            </div>
                            <div className="space-y-2">
                                <label className="text-xs font-bold text-slate-500 uppercase tracking-wider">Account Number</label>
                                <input
                                    required
                                    name="account_number"
                                    value={details.account_number}
                                    onChange={handleInputChange}
                                    className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-indigo-500"
                                />
                            </div>
                            <div className="grid grid-cols-2 gap-4">
                                <div className="space-y-2">
                                    <label className="text-xs font-bold text-slate-500 uppercase tracking-wider">IFSC Code</label>
                                    <input
                                        required
                                        name="ifsc_code"
                                        value={details.ifsc_code}
                                        onChange={handleInputChange}
                                        className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-indigo-500"
                                    />
                                </div>
                                <div className="space-y-2">
                                    <label className="text-xs font-bold text-slate-500 uppercase tracking-wider">Bank Name</label>
                                    <input
                                        required
                                        name="bank_name"
                                        value={details.bank_name}
                                        onChange={handleInputChange}
                                        className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-indigo-500"
                                    />
                                </div>
                            </div>
                        </div>
                    )}

                    <div className="pt-4 flex items-center gap-3">
                        <button
                            type="button"
                            onClick={onClose}
                            className="flex-1 py-3 px-4 rounded-xl bg-white/5 text-slate-400 font-bold hover:bg-white/10 transition-all"
                        >
                            Cancel
                        </button>
                        <button
                            type="submit"
                            disabled={loading}
                            className="flex-[2] py-3 px-4 rounded-xl bg-indigo-600 text-white font-bold hover:bg-indigo-500 shadow-lg shadow-indigo-500/20 transition-all flex items-center justify-center gap-2"
                        >
                            {loading ? <Spinner size="sm" /> : <Landmark size={18} />}
                            {loading ? 'Processing...' : 'Complete Setup'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};

export default SellerOnboarding;
