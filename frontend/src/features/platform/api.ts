import { clearToken, getToken } from "./token";

export type ClassRelation = { class_id: string; relation: string };

export type Actor = {
  user_id: string;
  display_name: string;
  role_id: string;
  permissions: string[];
  classes: ClassRelation[];
};

export type Member = {
  user_id: string;
  display_name: string;
  relation: string;
};

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body !== undefined) headers.set("Content-Type", "application/json");
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);

  let response: Response;
  try {
    response = await fetch(`/api${path}`, { ...init, headers });
  } catch {
    throw new ApiError(0, "network_error", "无法连接服务，请确认后端已启动。");
  }

  const payload = (await response.json().catch(() => null)) as
    | { error?: { code?: string; message?: string } }
    | null;

  if (!response.ok) {
    if (response.status === 401) clearToken();
    const error = payload?.error ?? {};
    throw new ApiError(
      response.status,
      error.code ?? "unexpected_error",
      error.message ?? "服务暂时不可用，请稍后再试。",
    );
  }
  return payload as T;
}

export function login(login: string, password: string): Promise<{ access_token: string }> {
  return request<{ access_token: string }>("/login", {
    method: "POST",
    body: JSON.stringify({ login, password }),
  });
}

export function fetchMe(): Promise<Actor> {
  return request<Actor>("/me");
}

export function fetchMembers(
  classId: string,
  relation?: string,
): Promise<{ items: Member[] }> {
  const query = relation ? `?relation=${encodeURIComponent(relation)}` : "";
  return request<{ items: Member[] }>(`/classes/${encodeURIComponent(classId)}/members${query}`);
}
