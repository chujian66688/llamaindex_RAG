<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue';
import axios from 'axios';

const VITE_API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface DocInfo {
  file_name: string;
  doc_id: string;
  file_type: string;
  file_size: number;
  upload_time: string;
}

interface ChunkItem {
  chunk_id: string;
  text: string;
  metadata: {
    file_name: string;
    doc_id: string;
    upload_time: string;
    file_type: string;
    content_type: string;
    chunk_size: number;
  };
}

interface ChunkConfig {
  chunk_size: number;
  chunk_overlap: number;
}

const documents = ref<DocInfo[]>([]);
const loading = ref(false);
const uploadLoading = ref(false);

const chunkConfig = reactive<ChunkConfig>({ chunk_size: 512, chunk_overlap: 50 });
const uploadChunkConfig = reactive<ChunkConfig>({ chunk_size: 512, chunk_overlap: 50 });
const useCustomChunk = ref(false);

const selectedFiles = ref<File[]>([]);

const chunkDialogVisible = ref(false);
const chunkDialogTitle = ref('');
const chunks = ref<ChunkItem[]>([]);
const chunksTotal = ref(0);
const chunksPage = ref(1);
const chunksPageSize = ref(10);
const chunksLoading = ref(false);

const deleteDialogVisible = ref(false);
const deleteTarget = ref<DocInfo | null>(null);

const configDialogVisible = ref(false);

const message = ref('');
const messageType = ref<'success' | 'error'>('success');
const messageVisible = ref(false);

function showMessage(text: string, type: 'success' | 'error' = 'success') {
  message.value = text;
  messageType.value = type;
  messageVisible.value = true;
  setTimeout(() => { messageVisible.value = false; }, 3000);
}

function formatFileSize(bytes: number): string {
  if (!bytes) return '-';
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

function formatTime(iso: string): string {
  if (!iso) return '-';
  try {
    const d = new Date(iso);
    return d.toLocaleString('zh-CN');
  } catch {
    return iso;
  }
}

function getFileIcon(fileType: string): string {
  if (!fileType) return '📄';
  if (fileType.includes('pdf')) return '📕';
  if (fileType.includes('txt')) return '📝';
  if (fileType.includes('md')) return '📋';
  if (fileType.includes('doc')) return '📘';
  if (fileType.includes('xls') || fileType.includes('csv')) return '📊';
  return '📄';
}

async function loadDocuments() {
  loading.value = true;
  try {
    const resp = await axios.get(`${VITE_API_URL}/api/docs/list`);
    documents.value = resp.data.documents || [];
  } catch (err: any) {
    showMessage('加载文档列表失败: ' + (err.response?.data?.detail || err.message), 'error');
  } finally {
    loading.value = false;
  }
}

async function loadChunkConfig() {
  try {
    const resp = await axios.get(`${VITE_API_URL}/api/docs/config/chunk`);
    chunkConfig.chunk_size = resp.data.chunk_size;
    chunkConfig.chunk_overlap = resp.data.chunk_overlap;
    uploadChunkConfig.chunk_size = resp.data.chunk_size;
    uploadChunkConfig.chunk_overlap = resp.data.chunk_overlap;
  } catch (err: any) {
    console.error('加载分块配置失败:', err);
  }
}

function handleFileSelect(e: Event) {
  const input = e.target as HTMLInputElement;
  if (input.files) {
    selectedFiles.value = Array.from(input.files);
  }
}

function removeSelectedFile(index: number) {
  selectedFiles.value.splice(index, 1);
}

async function handleUpload() {
  if (selectedFiles.value.length === 0) {
    showMessage('请先选择文件', 'error');
    return;
  }
  uploadLoading.value = true;
  try {
    const formData = new FormData();
    selectedFiles.value.forEach(f => formData.append('files', f));
    if (useCustomChunk.value) {
      formData.append('chunk_size', String(uploadChunkConfig.chunk_size));
      formData.append('chunk_overlap', String(uploadChunkConfig.chunk_overlap));
    }
    const resp = await axios.post(`${VITE_API_URL}/api/docs/upload`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 300000,
    });
    showMessage(resp.data.message || '上传成功');
    selectedFiles.value = [];
    await loadDocuments();
  } catch (err: any) {
    showMessage('上传失败: ' + (err.response?.data?.detail || err.message), 'error');
  } finally {
    uploadLoading.value = false;
  }
}

async function viewChunks(doc: DocInfo) {
  chunkDialogTitle.value = doc.file_name;
  chunksPage.value = 1;
  await loadChunks(doc.doc_id);
  chunkDialogVisible.value = true;
}

async function loadChunks(docId: string) {
  chunksLoading.value = true;
  try {
    const resp = await axios.get(`${VITE_API_URL}/api/docs/chunks/${encodeURIComponent(docId)}`, {
      params: { page: chunksPage.value, page_size: chunksPageSize.value },
    });
    chunks.value = resp.data.chunks || [];
    chunksTotal.value = resp.data.total || 0;
  } catch (err: any) {
    showMessage('加载分块失败: ' + (err.response?.data?.detail || err.message), 'error');
  } finally {
    chunksLoading.value = false;
  }
}

const chunksTotalPages = computed(() => Math.ceil(chunksTotal.value / chunksPageSize.value));

function handleChunksPageChange(newPage: number, docId: string) {
  chunksPage.value = newPage;
  loadChunks(docId);
}

function confirmDelete(doc: DocInfo) {
  deleteTarget.value = doc;
  deleteDialogVisible.value = true;
}

async function doDelete() {
  if (!deleteTarget.value) return;
  try {
    const resp = await axios.delete(`${VITE_API_URL}/api/docs/documents/${encodeURIComponent(deleteTarget.value.doc_id)}`);
    showMessage(resp.data.message || '删除成功');
    await loadDocuments();
  } catch (err: any) {
    showMessage('删除失败: ' + (err.response?.data?.detail || err.message), 'error');
  } finally {
    deleteDialogVisible.value = false;
    deleteTarget.value = null;
  }
}

async function saveChunkConfig() {
  try {
    const resp = await axios.put(`${VITE_API_URL}/api/docs/config/chunk`, {
      chunk_size: chunkConfig.chunk_size,
      chunk_overlap: chunkConfig.chunk_overlap,
    });
    chunkConfig.chunk_size = resp.data.chunk_size;
    chunkConfig.chunk_overlap = resp.data.chunk_overlap;
    uploadChunkConfig.chunk_size = resp.data.chunk_size;
    uploadChunkConfig.chunk_overlap = resp.data.chunk_overlap;
    showMessage('分块配置已更新');
    configDialogVisible.value = false;
  } catch (err: any) {
    showMessage('保存失败: ' + (err.response?.data?.detail || err.message), 'error');
  }
}

onMounted(() => {
  loadDocuments();
  loadChunkConfig();
});
</script>

<template>
  <div class="doc-manage">
      <!-- 顶部标题栏 -->
      <header class="doc-manage__header">
        <div class="doc-manage__header-left">
          <h1 class="doc-manage__title">文档管理</h1>
          <span class="doc-manage__count">{{ documents.length }} 个文档</span>
        </div>
        <button class="doc-manage__config-btn" @click="configDialogVisible = true">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="3" />
            <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" />
          </svg>
          <span>分块配置</span>
        </button>
      </header>

      <!-- 上传区域 -->
      <section class="doc-manage__upload">
        <div class="doc-manage__upload-header">
          <h2>上传文档</h2>
          <label class="doc-manage__custom-toggle">
            <input type="checkbox" v-model="useCustomChunk" />
            <span>自定义分块参数</span>
          </label>
        </div>

        <div class="doc-manage__upload-body">
          <div class="doc-manage__file-drop" @click="($refs.fileInput as HTMLInputElement).click()">
            <input ref="fileInput" type="file" multiple accept=".txt,.md,.pdf,.doc,.docx,.csv" @change="handleFileSelect" style="display:none" />
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" opacity="0.5">
              <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M17 8l-5-5-5 5M12 3v12" />
            </svg>
            <p>点击选择文件或拖拽到此处</p>
            <span>支持 txt、md、pdf 等格式</span>
          </div>

          <!-- 已选文件列表 -->
          <div v-if="selectedFiles.length > 0" class="doc-manage__selected">
            <div v-for="(file, idx) in selectedFiles" :key="idx" class="doc-manage__selected-item">
              <span class="doc-manage__selected-name">{{ file.name }}</span>
              <span class="doc-manage__selected-size">{{ formatFileSize(file.size) }}</span>
              <button class="doc-manage__selected-remove" @click="removeSelectedFile(idx)">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M18 6L6 18M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>

          <!-- 自定义分块参数 -->
          <div v-if="useCustomChunk" class="doc-manage__chunk-params">
            <div class="doc-manage__param">
              <label>分块大小</label>
              <input type="number" v-model.number="uploadChunkConfig.chunk_size" min="50" max="4000" />
              <span class="doc-manage__param-hint">字符数 (50-4000)</span>
            </div>
            <div class="doc-manage__param">
              <label>重叠大小</label>
              <input type="number" v-model.number="uploadChunkConfig.chunk_overlap" min="0" :max="uploadChunkConfig.chunk_size - 1" />
              <span class="doc-manage__param-hint">字符数</span>
            </div>
          </div>

          <button
            class="doc-manage__upload-btn"
            :disabled="uploadLoading || selectedFiles.length === 0"
            @click="handleUpload"
          >
            <svg v-if="uploadLoading" class="doc-manage__spinner" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
            </svg>
            <span>{{ uploadLoading ? '上传中...' : '开始上传' }}</span>
          </button>
        </div>
      </section>

      <!-- 文档列表 -->
      <section class="doc-manage__list">
        <h2>文档列表</h2>
        <div v-if="loading" class="doc-manage__loading">
          <div class="doc-manage__loading-spinner"></div>
          <span>加载中...</span>
        </div>
        <div v-else-if="documents.length === 0" class="doc-manage__empty">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" opacity="0.3">
            <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
            <polyline points="14,2 14,8 20,8" />
          </svg>
          <p>暂无文档，请上传文件</p>
        </div>
        <div v-else class="doc-manage__table-wrapper">
          <table class="doc-manage__table">
            <thead>
              <tr>
                <th>文件名</th>
                <th>类型</th>
                <th>大小</th>
                <th>上传时间</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="doc in documents" :key="doc.doc_id">
                <td class="doc-manage__td-name">
                  <span class="doc-manage__file-icon">{{ getFileIcon(doc.file_type) }}</span>
                  <span>{{ doc.file_name }}</span>
                </td>
                <td>{{ doc.file_type || '-' }}</td>
                <td>{{ formatFileSize(doc.file_size) }}</td>
                <td>{{ formatTime(doc.upload_time) }}</td>
                <td class="doc-manage__td-actions">
                  <button class="doc-manage__action-btn doc-manage__action-btn--view" @click="viewChunks(doc)" title="查看分块">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                      <circle cx="12" cy="12" r="3" />
                    </svg>
                    <span>查看分块</span>
                  </button>
                  <button class="doc-manage__action-btn doc-manage__action-btn--delete" @click="confirmDelete(doc)" title="删除">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2" />
                    </svg>
                    <span>删除</span>
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <!-- 分块查看弹框 -->
      <Teleport to="body">
        <Transition name="dialog">
          <div v-if="chunkDialogVisible" class="doc-dialog-overlay" @click.self="chunkDialogVisible = false">
            <div class="doc-dialog doc-dialog--chunks">
              <div class="doc-dialog__header">
                <h3>分块详情 - {{ chunkDialogTitle }}</h3>
                <span class="doc-dialog__count">共 {{ chunksTotal }} 个分块</span>
                <button class="doc-dialog__close" @click="chunkDialogVisible = false">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M18 6L6 18M6 6l12 12" />
                  </svg>
                </button>
              </div>
              <div class="doc-dialog__body">
                <div v-if="chunksLoading" class="doc-manage__loading">
                  <div class="doc-manage__loading-spinner"></div>
                  <span>加载中...</span>
                </div>
                <div v-else-if="chunks.length === 0" class="doc-manage__empty">
                  <p>暂无分块数据</p>
                </div>
                <div v-else class="doc-manage__chunks-list">
                  <div v-for="(chunk, idx) in chunks" :key="chunk.chunk_id" class="doc-manage__chunk-card">
                    <div class="doc-manage__chunk-header">
                      <span class="doc-manage__chunk-index">#{{ (chunksPage - 1) * chunksPageSize + idx + 1 }}</span>
                      <span class="doc-manage__chunk-id">{{ chunk.chunk_id }}</span>
                    </div>
                    <div class="doc-manage__chunk-text">{{ chunk.text }}</div>
                    <div class="doc-manage__chunk-meta">
                      <span>类型: {{ chunk.metadata.content_type || 'text' }}</span>
                      <span>长度: {{ chunk.metadata.chunk_size || chunk.text.length }} 字符</span>
                    </div>
                  </div>
                </div>
              </div>
              <!-- 分页 -->
              <div v-if="chunksTotalPages > 1" class="doc-dialog__footer">
                <button
                  class="doc-dialog__page-btn"
                  :disabled="chunksPage <= 1"
                  @click="handleChunksPageChange(chunksPage - 1, chunks[0]?.metadata?.doc_id || '')"
                >上一页</button>
                <span class="doc-dialog__page-info">{{ chunksPage }} / {{ chunksTotalPages }}</span>
                <button
                  class="doc-dialog__page-btn"
                  :disabled="chunksPage >= chunksTotalPages"
                  @click="handleChunksPageChange(chunksPage + 1, chunks[0]?.metadata?.doc_id || '')"
                >下一页</button>
              </div>
            </div>
          </div>
        </Transition>
      </Teleport>

      <!-- 删除确认弹框 -->
      <Teleport to="body">
        <Transition name="dialog">
          <div v-if="deleteDialogVisible" class="doc-dialog-overlay" @click.self="deleteDialogVisible = false">
            <div class="doc-dialog doc-dialog--delete">
              <div class="doc-dialog__icon">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                  <circle cx="12" cy="12" r="10" />
                  <path d="M12 8v4M12 16h.01" />
                </svg>
              </div>
              <h3>确认删除</h3>
              <p>确定要删除文档「{{ deleteTarget?.file_name }}」吗？<br/>删除后将无法恢复。</p>
              <div class="doc-dialog__actions">
                <button class="doc-dialog__btn doc-dialog__btn--cancel" @click="deleteDialogVisible = false">取消</button>
                <button class="doc-dialog__btn doc-dialog__btn--confirm" @click="doDelete">确认删除</button>
              </div>
            </div>
          </div>
        </Transition>
      </Teleport>

      <!-- 分块配置弹框 -->
      <Teleport to="body">
        <Transition name="dialog">
          <div v-if="configDialogVisible" class="doc-dialog-overlay" @click.self="configDialogVisible = false">
            <div class="doc-dialog doc-dialog--config">
              <div class="doc-dialog__header">
                <h3>全局分块配置</h3>
                <button class="doc-dialog__close" @click="configDialogVisible = false">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M18 6L6 18M6 6l12 12" />
                  </svg>
                </button>
              </div>
              <div class="doc-dialog__body">
                <p class="doc-dialog__hint">修改后对新上传的文档生效</p>
                <div class="doc-manage__form-group">
                  <label>分块大小 (chunk_size)</label>
                  <input type="number" v-model.number="chunkConfig.chunk_size" min="50" max="4000" />
                  <span class="doc-manage__param-hint">默认 512，范围 50-4000 字符</span>
                </div>
                <div class="doc-manage__form-group">
                  <label>重叠大小 (chunk_overlap)</label>
                  <input type="number" v-model.number="chunkConfig.chunk_overlap" min="0" :max="chunkConfig.chunk_size - 1" />
                  <span class="doc-manage__param-hint">默认 50，需小于分块大小</span>
                </div>
              </div>
              <div class="doc-dialog__footer">
                <button class="doc-dialog__btn doc-dialog__btn--cancel" @click="configDialogVisible = false">取消</button>
                <button class="doc-dialog__btn doc-dialog__btn--confirm" @click="saveChunkConfig">保存</button>
              </div>
            </div>
          </div>
        </Transition>
      </Teleport>

      <!-- 消息提示 -->
      <Transition name="msg">
        <div v-if="messageVisible" class="doc-manage__message" :class="`doc-manage__message--${messageType}`">
          {{ message }}
        </div>
      </Transition>
    </div>
</template>

<style scoped>
.doc-manage {
  max-width: 1100px;
}

.doc-manage__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-6);
}

.doc-manage__header-left {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.doc-manage__back {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-md);
  color: var(--color-text-secondary);
  transition: all var(--transition-fast);
}

.doc-manage__back:hover {
  background-color: var(--color-bg-secondary);
  color: var(--color-text);
}

.doc-manage__title {
  font-size: var(--text-2xl);
  font-weight: var(--font-semibold);
  color: var(--color-text);
}

.doc-manage__count {
  font-size: var(--text-sm);
  color: var(--color-text-tertiary);
  background: var(--color-bg-secondary);
  padding: var(--space-1) var(--space-3);
  border-radius: var(--radius-full);
}

.doc-manage__config-btn {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-4);
  background-color: var(--color-bg-secondary);
  color: var(--color-text-secondary);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  transition: all var(--transition-fast);
}

.doc-manage__config-btn:hover {
  background-color: var(--color-bg-tertiary);
  color: var(--color-text);
}

/* 上传区域 */
.doc-manage__upload {
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-6);
  margin-bottom: var(--space-6);
}

.doc-manage__upload-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-4);
}

.doc-manage__upload-header h2 {
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
}

.doc-manage__custom-toggle {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  cursor: pointer;
}

.doc-manage__custom-toggle input {
  accent-color: var(--color-accent);
}

.doc-manage__upload-body {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.doc-manage__file-drop {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  padding: var(--space-8) var(--space-4);
  border: 2px dashed var(--color-border);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--transition-fast);
  color: var(--color-text-tertiary);
}

.doc-manage__file-drop:hover {
  border-color: var(--color-accent);
  background-color: var(--color-accent-subtle);
}

.doc-manage__file-drop p {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
}

.doc-manage__file-drop span {
  font-size: var(--text-xs);
}

.doc-manage__selected {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.doc-manage__selected-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2) var(--space-3);
  background: var(--color-bg-secondary);
  border-radius: var(--radius-sm);
}

.doc-manage__selected-name {
  flex: 1;
  font-size: var(--text-sm);
  color: var(--color-text);
}

.doc-manage__selected-size {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
}

.doc-manage__selected-remove {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-sm);
  color: var(--color-text-tertiary);
  transition: all var(--transition-fast);
}

.doc-manage__selected-remove:hover {
  background: var(--color-error);
  color: white;
}

.doc-manage__chunk-params {
  display: flex;
  gap: var(--space-4);
}

.doc-manage__param {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.doc-manage__param label {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--color-text-secondary);
}

.doc-manage__param input {
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  font-size: var(--text-sm);
  color: var(--color-text);
  background: var(--color-bg);
  outline: none;
  transition: border-color var(--transition-fast);
}

.doc-manage__param input:focus {
  border-color: var(--color-accent);
}

.doc-manage__param-hint {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
}

.doc-manage__upload-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-6);
  background-color: var(--color-accent);
  color: white;
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  transition: all var(--transition-fast);
  align-self: flex-end;
}

.doc-manage__upload-btn:hover:not(:disabled) {
  background-color: var(--color-accent-dark);
  transform: translateY(-1px);
}

.doc-manage__upload-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.doc-manage__spinner {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* 文档列表 */
.doc-manage__list {
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-6);
}

.doc-manage__list h2 {
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  margin-bottom: var(--space-4);
}

.doc-manage__loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-3);
  padding: var(--space-12);
  color: var(--color-text-tertiary);
}

.doc-manage__loading-spinner {
  width: 24px;
  height: 24px;
  border: 3px solid var(--color-border);
  border-top-color: var(--color-accent);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.doc-manage__empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-12);
  color: var(--color-text-tertiary);
}

.doc-manage__empty p {
  font-size: var(--text-sm);
}

.doc-manage__table-wrapper {
  overflow-x: auto;
}

.doc-manage__table {
  width: 100%;
  border-collapse: collapse;
}

.doc-manage__table th {
  text-align: left;
  padding: var(--space-3) var(--space-4);
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  color: var(--color-text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  border-bottom: 1px solid var(--color-border);
}

.doc-manage__table td {
  padding: var(--space-3) var(--space-4);
  font-size: var(--text-sm);
  color: var(--color-text);
  border-bottom: 1px solid var(--color-border);
}

.doc-manage__table tr:last-child td {
  border-bottom: none;
}

.doc-manage__table tr:hover td {
  background-color: var(--color-bg-secondary);
}

.doc-manage__td-name {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-weight: var(--font-medium);
}

.doc-manage__file-icon {
  font-size: var(--text-lg);
}

.doc-manage__td-actions {
  display: flex;
  gap: var(--space-2);
}

.doc-manage__action-btn {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-1) var(--space-3);
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  transition: all var(--transition-fast);
}

.doc-manage__action-btn--view {
  color: var(--color-accent);
  background: var(--color-accent-subtle);
}

.doc-manage__action-btn--view:hover {
  background: var(--color-accent);
  color: white;
}

.doc-manage__action-btn--delete {
  color: var(--color-error);
  background: rgba(239, 68, 68, 0.08);
}

.doc-manage__action-btn--delete:hover {
  background: var(--color-error);
  color: white;
}

/* 分块卡片 */
.doc-manage__chunks-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  max-height: 60vh;
  overflow-y: auto;
  padding: var(--space-2);
}

.doc-manage__chunk-card {
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--space-4);
}

.doc-manage__chunk-header {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-bottom: var(--space-2);
}

.doc-manage__chunk-index {
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  color: var(--color-accent);
  background: var(--color-accent-subtle);
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-sm);
}

.doc-manage__chunk-id {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  font-family: var(--font-mono);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.doc-manage__chunk-text {
  font-size: var(--text-sm);
  color: var(--color-text);
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-word;
  margin-bottom: var(--space-2);
  max-height: 200px;
  overflow-y: auto;
}

.doc-manage__chunk-meta {
  display: flex;
  gap: var(--space-4);
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
}

/* 弹框 */
.doc-dialog-overlay {
  position: fixed;
  inset: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(4px);
}

.doc-dialog {
  background-color: var(--color-bg-elevated);
  border-radius: var(--radius-xl);
  max-width: 500px;
  width: 90%;
  box-shadow: var(--shadow-xl);
}

.doc-dialog--chunks {
  max-width: 700px;
  max-height: 85vh;
  display: flex;
  flex-direction: column;
}

.doc-dialog__header {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-5) var(--space-6);
  border-bottom: 1px solid var(--color-border);
}

.doc-dialog__header h3 {
  flex: 1;
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
}

.doc-dialog__count {
  font-size: var(--text-sm);
  color: var(--color-text-tertiary);
}

.doc-dialog__close {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-sm);
  color: var(--color-text-tertiary);
  transition: all var(--transition-fast);
}

.doc-dialog__close:hover {
  background: var(--color-bg-secondary);
  color: var(--color-text);
}

.doc-dialog__body {
  padding: var(--space-5) var(--space-6);
  overflow-y: auto;
  flex: 1;
}

.doc-dialog__hint {
  font-size: var(--text-sm);
  color: var(--color-text-tertiary);
  margin-bottom: var(--space-4);
}

.doc-manage__form-group {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  margin-bottom: var(--space-4);
}

.doc-manage__form-group label {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--color-text-secondary);
}

.doc-manage__form-group input {
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  font-size: var(--text-sm);
  color: var(--color-text);
  background: var(--color-bg);
  outline: none;
  transition: border-color var(--transition-fast);
}

.doc-manage__form-group input:focus {
  border-color: var(--color-accent);
}

.doc-dialog__footer {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-3);
  padding: var(--space-4) var(--space-6);
  border-top: 1px solid var(--color-border);
}

.doc-dialog__page-info {
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
}

.doc-dialog__page-btn {
  padding: var(--space-2) var(--space-4);
  background: var(--color-bg-secondary);
  color: var(--color-text);
  border-radius: var(--radius-sm);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  transition: all var(--transition-fast);
}

.doc-dialog__page-btn:hover:not(:disabled) {
  background: var(--color-bg-tertiary);
}

.doc-dialog__page-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* 删除弹框 */
.doc-dialog--delete {
  padding: var(--space-8);
  text-align: center;
  max-width: 400px;
}

.doc-dialog__icon {
  display: flex;
  justify-content: center;
  margin-bottom: var(--space-4);
  color: var(--color-warning);
}

.doc-dialog--delete h3 {
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  margin-bottom: var(--space-2);
}

.doc-dialog--delete p {
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  line-height: 1.6;
  margin-bottom: var(--space-6);
}

.doc-dialog__actions {
  display: flex;
  gap: var(--space-3);
  justify-content: center;
}

.doc-dialog__btn {
  padding: var(--space-2) var(--space-6);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  transition: all var(--transition-fast);
  min-width: 100px;
}

.doc-dialog__btn--cancel {
  background-color: var(--color-bg-secondary);
  color: var(--color-text);
}

.doc-dialog__btn--cancel:hover {
  background-color: var(--color-bg-tertiary);
}

.doc-dialog__btn--confirm {
  background-color: var(--color-accent);
  color: white;
}

.doc-dialog__btn--confirm:hover {
  background-color: var(--color-accent-dark);
  transform: translateY(-1px);
}

/* 消息提示 */
.doc-manage__message {
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

.doc-manage__message--success {
  background: var(--color-success);
  color: white;
}

.doc-manage__message--error {
  background: var(--color-error);
  color: white;
}

/* 弹框动画 */
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

.dialog-enter-from .doc-dialog {
  transform: scale(0.95) translateY(10px);
  opacity: 0;
}

.dialog-enter-active .doc-dialog {
  transition: all 0.3s ease-out;
}

.dialog-leave-active .doc-dialog {
  transition: all 0.2s ease-in;
}

.dialog-leave-to .doc-dialog {
  transform: scale(0.95) translateY(10px);
  opacity: 0;
}

/* 消息动画 */
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
  .doc-manage {
    padding: var(--space-4);
  }

  .doc-manage__chunk-params {
    flex-direction: column;
  }

  .doc-manage__table th:nth-child(3),
  .doc-manage__table td:nth-child(3),
  .doc-manage__table th:nth-child(4),
  .doc-manage__table td:nth-child(4) {
    display: none;
  }
}
</style>
