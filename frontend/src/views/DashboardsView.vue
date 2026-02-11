<template>
  <div class="dashboards-view">
    <div class="view-header">
      <h1><i class="pi pi-th-large" /> Custom Dashboards</h1>
      <button class="btn-primary" @click="showCreate = true">
        <i class="pi pi-plus" /> New Dashboard
      </button>
    </div>

    <div v-if="store.loading" class="loading-state"><i class="pi pi-spin pi-spinner" /> Loading...</div>

    <div v-else-if="store.dashboards.length === 0" class="empty-state">
      <i class="pi pi-th-large" />
      <p>No custom dashboards yet. Create one to get started!</p>
    </div>

    <div v-else class="dashboard-grid">
      <div
        v-for="db in store.dashboards"
        :key="db.public_id"
        class="dashboard-card"
        @click="$router.push({ name: 'dashboard-custom', params: { id: db.public_id } })"
      >
        <div class="dashboard-card__header">
          <span class="dashboard-card__name">{{ db.name }}</span>
          <span v-if="db.is_global" class="badge badge--global">Global</span>
        </div>
        <div class="dashboard-card__meta">
          {{ db.widgets.length }} widget{{ db.widgets.length !== 1 ? 's' : '' }}
        </div>
        <div class="dashboard-card__actions" @click.stop>
          <button class="btn-icon" @click="confirmDelete(db.public_id)" title="Delete">
            <i class="pi pi-trash" />
          </button>
        </div>
      </div>
    </div>

    <!-- Create dialog -->
    <div v-if="showCreate" class="modal-overlay" @click.self="showCreate = false">
      <div class="modal">
        <h2>New Dashboard</h2>
        <form @submit.prevent="handleCreate">
          <label>Name</label>
          <input v-model="newName" type="text" placeholder="My Dashboard" required maxlength="255" />
          <label class="checkbox-label">
            <input v-model="newGlobal" type="checkbox" />
            Visible to all users
          </label>
          <div class="modal-actions">
            <button type="button" class="btn-secondary" @click="showCreate = false">Cancel</button>
            <button type="submit" class="btn-primary">Create</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useDashboardStore } from '@/stores/dashboards'

const store = useDashboardStore()
const router = useRouter()

const showCreate = ref(false)
const newName = ref('')
const newGlobal = ref(false)

async function handleCreate() {
  const db = await store.createDashboard({ name: newName.value, is_global: newGlobal.value })
  showCreate.value = false
  newName.value = ''
  newGlobal.value = false
  router.push({ name: 'dashboard-custom', params: { id: db.public_id } })
}

async function confirmDelete(publicId: string) {
  if (confirm('Delete this dashboard?')) {
    await store.deleteDashboard(publicId)
  }
}

onMounted(() => store.fetchDashboards())
</script>

<style scoped>
.dashboards-view { padding: 1.5rem; }
.view-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1.5rem;
}
.view-header h1 {
  font-size: 1.5rem;
  color: var(--wm-text, #e2e8f0);
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.dashboard-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 1rem;
}
.dashboard-card {
  background: var(--wm-surface, #1e293b);
  border: 1px solid var(--wm-border, #334155);
  border-radius: 12px;
  padding: 1rem;
  cursor: pointer;
  transition: border-color 0.2s;
  position: relative;
}
.dashboard-card:hover { border-color: #3b82f6; }
.dashboard-card__header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}
.dashboard-card__name { font-weight: 600; color: var(--wm-text, #e2e8f0); }
.badge { font-size: 0.7rem; padding: 2px 6px; border-radius: 4px; }
.badge--global { background: rgba(59,130,246,0.2); color: #60a5fa; }
.dashboard-card__meta { font-size: 0.8rem; color: var(--wm-text-muted, #94a3b8); }
.dashboard-card__actions { position: absolute; top: 0.75rem; right: 0.75rem; }

.loading-state, .empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  padding: 3rem;
  color: var(--wm-text-muted, #94a3b8);
}
.empty-state i { font-size: 2rem; }

.btn-primary {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  background: #3b82f6;
  color: #fff;
  border: none;
  border-radius: 8px;
  padding: 0.5rem 1rem;
  font-size: 0.85rem;
  cursor: pointer;
}
.btn-primary:hover { background: #2563eb; }
.btn-secondary {
  background: transparent;
  color: var(--wm-text-muted, #94a3b8);
  border: 1px solid var(--wm-border, #334155);
  border-radius: 8px;
  padding: 0.5rem 1rem;
  font-size: 0.85rem;
  cursor: pointer;
}
.btn-icon {
  background: none;
  border: none;
  color: var(--wm-text-muted, #94a3b8);
  cursor: pointer;
  padding: 4px;
}
.btn-icon:hover { color: #ef4444; }

.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 200;
}
.modal {
  background: var(--wm-surface, #1e293b);
  border: 1px solid var(--wm-border, #334155);
  border-radius: 12px;
  padding: 1.5rem;
  min-width: 340px;
}
.modal h2 { color: var(--wm-text, #e2e8f0); margin-bottom: 1rem; font-size: 1.1rem; }
.modal label { display: block; font-size: 0.85rem; color: var(--wm-text-muted, #94a3b8); margin-bottom: 0.3rem; }
.modal input[type="text"] {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid var(--wm-border, #334155);
  border-radius: 8px;
  background: var(--wm-bg, #0f172a);
  color: var(--wm-text, #e2e8f0);
  margin-bottom: 0.75rem;
}
.checkbox-label {
  display: flex !important;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 1rem;
}
.modal-actions { display: flex; justify-content: flex-end; gap: 0.5rem; }
</style>
