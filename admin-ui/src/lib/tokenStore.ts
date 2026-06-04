let accessToken: string | null = null;
let refreshToken: string | null = null;

export const setTokens = (access: string, refresh: string) => {
  accessToken = access;
  refreshToken = refresh;
  if (typeof window !== "undefined") {
    localStorage.setItem("access_token", access);
    localStorage.setItem("refresh_token", refresh);
    document.cookie = `access_token=${access}; path=/; max-age=86400; SameSite=Lax`;
  }
};

export const getAccessToken = () => {
  if (!accessToken && typeof window !== "undefined") {
    accessToken = localStorage.getItem("access_token");
  }
  return accessToken;
};

export const getRefreshToken = () => {
  if (!refreshToken && typeof window !== "undefined") {
    refreshToken = localStorage.getItem("refresh_token");
  }
  return refreshToken;
};

export const clearTokens = () => {
  accessToken = null;
  refreshToken = null;
  if (typeof window !== "undefined") {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    document.cookie = "access_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT";
  }
};

export const refreshAccessToken = async (): Promise<void> => {
  const currentRefresh = getRefreshToken();
  if (!currentRefresh) {
    throw new Error('No refresh token available');
  }
  
  const baseUrl = process.env.NEXT_PUBLIC_API_URL || (process.env.NODE_ENV === 'production' ? "https://cheeseball-v2.vercel.app/api" : "http://localhost:8000/api");
  
  const response = await fetch(`${baseUrl}/auth/token/refresh`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ refresh: currentRefresh }),
  });

  if (!response.ok) {
    clearTokens();
    throw new Error('Failed to refresh access token');
  }

  const data = await response.json();
  if (data.access) {
    setTokens(data.access, data.refresh || currentRefresh);
  } else {
    clearTokens();
    throw new Error('Refresh response missing access token');
  }
};
