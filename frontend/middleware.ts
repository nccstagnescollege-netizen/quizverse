import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Protect /super-admin and /admin consoles from public / unauthenticated access
  const isSuperAdminRoute = pathname.startsWith('/super-admin');
  const isAdminRoute = pathname.startsWith('/admin');

  if (isSuperAdminRoute || isAdminRoute) {
    // Check for authentication token in cookies
    // 1. Custom app cookie: 'quizverse_auth_token'
    // 2. Standard Supabase auth cookies: 'sb-access-token' or 'sb-<ref>-auth-token'
    const hasAuthCookie =
      request.cookies.has('quizverse_auth_token') ||
      request.cookies.has('sb-access-token') ||
      Array.from(request.cookies.getAll()).some(
        (c) => c.name.startsWith('sb-') && c.name.endsWith('-auth-token')
      );

    if (!hasAuthCookie) {
      // Public user attempted to access protected administrative console
      const loginUrl = new URL('/login', request.url);
      loginUrl.searchParams.set('redirect', pathname);
      return NextResponse.redirect(loginUrl);
    }
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/super-admin/:path*', '/admin/:path*'],
};
