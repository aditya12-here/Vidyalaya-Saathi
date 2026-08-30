import React, { createContext, useContext, useState, useEffect } from 'react';
import type { ReactNode } from 'react';
import axios from 'axios';

type Role = 'DISTRICT_OFFICER' | 'SCHOOL_MANAGEMENT' | 'SURVEYOR' | 'COMMUNITY';

interface User {
    user_id: string;
    email: string;
    role: Role;
    is_global: boolean;
    school_id: string | null;
}

interface AuthContextType {
    user: User | null;
    token: string | null;
    login: (token: string, userData: any) => void;
    logout: () => void;
    isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const API_BASE = 'http://localhost:8000/api/v1';

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
    const [user, setUser] = useState<User | null>(null);
    const [token, setToken] = useState<string | null>(localStorage.getItem('token'));
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        const fetchUser = async () => {
            if (token) {
                try {
                    axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
                    const res = await axios.get(`${API_BASE}/auth/me`);
                    setUser(res.data);
                } catch (err) {
                    console.error('Session expired or invalid', err);
                    logout();
                }
            }
            setIsLoading(false);
        };
        fetchUser();
    }, [token]);

    const login = (newToken: string, userData: any) => {
        localStorage.setItem('token', newToken);
        setToken(newToken);
        axios.defaults.headers.common['Authorization'] = `Bearer ${newToken}`;
        // we'll get the real user from /me on the effect, but can pre-fill here if passed
        if (userData) {
            setUser({
                user_id: userData.user_id || '',
                email: userData.email || '',
                role: userData.role as Role,
                is_global: userData.role === 'DISTRICT_OFFICER' || userData.role === 'SURVEYOR',
                school_id: userData.school_id || null
            });
        }
    };

    const logout = () => {
        localStorage.removeItem('token');
        setToken(null);
        setUser(null);
        delete axios.defaults.headers.common['Authorization'];
    };

    return (
        <AuthContext.Provider value={{ user, token, login, logout, isLoading }}>
            {children}
        </AuthContext.Provider>
    );
};

export const useAuth = () => {
    const context = useContext(AuthContext);
    if (context === undefined) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
};
