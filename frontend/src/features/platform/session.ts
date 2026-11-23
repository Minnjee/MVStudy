import { ref } from "vue";
import { ApiError, fetchMe, login as loginRequest, type Actor } from "./api";
import { clearToken, getToken, setToken } from "./token";

/** 当前登录者；结构与 U2 /me 一致，其他页面直接读它。 */
export const currentActor = ref<Actor | null>(null);

export const ROLE_LABELS: Record<string, string> = {
  student: "学生",
  teacher: "教师",
  admin: "管理员",
};

export function roleLabel(roleId: string): string {
  return ROLE_LABELS[roleId] ?? roleId;
}

export async function signIn(login: string, password: string): Promise<Actor> {
  const { access_token } = await loginRequest(login, password);
  setToken(access_token);
  const actor = await fetchMe();
  currentActor.value = actor;
  return actor;
}

export function signOut(): void {
  clearToken();
  currentActor.value = null;
}

/** 刷新后凭已存凭证恢复身份；凭证失效则清除并返回 false。 */
export async function restoreSession(): Promise<boolean> {
  if (!getToken()) return false;
  try {
    currentActor.value = await fetchMe();
    return true;
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) {
      clearToken();
      currentActor.value = null;
      return false;
    }
    throw error;
  }
}
