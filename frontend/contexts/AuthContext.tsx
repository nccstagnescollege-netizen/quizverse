'use client';

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { supabase } from '@/lib/supabase';

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

function setAuthCookie(token: string) {
  if (typeof document !== 'undefined') {
    document.cookie = `quizverse_auth_token=${token}; path=/; max-age=604800; SameSite=Lax;`;
  }
}

function clearAuthCookie() {
  if (typeof document !== 'undefined') {
    document.cookie = 'quizverse_auth_token=; path=/; max-age=0; SameSite=Lax;';
  }
}

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
      clearAuthCookie();
      setToken(null);
      setUser(null);
    }
  }, [token, fetchProfile]);

  useEffect(() => {
    let isMounted = true;

    async function initializeSession() {
      // 1. Check Supabase Auth active session first if available
      if (supabase) {
        try {
          const { data: { session } } = await supabase.auth.getSession();
          if (session?.access_token) {
            const profile = await fetchProfile(session.access_token);
            if (profile && isMounted) {
              localStorage.setItem('quizverse_admin_token', session.access_token);
              setAuthCookie(session.access_token);
              setToken(session.access_token);
              setUser(profile);
              setIsLoading(false);
              return;
            } else if (!profile && isMounted) {
              // User has Supabase session but is not an administrator
              await supabase.auth.signOut();
            }
          }
        } catch {
          // Fall through to stored token verification
        }
      }

      // 2. Check saved localStorage token
      const savedToken = localStorage.getItem('quizverse_admin_token');
      if (savedToken) {
        setToken(savedToken);
        const profile = await fetchProfile(savedToken);
        if (profile && isMounted) {
          setAuthCookie(savedToken);
          setUser(profile);
        } else if (isMounted) {
          localStorage.removeItem('quizverse_admin_token');
          clearAuthCookie();
          setToken(null);
          setUser(null);
        }
      }

      if (isMounted) {
        setIsLoading(false);
      }
    }

    initializeSession();

    // 3. Listen to Supabase Auth state changes if available
    let authListener: { unsubscribe: () => void } | null = null;
    if (supabase) {
      const { data } = supabase.auth.onAuthStateChange(async (event, session) => {
        if (!isMounted) return;

        if (event === 'SIGNED_OUT') {
          localStorage.removeItem('quizverse_admin_token');
          clearAuthCookie();
          setToken(null);
          setUser(null);
        } else if (event === 'SIGNED_IN' && session?.access_token) {
          const profile = await fetchProfile(session.access_token);
          if (profile && isMounted) {
            localStorage.setItem('quizverse_admin_token', session.access_token);
            setAuthCookie(session.access_token);
            setToken(session.access_token);
            setUser(profile);
          }
        }
      });
      authListener = data.subscription;
    }

    return () => {
      isMounted = false;
      if (authListener) {
        authListener.unsubscribe();
      }
    };
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
    const normalizedEmail = email.trim().toLowerCase();

    try {
      let authToken: string | null = null;
      let adminProfile: AdminProfile | null = null;

      // 1. Try Supabase Auth first if configured
      if (supabase) {
        try {
          const { data: sbData, error: sbError } = await supabase.auth.signInWithPassword({
            email: normalizedEmail,
            password,
          });

          if (!sbError && sbData?.session?.access_token) {
            authToken = sbData.session.access_token;
            // Validate that this Supabase user is an administrator in QUIZVERSE database
            adminProfile = await fetchProfile(authToken);

            if (!adminProfile) {
              // Public user exists in Supabase Auth, but is not an administrator in QUIZVERSE
              await supabase.auth.signOut();
              clearAuthCookie();
              localStorage.removeItem('quizverse_admin_token');
              setIsLoading(false);
              return {
                success: false,
                error: 'Access Denied: This account is not authorized as an administrator. Public users cannot access the admin console.',
              };
            }
          }
        } catch {
          // Fall through to backend login
        }
      }

      // 2. Fallback to QUIZVERSE Backend API Auth
      if (!authToken || !adminProfile) {
        const res = await fetch(`${API_BASE}/auth/login`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email: normalizedEmail, password }),
        });

        const data = await res.json();
        if (!res.ok) {
          setIsLoading(false);
          const errMsg = data.error?.message || data.detail || 'Authentication failed. Please verify credentials.';
          return { success: false, error: errMsg };
        }

        authToken = data.access_token;
        adminProfile = data.user;
      }

      if (!authToken || !adminProfile) {
        setIsLoading(false);
        return { success: false, error: 'Authentication failed. No administrator record found.' };
      }

      // Check account status
      if (adminProfile.status !== 'active') {
        setIsLoading(false);
        return {
          success: false,
          error: `Administrator account is ${adminProfile.status}. Access denied.`,
        };
      }

      // Persist token in localStorage and cookie for Next.js middleware protection
      localStorage.setItem('quizverse_admin_token', authToken);
      setAuthCookie(authToken);
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
    if (supabase) {
      try {
        await supabase.auth.signOut();
      } catch {
        // Proceed with logout
      }
    }

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
    clearAuthCookie();
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
