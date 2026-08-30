import React, { useState } from 'react';
import axios from 'axios';
import { useAuth } from '../contexts/AuthContext';
import './AuthPage.css';

const API_BASE = 'http://localhost:8000/api/v1';

export const AuthPage: React.FC = () => {
    const { login } = useAuth();
    const [isLogin, setIsLogin] = useState(true);
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [schoolId, setSchoolId] = useState('');
    const [communityId, setCommunityId] = useState('');
    const [error, setError] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);
        setLoading(true);

        try {
            if (isLogin) {
                const params = new URLSearchParams();
                params.append('username', email);
                params.append('password', password);
                
                const res = await axios.post(`${API_BASE}/auth/token`, params, {
                    headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
                });
                
                login(res.data.access_token, res.data);
            } else {
                // Signup is only for community members right now based on our decision
                await axios.post(`${API_BASE}/auth/signup/community`, {
                    email,
                    password,
                    school_id: schoolId,
                    community_id_number: communityId
                });
                
                // Immediately login after signup
                const params = new URLSearchParams();
                params.append('username', email);
                params.append('password', password);
                const loginRes = await axios.post(`${API_BASE}/auth/token`, params);
                login(loginRes.data.access_token, loginRes.data);
            }
        } catch (err: any) {
            console.error(err);
            setError(err.response?.data?.detail || 'An error occurred. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="auth-container">
            <div className="auth-card">
                <h2>{isLogin ? 'Login to Vidyalaya Saathi' : 'Community Signup'}</h2>
                {error && <div className="auth-error">{error}</div>}
                
                <form onSubmit={handleSubmit} className="auth-form">
                    <div className="auth-field">
                        <label>Email</label>
                        <input type="email" value={email} onChange={e => setEmail(e.target.value)} required />
                    </div>
                    <div className="auth-field">
                        <label>Password</label>
                        <input type="password" value={password} onChange={e => setPassword(e.target.value)} required minLength={8} />
                    </div>

                    {!isLogin && (
                        <>
                            <div className="auth-field">
                                <label>School ID (UDISE / Code)</label>
                                <input type="text" value={schoolId} onChange={e => setSchoolId(e.target.value)} required />
                            </div>
                            <div className="auth-field">
                                <label>Student / Teacher ID Number</label>
                                <input type="text" value={communityId} onChange={e => setCommunityId(e.target.value)} required />
                            </div>
                            <p className="auth-hint">Note: Only Community (Students/Parents/Teachers) can sign up here. Officials must be invited.</p>
                        </>
                    )}

                    <button type="submit" disabled={loading} className="auth-btn">
                        {loading ? 'Processing...' : (isLogin ? 'Login' : 'Sign Up')}
                    </button>
                </form>
                
                <div className="auth-toggle">
                    {isLogin ? "Don't have an account? " : "Already have an account? "}
                    <button type="button" onClick={() => setIsLogin(!isLogin)} className="auth-toggle-btn">
                        {isLogin ? 'Sign up as Community' : 'Login'}
                    </button>
                </div>
            </div>
        </div>
    );
};
