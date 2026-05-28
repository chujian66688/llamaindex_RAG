<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue';
import axios from 'axios';

const VITE_API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface UserInfo {
  username: string;
  email: string | null;
  full_name: string | null;
  disabled: boolean;
  role: string;
  created_at: string | null;
  updated_at: string | null;
}

const users = ref<UserInfo[]>([]);
const loading = ref(false);

const dialogVisible = ref(false);
const dialogMode = ref<'create' | 'edit'>('create');
const editingUsername = ref('');

const form = reactive({
  username: '',
  password: '',
  email: '',
  full_name: '',
  role: 'user',
  disabled: false,
});

const deleteDialogVisible = ref(false);
const deleteTarget = ref<UserInfo | null>(null);

const message = ref('');
const messageType = ref<'success' | 'error'>('success');
const messageVisible = ref(false);

function showMessage(text: string, type: 'success' | 'error' = 'success') {
  message.value = text;
  messageType.value = type;
  messageVisible.value = true;
  setTimeout(() => { messageVisible.value = false; }, 3000);
}

function formatTime(iso: string | null): string {
  if (!iso) return '-';
  try {
    return new Date(iso).toLocaleString('zh-CN');
  } catch {
    return iso;
  }
}

function resetForm() {
  form.username = '';
  form.password = '';
  form.email = '';
  form.full_name = '';
  form.role = 'user';
  form.disabled = false;
}

function openCreateDialog() {
  resetForm();
  dialogMode.value = 'create';
  dialogVisible.value = true;
}

function openEditDialog(user: UserInfo) {
  dialogMode.value = 'edit';
  editingUsername.value = user.username;
  form.username = user.username;
  form.password = '';
  form.email = user.email || '';
  form.full_name = user.full_name || '';
  form.role = user.role;
  form.disabled = user.disabled;
  dialogVisible.value = true;
}

async function loadUsers() {
  loading.value = true;
  try {
    const resp = await axios.get(`${VITE_API_URL}/users/admin/users`);
    users.value = resp.data.users || [];
  } catch (err: any) {
    showMessage('加载用户列表失败: ' + (err.response?.data?.detail || err.message), 'error');
  } finally {
    loading.value = false;
  }
}

async function handleSubmit() {
  if (dialogMode.value === 'create') {
    await handleCreate();
  } else {
    await handleUpdate();
  }
}

async function handleCreate() {
  if (!form.username || !form.password) {
    showMessage('用户名和密码不能为空', 'error');
    return;
  }
  try {
    await axios.post(`${VITE_API_URL}/users/admin/users`, {
      username: form.username,
      password: form.password,
      email: form.email || null,
      full_name: form.full_name || null,
      role: form.role,
    });
    showMessage('用户创建成功');
    dialogVisible.value = false;
    await loadUsers();
  } catch (err: any) {
    showMessage('创建失败: ' + (err.response?.data?.detail || err.message), 'error');
  }
}

async function handleUpdate() {
  try {
    const payload: any = {
      email: form.email || null,
      full_name: form.full_name || null,
      role: form.role,
      disabled: form.disabled,
    };
    if (form.password) {
      payload.password = form.password;
    }
    await axios.put(`${VITE_API_URL}/users/admin/users/${editingUsername.value}`, payload);
    showMessage('用户更新成功');
    dialogVisible.value = false;
    await loadUsers();
  } catch (err: any) {
    showMessage('更新失败: ' + (err.response?.data?.detail || err.message), 'error');
  }
}

function confirmDelete(user: UserInfo) {
  deleteTarget.value = user;
  deleteDialogVisible.value = true;
}

async function doDelete() {
  if (!deleteTarget.value) return;
  try {
    await axios.delete(`${VITE_API_URL}/users/admin/users/${deleteTarget.value.username}`);
    showMessage('用户已删除');
    await loadUsers();
  } catch (err: any) {
    showMessage('删除失败: ' + (err.response?.data?.detail || err.message), 'error');
  } finally {
    deleteDialogVisible.value = false;
    deleteTarget.value = null;
  }
}

onMounted(() => {
  loadUsers();
});
</script>

<template>
  <div class="user-manage">
      <header class="user-manage__header">
        <h1 class="user-manage__title">用户管理</h1>
        <button class="user-manage__add-btn" @click="openCreateDialog">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 5v14M5 12h14" />
          </svg>
          <span>添加用户</span>
        </button>
      </header>

      <!-- 用户列表 -->
      <section class="user-manage__list">
        <div v-if="loading" class="user-manage__loading">
          <div class="user-manage__loading-spinner"></div>
          <span>加载中...</span>
        </div>
        <div v-else-if="users.length === 0" class="user-manage__empty">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" opacity="0.3">
            <path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2" />
            <circle cx="9" cy="7" r="4" />
          </svg>
          <p>暂无用户</p>
        </div>
        <div v-else class="user-manage__table-wrapper">
          <table class="user-manage__table">
            <thead>
              <tr>
                <th>用户名</th>
                <th>姓名</th>
                <th>邮箱</th>
                <th>角色</th>
                <th>状态</th>
                <th>创建时间</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="user in users" :key="user.username">
                <td class="user-manage__td-username">
                  <div class="user-manage__avatar-sm">
                    {{ (user.username || 'U').charAt(0).toUpperCase() }}
                  </div>
                  <span>{{ user.username }}</span>
                </td>
                <td>{{ user.full_name || '-' }}</td>
                <td>{{ user.email || '-' }}</td>
                <td>
                  <span class="user-manage__role-badge" :class="`user-manage__role-badge--${user.role}`">
                    {{ user.role === 'admin' ? '管理员' : '普通用户' }}
                  </span>
                </td>
                <td>
                  <span class="user-manage__status" :class="user.disabled ? 'user-manage__status--disabled' : 'user-manage__status--active'">
                    {{ user.disabled ? '已禁用' : '正常' }}
                  </span>
                </td>
                <td>{{ formatTime(user.created_at) }}</td>
                <td class="user-manage__td-actions">
                  <button class="user-manage__action-btn user-manage__action-btn--edit" @click="openEditDialog(user)" title="编辑">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7" />
                      <path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z" />
                    </svg>
                  </button>
                  <button class="user-manage__action-btn user-manage__action-btn--delete" @click="confirmDelete(user)" title="删除">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2" />
                    </svg>
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <!-- 创建/编辑弹框 -->
      <Teleport to="body">
        <Transition name="dialog">
          <div v-if="dialogVisible" class="user-dialog-overlay" @click.self="dialogVisible = false">
            <div class="user-dialog">
              <div class="user-dialog__header">
                <h3>{{ dialogMode === 'create' ? '添加用户' : '编辑用户' }}</h3>
                <button class="user-dialog__close" @click="dialogVisible = false">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M18 6L6 18M6 6l12 12" />
                  </svg>
                </button>
              </div>
              <div class="user-dialog__body">
                <div class="user-manage__form-group">
                  <label>用户名</label>
                  <input
                    v-model="form.username"
                    type="text"
                    :disabled="dialogMode === 'edit'"
                    placeholder="请输入用户名"
                  />
                </div>
                <div class="user-manage__form-group">
                  <label>{{ dialogMode === 'create' ? '密码' : '新密码（留空则不修改）' }}</label>
                  <input v-model="form.password" type="password" placeholder="请输入密码" />
                </div>
                <div class="user-manage__form-group">
                  <label>姓名</label>
                  <input v-model="form.full_name" type="text" placeholder="请输入姓名" />
                </div>
                <div class="user-manage__form-group">
                  <label>邮箱</label>
                  <input v-model="form.email" type="email" placeholder="请输入邮箱" />
                </div>
                <div class="user-manage__form-group">
                  <label>角色</label>
                  <select v-model="form.role">
                    <option value="user">普通用户</option>
                    <option value="admin">管理员</option>
                  </select>
                </div>
                <div v-if="dialogMode === 'edit'" class="user-manage__form-group">
                  <label class="user-manage__checkbox-label">
                    <input v-model="form.disabled" type="checkbox" />
                    <span>禁用该用户</span>
                  </label>
                </div>
              </div>
              <div class="user-dialog__footer">
                <button class="user-dialog__btn user-dialog__btn--cancel" @click="dialogVisible = false">取消</button>
                <button class="user-dialog__btn user-dialog__btn--confirm" @click="handleSubmit">
                  {{ dialogMode === 'create' ? '创建' : '保存' }}
                </button>
              </div>
            </div>
          </div>
        </Transition>
      </Teleport>

      <!-- 删除确认弹框 -->
      <Teleport to="body">
        <Transition name="dialog">
          <div v-if="deleteDialogVisible" class="user-dialog-overlay" @click.self="deleteDialogVisible = false">
            <div class="user-dialog user-dialog--delete">
              <div class="user-dialog__icon">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                  <circle cx="12" cy="12" r="10" />
                  <path d="M12 8v4M12 16h.01" />
                </svg>
              </div>
              <h3>确认删除</h3>
              <p>确定要删除用户「{{ deleteTarget?.username }}」吗？<br/>删除后将无法恢复。</p>
              <div class="user-dialog__actions">
                <button class="user-dialog__btn user-dialog__btn--cancel" @click="deleteDialogVisible = false">取消</button>
                <button class="user-dialog__btn user-dialog__btn--danger" @click="doDelete">确认删除</button>
              </div>
            </div>
          </div>
        </Transition>
      </Teleport>

      <!-- 消息提示 -->
      <Transition name="msg">
        <div v-if="messageVisible" class="user-manage__message" :class="`user-manage__message--${messageType}`">
          {{ message }}
        </div>
      </Transition>
    </div>
</template>

<style scoped>
.user-manage {
  max-width: 1100px;
}

.user-manage__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-6);
}

.user-manage__title {
  font-size: var(--text-2xl);
  font-weight: var(--font-semibold);
  color: var(--color-text);
}

.user-manage__add-btn {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-4);
  background-color: var(--color-accent);
  color: white;
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  transition: all var(--transition-fast);
}

.user-manage__add-btn:hover {
  background-color: var(--color-accent-dark);
  transform: translateY(-1px);
}

/* 列表 */
.user-manage__list {
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-6);
}

.user-manage__loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-3);
  padding: var(--space-12);
  color: var(--color-text-tertiary);
}

.user-manage__loading-spinner {
  width: 24px;
  height: 24px;
  border: 3px solid var(--color-border);
  border-top-color: var(--color-accent);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.user-manage__empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-12);
  color: var(--color-text-tertiary);
}

.user-manage__empty p {
  font-size: var(--text-sm);
}

.user-manage__table-wrapper {
  overflow-x: auto;
}

.user-manage__table {
  width: 100%;
  border-collapse: collapse;
}

.user-manage__table th {
  text-align: left;
  padding: var(--space-3) var(--space-4);
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  color: var(--color-text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  border-bottom: 1px solid var(--color-border);
}

.user-manage__table td {
  padding: var(--space-3) var(--space-4);
  font-size: var(--text-sm);
  color: var(--color-text);
  border-bottom: 1px solid var(--color-border);
}

.user-manage__table tr:last-child td {
  border-bottom: none;
}

.user-manage__table tr:hover td {
  background-color: var(--color-bg-secondary);
}

.user-manage__td-username {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-weight: var(--font-medium);
}

.user-manage__avatar-sm {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, var(--color-accent), var(--color-accent-light));
  color: white;
  font-weight: var(--font-semibold);
  font-size: var(--text-xs);
  border-radius: var(--radius-full);
}

.user-manage__role-badge {
  display: inline-block;
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
}

.user-manage__role-badge--admin {
  background: rgba(74, 108, 247, 0.1);
  color: var(--color-accent);
}

.user-manage__role-badge--user {
  background: var(--color-bg-secondary);
  color: var(--color-text-secondary);
}

.user-manage__status {
  display: inline-block;
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
}

.user-manage__status--active {
  background: rgba(34, 197, 94, 0.1);
  color: var(--color-success);
}

.user-manage__status--disabled {
  background: rgba(239, 68, 68, 0.1);
  color: var(--color-error);
}

.user-manage__td-actions {
  display: flex;
  gap: var(--space-2);
}

.user-manage__action-btn {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-sm);
  transition: all var(--transition-fast);
}

.user-manage__action-btn--edit {
  color: var(--color-accent);
  background: var(--color-accent-subtle);
}

.user-manage__action-btn--edit:hover {
  background: var(--color-accent);
  color: white;
}

.user-manage__action-btn--delete {
  color: var(--color-error);
  background: rgba(239, 68, 68, 0.08);
}

.user-manage__action-btn--delete:hover {
  background: var(--color-error);
  color: white;
}

/* 弹框 */
.user-dialog-overlay {
  position: fixed;
  inset: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(4px);
}

.user-dialog {
  background-color: var(--color-bg-elevated);
  border-radius: var(--radius-xl);
  max-width: 480px;
  width: 90%;
  box-shadow: var(--shadow-xl);
}

.user-dialog__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-5) var(--space-6);
  border-bottom: 1px solid var(--color-border);
}

.user-dialog__header h3 {
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
}

.user-dialog__close {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-sm);
  color: var(--color-text-tertiary);
  transition: all var(--transition-fast);
}

.user-dialog__close:hover {
  background: var(--color-bg-secondary);
  color: var(--color-text);
}

.user-dialog__body {
  padding: var(--space-5) var(--space-6);
}

.user-manage__form-group {
  margin-bottom: var(--space-4);
}

.user-manage__form-group label {
  display: block;
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--color-text-secondary);
  margin-bottom: var(--space-1);
}

.user-manage__form-group input,
.user-manage__form-group select {
  width: 100%;
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  font-size: var(--text-sm);
  color: var(--color-text);
  background: var(--color-bg);
  outline: none;
  transition: border-color var(--transition-fast);
}

.user-manage__form-group input:focus,
.user-manage__form-group select:focus {
  border-color: var(--color-accent);
}

.user-manage__form-group input:disabled {
  background: var(--color-bg-secondary);
  color: var(--color-text-tertiary);
}

.user-manage__checkbox-label {
  display: flex !important;
  align-items: center;
  gap: var(--space-2);
  cursor: pointer;
}

.user-manage__checkbox-label input {
  width: auto !important;
  accent-color: var(--color-accent);
}

.user-dialog__footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-3);
  padding: var(--space-4) var(--space-6);
  border-top: 1px solid var(--color-border);
}

.user-dialog__btn {
  padding: var(--space-2) var(--space-5);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  transition: all var(--transition-fast);
}

.user-dialog__btn--cancel {
  background-color: var(--color-bg-secondary);
  color: var(--color-text);
}

.user-dialog__btn--cancel:hover {
  background-color: var(--color-bg-tertiary);
}

.user-dialog__btn--confirm {
  background-color: var(--color-accent);
  color: white;
}

.user-dialog__btn--confirm:hover {
  background-color: var(--color-accent-dark);
}

.user-dialog__btn--danger {
  background-color: var(--color-error);
  color: white;
}

.user-dialog__btn--danger:hover {
  background-color: #dc2626;
}

/* 删除弹框 */
.user-dialog--delete {
  padding: var(--space-8);
  text-align: center;
  max-width: 400px;
}

.user-dialog__icon {
  display: flex;
  justify-content: center;
  margin-bottom: var(--space-4);
  color: var(--color-warning);
}

.user-dialog--delete h3 {
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  margin-bottom: var(--space-2);
}

.user-dialog--delete p {
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  line-height: 1.6;
  margin-bottom: var(--space-6);
}

.user-dialog__actions {
  display: flex;
  gap: var(--space-3);
  justify-content: center;
}

/* 消息提示 */
.user-manage__message {
  position: fixed;
  top: var(--space-6);
  left: 50%;
  transform: translateX(-50%);
  padding: var(--space-3) var(--space-6);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  z-index: 2000;
  box-shadow: var(--shadow-lg);
}

.user-manage__message--success {
  background: var(--color-success);
  color: white;
}

.user-manage__message--error {
  background: var(--color-error);
  color: white;
}

/* 动画 */
.dialog-enter-active {
  transition: all 0.3s ease-out;
}

.dialog-leave-active {
  transition: all 0.2s ease-in;
}

.dialog-enter-from,
.dialog-leave-to {
  opacity: 0;
}

.dialog-enter-from .user-dialog {
  transform: scale(0.95) translateY(10px);
  opacity: 0;
}

.dialog-enter-active .user-dialog {
  transition: all 0.3s ease-out;
}

.dialog-leave-active .user-dialog {
  transition: all 0.2s ease-in;
}

.dialog-leave-to .user-dialog {
  transform: scale(0.95) translateY(10px);
  opacity: 0;
}

.msg-enter-active {
  transition: all 0.3s ease-out;
}

.msg-leave-active {
  transition: all 0.2s ease-in;
}

.msg-enter-from {
  opacity: 0;
  transform: translateX(-50%) translateY(-20px);
}

.msg-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(-20px);
}

/* 响应式 */
@media (max-width: 768px) {
  .user-manage__table th:nth-child(3),
  .user-manage__table td:nth-child(3),
  .user-manage__table th:nth-child(6),
  .user-manage__table td:nth-child(6) {
    display: none;
  }
}
</style>
