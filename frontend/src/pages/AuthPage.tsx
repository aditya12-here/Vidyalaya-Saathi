import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../contexts/AuthContext';
import './AuthPage.css';

const API_BASE = 'http://localhost:8000/api/v1';

interface RegisteredSchool {
    school_id: string;
    name: string;
}

export const AuthPage: React.FC = () => {
    const { login } = useAuth();
    const [isLogin, setIsLogin] = useState(true);
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [schoolId, setSchoolId] = useState('');
    const [communityId, setCommunityId] = useState('');
    const [registeredSchools, setRegisteredSchools] = useState<RegisteredSchool[]>([]);
    const [loadingSchools, setLoadingSchools] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);

    // Fetch registered schools so community users can easily pick their school
    useEffect(() => {
        const fetchSchools = async () => {
            setLoadingSchools(true);
            try {
                const res = await axios.get(`${API_BASE}/explorer/schools`);
                setRegisteredSchools(res.data.schools || []);
                if (res.data.schools && res.data.schools.length > 0 && !schoolId) {
                    setSchoolId(res.data.schools[0].school_id);
                }
            } catch (err) {
                console.error('Could not fetch schools for signup dropdown', err);
            } finally {
                setLoadingSchools(false);
            }
        };
        fetchSchools();
    }, []);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);
        setLoading(true);

        try {
            if (isLogin) {
                // Login only requires username (email) and password
                const params = new URLSearchParams();
                params.append('username', email.trim());
                params.append('password', password);
                
                const res = await axios.post(`${API_BASE}/auth/token`, params, {
                    headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
                });
                
                login(res.data.access_token, res.data);
            } else {
                // Community Signup requires email, password, and a valid school_id
                if (!schoolId) {
                    setError('Please select or enter a registered School ID.');
                    setLoading(false);
                    return;
                }

                await axios.post(`${API_BASE}/auth/signup/community`, {
                    email: email.trim(),
                    password,
                    school_id: schoolId.trim(),
                    community_id_number: communityId.trim() || undefined
                });
                
                // Automatically log in after successful signup
                const params = new URLSearchParams();
                params.append('username', email.trim());
                params.append('password', password);
                const loginRes = await axios.post(`${API_BASE}/auth/token`, params);
                login(loginRes.data.access_token, loginRes.data);
            }
        } catch (err: any) {
            console.error(err);
            setError(err.response?.data?.detail || 'Authentication failed. Please check your credentials.');
        } finally {
            setLoading(false);
        }
    };

    const fillDemoAdmin = () => {
        setEmail('admin@vidyalaya.gov.in');
        setPassword('admin123');
        setIsLogin(true);
        setError(null);
    };

    return (
        <div className="auth-container">
            <div className="auth-card">
                <h2>{isLogin ? 'Login to Vidyalaya Saathi' : 'Community Member Signup'}</h2>
                <p className="auth-subtitle">
                    {isLogin 
                        ? 'Sign in to access your role-based diagnostic dashboard.' 
                        : 'Students, parents, and teachers can register here to report grievances and track school repairs.'}
                </p>

                {error && <div className="auth-error">{error}</div>}
                
                <form onSubmit={handleSubmit} className="auth-form">
                    <div className="auth-field">
                        <label>Email Address *</label>
                        <input 
                            type="email" 
                            value={email} 
                            onChange={e => setEmail(e.target.value)} 
                            placeholder="e.g. user@domain.com"
                            required 
                        />
                    </div>
                    
                    <div className="auth-field">
                        <label>Password (min 8 chars) *</label>
                        <input 
                            type="password" 
                            value={password} 
                            onChange={e => setPassword(e.target.value)} 
                            placeholder="••••••••"
                            required 
                            minLength={8} 
                        />
                    </div>

                    {!isLogin && (
                        <>
                            <div className="auth-field">
                                <label>Your School *</label>
                                {registeredSchools.length > 0 ? (
                                    <select
                                        value={schoolId}
                                        onChange={e => setSchoolId(e.target.value)}
                                        required
                                    >
                                        <option value="">-- Select Your School --</option>
                                        {registeredSchools.map(s => (
                                            <option key={s.school_id} value={s.school_id}>
                                                {s.name} ({s.school_id})
                                            </option>
                                        ))}
                                    </select>
                                ) : (
                                    <input 
                                        type="text" 
                                        value={schoolId} 
                                        onChange={e => setSchoolId(e.target.value)} 
                                        placeholder={loadingSchools ? 'Loading schools...' : 'Enter registered School ID (e.g. SCH-001)'}
                                        required 
                                    />
                                )}
                                {registeredSchools.length === 0 && !loadingSchools && (
                                    <span className="auth-input-hint">
                                        Note: A school must first be registered in the system by the District Officer before signup.
                                    </span>
                                )}
                            </div>

                            <div className="auth-field">
                                <label>Student / Teacher ID / Roll No (Optional)</label>
                                <input 
                                    type="text" 
                                    value={communityId} 
                                    onChange={e => setCommunityId(e.target.value)} 
                                    placeholder="e.g. STU-1042, ROLL-15, or leave blank"
                                />
                            </div>

                            <p className="auth-hint">
                                Note: Officials (District Officers, Surveyors, School Principals) are provisioned directly by the District Administrator.
                            </p>
                        </>
                    )}

                    <button type="submit" disabled={loading} className="auth-btn">
                        {loading ? 'Authenticating...' : (isLogin ? 'Sign In' : 'Create Community Account')}
                    </button>
                </form>
                
                <div className="auth-toggle">
                    {isLogin ? "Are you a student, parent, or local resident? " : "Already registered? "}
                    <button 
                        type="button" 
                        onClick={() => {
                            setIsLogin(!isLogin);
                            setError(null);
                        }} 
                        className="auth-toggle-btn"
                    >
                        {isLogin ? 'Sign up as Community Member' : 'Back to Login'}
                    </button>
                </div>

                {isLogin && (
                    <div className="auth-demo-box">
                        <span>Default District Officer Account:</span>
                        <button type="button" onClick={fillDemoAdmin} className="demo-fill-btn">
                            Auto-fill Admin (admin@vidyalaya.gov.in / admin123)
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
};
