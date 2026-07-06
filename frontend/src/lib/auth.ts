/** Auth client for the FleetUp backend (cookie-based sessions). */

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8010";

export interface Organization {
  id: number;
  name: string;
}

export interface AuthUser {
  id: number;
  full_name: string;
  email: string;
  role: string;
  organization: Organization;
}

export interface SignupInput {
  full_name: string;
  company_name: string;
  email: string;
  password: string;
}

export class AuthError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

/** Pull a human-readable message out of a FastAPI error body. */
function messageFrom(body: unknown, fallback: string): string {
  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    // 422 validation errors arrive as a list of {loc, msg, ...}.
    if (Array.isArray(detail) && detail.length > 0) {
      const first = detail[0] as { msg?: string };
      if (first?.msg) return first.msg.replace(/^Value error,\s*/, "");
    }
  }
  return fallback;
}

async function authRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    method: "GET",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    ...init,
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new AuthError(messageFrom(body, response.statusText), response.status);
  }
  return response.status === 204 ? (undefined as T) : response.json();
}

export const authApi = {
  me: () => authRequest<AuthUser>("/api/auth/me"),
  login: (email: string, password: string) =>
    authRequest<AuthUser>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  signup: (data: SignupInput) =>
    authRequest<AuthUser>("/api/auth/signup", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  logout: () => authRequest<void>("/api/auth/logout", { method: "POST" }),
};
