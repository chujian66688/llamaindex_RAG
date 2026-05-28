import { createRouter, createWebHistory } from 'vue-router';
import HomeView from '../views/HomeView.vue';
import ChatView from '../views/ChatView.vue';
import AdminLogin from '../views/AdminLogin.vue';
import AdminLayout from '../layouts/AdminLayout.vue';
import DocumentManage from '../views/DocumentManage.vue';
import UserManage from '../views/UserManage.vue';
import { useUserStore } from '../stores/user';

const routes = [
  { path: '/', component: HomeView },
  { path: '/chat/:conversationId?', component: ChatView },
  { path: '/admin', component: AdminLogin },
  {
    path: '/admin',
    component: AdminLayout,
    meta: { requiresAdmin: true },
    children: [
      { path: 'users', component: UserManage },
      { path: 'documents', component: DocumentManage },
      { path: '', redirect: '/admin/users' },
    ],
  },
];

export const router = createRouter({
  history: createWebHistory(),
  routes,
});

// 路由守卫
router.beforeEach((to, _from, next) => {
  const userStore = useUserStore();

  // 检查路由或其父路由是否需要管理员权限
  const requiresAdmin = to.matched.some(record => record.meta.requiresAdmin);

  if (requiresAdmin) {
    if (!userStore.token) {
      next('/admin');
    } else if (!userStore.isAdmin) {
      next('/admin');
    } else {
      next();
    }
  } else {
    next();
  }
});
