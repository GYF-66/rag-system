import { createPinia, setActivePinia } from 'pinia';

import { useAuthStore } from '@/stores/auth';

describe('Auth Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    localStorage.clear();
    vi.restoreAllMocks();
    global.fetch = vi.fn();
  });

  it('restores persisted auth state from localStorage', () => {
    localStorage.setItem('auth_access_token', 'access-token');
    localStorage.setItem('auth_refresh_token', 'refresh-token');
    localStorage.setItem('auth_user', JSON.stringify({ user_id: 'u1', username: 'demo' }));

    const store = useAuthStore();

    expect(store.accessToken).toBe('access-token');
    expect(store.refreshToken).toBe('refresh-token');
    expect(store.user).toEqual({ user_id: 'u1', username: 'demo' });
    expect(store.isAuthenticated).toBe(true);
  });

  it('persists auth data via setAuth', () => {
    const store = useAuthStore();

    store.setAuth({
      access_token: 'access-token',
      refresh_token: 'refresh-token',
      token_type: 'bearer',
      expires_in: 3600,
      user: { user_id: 'u2', username: 'tester' },
    });

    expect(localStorage.getItem('auth_access_token')).toBe('access-token');
    expect(localStorage.getItem('auth_refresh_token')).toBe('refresh-token');
    expect(store.user?.username).toBe('tester');
    expect(store.isAuthenticated).toBe(true);
  });

  it('clears auth state via clearAuth', () => {
    const store = useAuthStore();
    store.setAuth({
      access_token: 'access-token',
      refresh_token: 'refresh-token',
      token_type: 'bearer',
      expires_in: 3600,
      user: { user_id: 'u3', username: 'tester' },
    });

    store.clearAuth();

    expect(store.accessToken).toBeNull();
    expect(store.refreshToken).toBeNull();
    expect(store.user).toBeNull();
    expect(store.isAuthenticated).toBe(false);
  });

  it('refreshes the access token when refresh token exists', async () => {
    const store = useAuthStore();
    store.refreshToken = 'refresh-token';
    vi.mocked(global.fetch).mockResolvedValue(
      new Response(JSON.stringify({ access_token: 'new-token', token_type: 'bearer', expires_in: 3600 }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );

    const ok = await store.refreshAccessToken();

    expect(ok).toBe(true);
    expect(store.accessToken).toBe('new-token');
    expect(localStorage.getItem('auth_access_token')).toBe('new-token');
  });

  it('returns false when no refresh token is available', async () => {
    const store = useAuthStore();

    const ok = await store.refreshAccessToken();

    expect(ok).toBe(false);
    expect(store.isAuthenticated).toBe(false);
  });
});
