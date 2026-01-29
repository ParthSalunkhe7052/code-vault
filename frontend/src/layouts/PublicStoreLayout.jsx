import { Outlet, Link } from 'react-router-dom';
import { ShoppingBag, Hexagon } from 'lucide-react';

export default function PublicStoreLayout() {
    return (
        <div className="min-h-screen bg-slate-950 text-slate-200 font-sans selection:bg-cyan-500/30">
            {/* Navbar */}
            <header className="border-b border-slate-800 bg-slate-900/50 backdrop-blur-md sticky top-0 z-50">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
                    <Link to="/store" className="flex items-center gap-2 group">
                        <div className="bg-cyan-500/10 p-2 rounded-lg group-hover:bg-cyan-500/20 transition-colors">
                            <Hexagon className="w-6 h-6 text-cyan-400" />
                        </div>
                        <span className="font-bold text-xl tracking-tight text-white">
                            CodeVault <span className="text-cyan-400">Store</span>
                        </span>
                    </Link>

                    <div className="flex items-center gap-4">
                        <Link to="/login" className="text-sm font-medium text-slate-400 hover:text-white transition-colors">
                            Seller Login
                        </Link>
                        <Link 
                            to="/store/cart" 
                            className="p-2 hover:bg-slate-800 rounded-full transition-colors relative"
                        >
                            <ShoppingBag className="w-5 h-5 text-slate-300" />
                            {/* Cart Badge could go here */}
                        </Link>
                    </div>
                </div>
            </header>

            {/* Main Content */}
            <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <Outlet />
            </main>

            {/* Footer */}
            <footer className="border-t border-slate-800 bg-slate-950 mt-auto">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
                    <div className="flex flex-col md:flex-row justify-between items-center gap-6">
                        <div className="flex items-center gap-2">
                            <Hexagon className="w-5 h-5 text-slate-600" />
                            <span className="text-slate-500 font-semibold">CodeVault</span>
                        </div>
                        <div className="text-sm text-slate-600">
                            © {new Date().getFullYear()} CodeVault. All rights reserved.
                        </div>
                    </div>
                </div>
            </footer>
        </div>
    );
}
