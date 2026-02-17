<template>
  <div class="view-users">
    <div class="view-header">
      <h2>Users</h2>
      <button class="btn-primary" @click="showCreateDialog = true">
        <i class="pi pi-plus" /> Add User
      </button>
    </div>

    <div v-if="loading" class="loading"><i class="pi pi-spin pi-spinner" /> Loading users...</div>

    <table v-else-if="users.length" class="data-table">
      <thead>
        <tr>
          <th>Username</th>
          <th>Email</th>
          <th>Role</th>
          <th>Registered</th>
          <th style="width: 80px">Actions</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="user in users" :key="user.public_id">
          <td><strong>{{ user.username }}</strong></td>
          <td>{{ user.email }}</td>
          <td><span class="badge" :class="roleBadgeClass(user.role)">{{ capitalize(user.role) }}</span></td>
          <td>{{ formatDate(user.registered_on) }}</td>
          <td>
            <button class="btn-icon" @click="handleDelete(user)" title="Delete user" aria-label="Delete user">
              <i class="pi pi-trash" />
            </button>
          </td>
        </tr>
      </tbody>
    </table>

    <div v-else class="empty-state">
      <i class="pi pi-users" />
      No users found. Add a user to get started.
    </div>

    <!-- Create User Dialog -->
    <div v-if="showCreateDialog" class="dialog-overlay" @click.self="showCreateDialog = false">
      <div class="dialog" style="max-width: 440px">
        <h3>Add User</h3>
        <form @submit.prevent="handleCreate">
          <div class="form-group">
            <label>Username</label>
            <input v-model="form.username" required minlength="2" placeholder="e.g. johndoe" />
          </div>
          <div class="form-group">
            <label>Email</label>
            <input v-model="form.email" type="email" required placeholder="e.g. john@example.com" />
          </div>
          <div class="form-group">
            <label>Password</label>
            <input v-model="form.password" type="password" required minlength="8" placeholder="Min. 8 characters" />
          </div>
          <div class="form-group">
            <label>Role</label>
            <select v-model="form.role">
              <option value="viewer">Viewer</option>
              <option value="operator">Operator</option>
              <option value="admin">Admin</option>
            </select>
          </div>
          <div v-if="createError" class="form-error">{{ createError }}</div>
          <div class="dialog-actions">
            <button type="button" class="btn-secondary" @click="closeCreateDialog">Cancel</button>
            <button type="submit" class="btn-primary" :disabled="creating">
              <i v-if="creating" class="pi pi-spin pi-spinner" />
              {{ creating ? 'Creating…' : 'Create User' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, reactive } from 'vue'
import api from '@/services/api'
import { useNotification } from '@/composables/useNotification'
import { useFormatters } from '@/composables/useFormatters'
import type { User, PaginatedResponse, UserRole } from '@/types'

const { success, error } = useNotification()
const { formatDate } = useFormatters()
const users = ref<User[]>([])
const loading = ref(false)
const showCreateDialog = ref(false)
const creating = ref(false)
const createError = ref('')

const form = reactive({
  username: '',
  email: '',
  password: '',
  role: 'viewer' as UserRole,
})

function roleBadgeClass(role: UserRole): string {
  if (role === 'admin') return 'badge--admin'
  if (role === 'operator') return 'badge--sensor'
  return ''
}

function capitalize(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1)
}

function resetForm() {
  form.username = ''
  form.email = ''
  form.password = ''
  form.role = 'viewer'
  createError.value = ''
}

function closeCreateDialog() {
  showCreateDialog.value = false
  resetForm()
}

async function fetchUsers() {
  loading.value = true
  try {
    const { data } = await api.get<PaginatedResponse<User>>('/users/')
    users.value = data.data
  } finally {
    loading.value = false
  }
}

async function handleCreate() {
  creating.value = true
  createError.value = ''
  try {
    await api.post('/users/', {
      username: form.username,
      email: form.email,
      password: form.password,
      role: form.role,
    })
    success('User created', `"${form.username}" was added successfully.`)
    closeCreateDialog()
    await fetchUsers()
  } catch (err: unknown) {
    const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      ?? (err as Error).message
    createError.value = msg
    error('Failed to create user', msg)
  } finally {
    creating.value = false
  }
}

async function handleDelete(user: User) {
  if (confirm(`Delete user "${user.username}"?`)) {
    try {
      await api.delete(`/users/${user.public_id}`)
      users.value = users.value.filter((u) => u.public_id !== user.public_id)
      success('User deleted', `"${user.username}" was removed.`)
    } catch (err: unknown) {
      error('Failed to delete user', (err as Error).message)
    }
  }
}

onMounted(fetchUsers)
</script>

<style lang="scss" scoped>
@import '@/assets/styles/views-shared';
</style>
