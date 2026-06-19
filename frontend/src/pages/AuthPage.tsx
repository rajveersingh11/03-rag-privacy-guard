import React, { useState } from 'react';
import { useApp } from '../components/AppContext';
import { apiClient } from '../api/client';
import { ShieldCheck, Lock, User, Eye, EyeOff, ArrowRight } from 'lucide-react';

export const AuthPage: React.FC = () => {
  const { loginUser, showToast } = useApp();
  const [isLogin, setIsLogin] = useState(true);
  
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username || !password) {
      showToast('Please fill in all fields', 'warning');
      return;
    }

    setLoading(true);
    try {
      if (isLogin) {
        const res = await apiClient.login(username, password);
        loginUser(res.username, res.role);
      } else {
        const res = await apiClient.signup(username, password);
        showToast('Admin account provisioned successfully!', 'success');
        loginUser(res.username, res.role);
      }
    } catch (err: any) {
      console.error(err);
      showToast(err.message || 'Authentication failed', 'error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#030712] flex items-center justify-center p-4 relative overflow-hidden font-sans">
      {/* Background decorations */}
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-blue-500/10 rounded-full blur-[100px] pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-purple-500/10 rounded-full blur-[100px] pointer-events-none" />

      <div className="w-full max-w-md bg-[#0b0f19] border border-gray-900 rounded-2xl p-8 shadow-2xl relative z-10">
        {/* Logo and title */}
        <div className="text-center mb-8">
          <div className="inline-flex bg-blue-950/40 p-3 rounded-2xl border border-blue-500/25 mb-4 shadow-lg shadow-blue-950/50">
            <ShieldCheck className="w-8 h-8 text-blue-400" />
          </div>
          <h1 className="text-xl font-bold font-mono tracking-wider text-gray-100 uppercase">AEGISVAULT</h1>
          <p className="text-xs text-gray-500 font-light mt-1">Enterprise RAG Privacy Guard Control Center</p>
        </div>

        {/* Tab selector */}
        <div className="flex border border-gray-900 bg-[#030712] rounded-xl p-1 mb-6">
          <button
            type="button"
            onClick={() => { setIsLogin(true); setUsername(''); setPassword(''); }}
            className={`flex-1 py-2 text-xs font-mono font-bold tracking-wider rounded-lg uppercase transition-all duration-200 ${
              isLogin ? 'bg-[#121826] border border-gray-800 text-blue-400' : 'text-gray-500 hover:text-gray-300'
            }`}
          >
            ADMIN SIGN IN
          </button>
          <button
            type="button"
            onClick={() => { setIsLogin(false); setUsername(''); setPassword(''); }}
            className={`flex-1 py-2 text-xs font-mono font-bold tracking-wider rounded-lg uppercase transition-all duration-200 ${
              !isLogin ? 'bg-[#121826] border border-gray-800 text-blue-400' : 'text-gray-500 hover:text-gray-300'
            }`}
          >
            PROVISION ACCOUNT
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <label className="block text-[10px] font-mono font-bold text-gray-400 uppercase tracking-widest">
              Username
            </label>
            <div className="relative">
              <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-600">
                <User className="w-4 h-4" />
              </span>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Enter admin username..."
                className="w-full bg-[#030712] border border-gray-800 rounded-xl pl-11 pr-4 py-3 text-sm font-mono text-gray-200 placeholder-gray-700 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500/20 transition-all"
                required
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <label className="block text-[10px] font-mono font-bold text-gray-400 uppercase tracking-widest">
              Password
            </label>
            <div className="relative">
              <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-600">
                <Lock className="w-4 h-4" />
              </span>
              <input
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter password..."
                className="w-full bg-[#030712] border border-gray-800 rounded-xl pl-11 pr-11 py-3 text-sm font-mono text-gray-200 placeholder-gray-700 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500/20 transition-all"
                required
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3.5 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300 p-0.5 rounded transition-colors"
              >
                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full mt-2 py-3 bg-blue-600 hover:bg-blue-500 disabled:bg-blue-800 disabled:text-gray-500 text-gray-100 rounded-xl text-xs font-mono font-bold tracking-wider flex items-center justify-center space-x-2 shadow-lg shadow-blue-950/40 glow-blue transition-all duration-200"
          >
            <span>{loading ? 'PROCESSING...' : isLogin ? 'SIGN IN GATEWAY' : 'CREATE ACCOUNT'}</span>
            {!loading && <ArrowRight className="w-4 h-4" />}
          </button>
        </form>

        <div className="text-[10px] font-mono text-gray-500 bg-gray-950/20 p-4 rounded-xl border border-gray-900 mt-6 leading-relaxed text-center">
          {isLogin ? (
            <span>Authorized administrators only. Provision new accounts to request keys.</span>
          ) : (
            <span>Provisioning will store cryptographically hashed credentials inside relational storage.</span>
          )}
        </div>
      </div>
    </div>
  );
};
