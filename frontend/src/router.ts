import { createRouter, createWebHistory } from "vue-router";
import HomePage from "./features/platform/HomePage.vue";
import LoginPage from "./features/platform/LoginPage.vue";
import { currentActor, restoreSession } from "./features/platform/session";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/login", name: "login", component: LoginPage, meta: { public: true } },
    { path: "/", name: "home", component: HomePage },
    { path: "/:pathMatch(.*)*", redirect: "/" },
  ],
});

router.beforeEach(async (to) => {
  if (to.meta.public === true) {
    return currentActor.value ? { path: "/" } : true;
  }
  if (currentActor.value) return true;
  const restored = await restoreSession();
  if (restored) return true;
  return { path: "/login", query: { redirect: to.fullPath } };
});

export default router;
