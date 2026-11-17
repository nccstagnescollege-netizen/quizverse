'use client';

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';

export interface AdminProfile {
  id: string;
  email: string;
  full_name: string;
  status: string;
  is_super_admin: boolean;
  roles: string[];
  permissions: string[];
  last_login_at?: string;
  created_at: string;
}

interface AuthContextType {
  user: AdminProfile | null;
  token: string | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  isSuperAdmin: boolean;
  hasPermission: (permission: string) => boolean;
  login: (email: string, password: string) => Promise<{ success: boolean; error?: string }>;
  logout: () => Promise<void>;
  refreshProfile: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AdminProfile | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const router = useRouter();

  const fetchProfile = useCallback(async (authToken: string): Promise<AdminProfile | null> => {
    try {
      const res = await fetch(`${API_BASE}/auth/me`, {
        headers: {
          Authorization: `Bearer ${authToken}`,
        },
      });
      if (res.ok) {
        const data = await res.json();
        return data;
      }
      return null;
    } catch {
      return null;
    }
  }, []);

  const refreshProfile = useCallback(async () => {
    if (!token) return;
    const profile = await fetchProfile(token);
    if (profile) {
      setUser(profile);
    } else {
      // Token invalid or revoked
      localStorage.removeItem('quizverse_admin_token');
      setToken(null);
      setUser(null);
    }
  }, [token, fetchProfile]);

  useEffect(() => {
    const savedToken = localStorage.getItem('quizverse_admin_token');
    if (savedToken) {
      setToken(savedToken);
      fetchProfile(savedToken).then((profile) => {
        if (profile) {
          setUser(profile);
        } else {
          localStorage.removeItem('quizverse_admin_token');
          setToken(null);
        }
        setIsLoading(false);
      });
    } else {
      setIsLoading(false);
    }
  }, [fetchProfile]);

  const hasPermission = useCallback(
    (permission: string): boolean => {
      if (!user) return false;
      if (user.is_super_admin) return true;
      return user.permissions.includes(permission) || user.permissions.includes('*');
    },
    [user]
  );

  const login = async (
    email: string,
    password: string
  ): Promise<{ success: boolean; error?: string }> => {
    setIsLoading(true);
    try {
      const res = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });

      const data = await res.json();
      if (!res.ok) {
        setIsLoading(false);
        const errMsg = data.error?.message || data.detail || 'Authentication failed.';
        return { success: false, error: errMsg };
      }

      const authToken = data.access_token;
      const adminProfile = data.user;

      localStorage.setItem('quizverse_admin_token', authToken);
      setToken(authToken);
      setUser(adminProfile);
      setIsLoading(false);

      // Role-based redirect
      if (adminProfile.is_super_admin) {
        router.push('/super-admin/dashboard');
      } else {
        router.push('/admin/dashboard');
      }

      return { success: true };
    } catch (err: any) {
      setIsLoading(false);
      return { success: false, error: err.message || 'Unable to connect to authentication server.' };
    }
  };

  const logout = async () => {
    if (token) {
      try {
        await fetch(`${API_BASE}/auth/logout`, {
          method: 'POST',
          headers: { Authorization: `Bearer ${token}` },
        });
      } catch {
        // Proceed with client logout even if backend unreachable
      }
    }
    localStorage.removeItem('quizverse_admin_token');
    setToken(null);
    setUser(null);
    router.push('/login');
  };

  const value: AuthContextType = {
    user,
    token,
    isLoading,
    isAuthenticated: !!user,
    isSuperAdmin: !!user?.is_super_admin,
    hasPermission,
    login,
    logout,
    refreshProfile,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
