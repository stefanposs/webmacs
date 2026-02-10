<template>
  <div class="view-users">
    <div class="view-header">
      <h2>Users</h2>
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
          <td><span class="badge" :class="user.admin ? 'badge--admin' : ''">{{ user.admin ? 'Admin' : 'User' }}</span></td>
          <td>{{ formatDate(user.registered_on) }}</td>
          <td>
            <button class="btn-icon" @click="handleDelete(user)" title="Delete user">
              <i class="pi pi-trash" />
            </button>
          </td>
        </tr>
      </tbody>
    </table>

    <div v-else class="empty-state">
      <i class="pi pi-users" />
      No users found.
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import api from '@/services/api'
import { useNotification } from '@/composables/useNotification'
import { useFormatters } from '@/composables/useFormatters'
import type { User, PaginatedResponse } from '@/types'

const { success, error } = useNotification()
const { formatDate } = useFormatters()
const users = ref<User[]>([])
const loading = ref(false)

async function fetchUsers() {
  loading.value = true
  try {
    const { data } = await api.get<PaginatedResponse<User>>('/users/')
    users.value = data.data
  } finally {
    loading.value = false
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
