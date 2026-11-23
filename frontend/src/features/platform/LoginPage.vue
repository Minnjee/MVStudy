<script setup lang="ts">
import { ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ApiError } from "./api";
import { signIn } from "./session";

const route = useRoute();
const router = useRouter();

const loginName = ref("");
const password = ref("");
const errorMessage = ref("");
const pending = ref(false);

async function handleSubmit(): Promise<void> {
  if (pending.value) return;
  errorMessage.value = "";
  pending.value = true;
  try {
    await signIn(loginName.value.trim(), password.value);
    const redirect = typeof route.query.redirect === "string" ? route.query.redirect : "/";
    await router.replace(redirect);
  } catch (error) {
    errorMessage.value = error instanceof ApiError ? error.message : "登录失败，请稍后再试。";
  } finally {
    pending.value = false;
  }
}
</script>

<template>
  <main class="login">
    <section class="card">
      <h1>机器视觉智慧学习平台</h1>
      <p class="hint">请使用课程分配的账号登录</p>
      <form @submit.prevent="handleSubmit">
        <label>
          登录名
          <input v-model="loginName" name="login" autocomplete="username" required />
        </label>
        <label>
          密码
          <input
            v-model="password"
            name="password"
            type="password"
            autocomplete="current-password"
            required
          />
        </label>
        <p v-if="errorMessage" class="error" role="alert">{{ errorMessage }}</p>
        <button type="submit" :disabled="pending">{{ pending ? "正在登录…" : "登录" }}</button>
      </form>
    </section>
  </main>
</template>

<style scoped>
.login {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}
.card {
  width: 100%;
  max-width: 360px;
  background: #fff;
  border: 1px solid #e2e6ec;
  border-radius: 10px;
  padding: 28px;
  box-shadow: 0 6px 24px rgb(15 33 51 / 6%);
}
h1 {
  margin: 0 0 6px;
  font-size: 20px;
  font-weight: 600;
}
.hint {
  margin: 0 0 20px;
  color: #667085;
  font-size: 13px;
}
form {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
label {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 13px;
  color: #475467;
}
input {
  padding: 9px 11px;
  border: 1px solid #d0d5dd;
  border-radius: 6px;
  font-size: 14px;
}
input:focus {
  outline: 2px solid #1d4ed8;
  outline-offset: 1px;
  border-color: #1d4ed8;
}
button {
  margin-top: 4px;
  padding: 10px 14px;
  background: #1d4ed8;
  color: #fff;
  border: 0;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
}
button:disabled {
  background: #93a7e8;
  cursor: progress;
}
.error {
  margin: 0;
  color: #b42318;
  font-size: 13px;
}
</style>
