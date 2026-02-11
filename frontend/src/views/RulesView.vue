<template>
  <div class="view-rules">
    <div class="view-header">
      <h2>Rules</h2>
      <button class="btn-primary" @click="showCreateDialog = true">
        <i class="pi pi-plus" /> New Rule
      </button>
    </div>

    <div v-if="ruleStore.loading" class="loading"><i class="pi pi-spin pi-spinner" /> Loading rules...</div>

    <table v-else-if="ruleStore.rules.length" class="data-table">
      <thead>
        <tr>
          <th>Name</th>
          <th>Event</th>
          <th>Operator</th>
          <th>Threshold</th>
          <th>Action</th>
          <th>Active</th>
          <th>Cooldown</th>
          <th>Last Triggered</th>
          <th>Created</th>
          <th style="width: 110px">Actions</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="rule in ruleStore.rules" :key="rule.public_id">
          <td><strong>{{ rule.name }}</strong></td>
          <td class="mono">{{ eventNameMap[rule.event_public_id] ?? rule.event_public_id.slice(0, 8) + '…' }}</td>
          <td>{{ operatorLabels[rule.operator] }}</td>
          <td>
            <template v-if="rule.operator === 'between' || rule.operator === 'not_between'">
              {{ rule.threshold }} – {{ rule.threshold_high }}
            </template>
            <template v-else>{{ rule.threshold }}</template>
          </td>
          <td><span class="badge badge--info">{{ rule.action_type }}</span></td>
          <td>
            <span class="badge" :class="rule.enabled ? 'badge--sensor' : 'badge--error'">
              {{ rule.enabled ? 'Active' : 'Inactive' }}
            </span>
          </td>
          <td>{{ rule.cooldown_seconds }}s</td>
          <td>{{ formatDate(rule.last_triggered_at) }}</td>
          <td>{{ formatDate(rule.created_on) }}</td>
          <td>
            <button class="btn-icon" @click="openEdit(rule)" title="Edit">
              <i class="pi pi-pencil" />
            </button>
            <button class="btn-icon" @click="confirmDelete(rule)" title="Delete">
              <i class="pi pi-trash" />
            </button>
          </td>
        </tr>
      </tbody>
    </table>

    <div v-else class="empty-state">
      <i class="pi pi-bolt" />
      No rules defined yet. Create a rule to automate actions based on events.
    </div>

    <div class="pagination">
      <button class="btn-secondary" :disabled="page <= 1" @click="changePage(-1)">
        <i class="pi pi-chevron-left" /> Previous
      </button>
      <span>Page {{ page }}</span>
      <button class="btn-secondary" :disabled="page * 50 >= ruleStore.total" @click="changePage(1)">
        Next <i class="pi pi-chevron-right" />
      </button>
    </div>

    <!-- Create Dialog -->
    <div v-if="showCreateDialog" class="dialog-overlay" @click.self="showCreateDialog = false">
      <div class="dialog" style="max-width: 540px">
        <h3>Create Rule</h3>
        <form @submit.prevent="handleCreate">
          <div class="form-group">
            <label>Name</label>
            <input v-model="form.name" required placeholder="e.g. High Temperature Alert" />
          </div>
          <div class="form-group">
            <label>Event</label>
            <select v-model="form.event_public_id" required>
              <option value="" disabled>Select an event</option>
              <option v-for="ev in eventStore.events" :key="ev.public_id" :value="ev.public_id">
                {{ ev.name }}
              </option>
            </select>
          </div>
          <div style="display: flex; gap: 0.75rem">
            <div class="form-group" style="flex: 1">
              <label>Operator</label>
              <select v-model="form.operator" required>
                <option v-for="(label, key) in operatorLabels" :key="key" :value="key">{{ label }}</option>
              </select>
            </div>
            <div class="form-group" style="flex: 1">
              <label>Threshold</label>
              <input v-model.number="form.threshold" type="number" step="any" required />
            </div>
            <div v-if="form.operator === 'between' || form.operator === 'not_between'" class="form-group" style="flex: 1">
              <label>Threshold High</label>
              <input v-model.number="form.threshold_high" type="number" step="any" required />
            </div>
          </div>
          <div style="display: flex; gap: 0.75rem">
            <div class="form-group" style="flex: 1">
              <label>Action Type</label>
              <select v-model="form.action_type" required>
                <option value="webhook">webhook</option>
                <option value="log">log</option>
              </select>
            </div>
            <div class="form-group" style="flex: 1">
              <label>Cooldown (seconds)</label>
              <input v-model.number="form.cooldown_seconds" type="number" min="0" required />
            </div>
          </div>
          <div v-if="form.action_type === 'webhook'" class="form-group">
            <label>Webhook Event Type</label>
            <select v-model="form.webhook_event_type">
              <option value="">None</option>
              <option value="sensor.threshold_exceeded">sensor.threshold_exceeded</option>
              <option value="sensor.reading">sensor.reading</option>
              <option value="experiment.started">experiment.started</option>
              <option value="experiment.stopped">experiment.stopped</option>
              <option value="system.health_changed">system.health_changed</option>
            </select>
          </div>
          <div class="form-group">
            <label>Active</label>
            <select v-model="form.enabled">
              <option :value="true">Yes</option>
              <option :value="false">No</option>
            </select>
          </div>
          <div class="dialog-actions">
            <button type="button" class="btn-secondary" @click="showCreateDialog = false">Cancel</button>
            <button type="submit" class="btn-primary">Create</button>
          </div>
        </form>
      </div>
    </div>

    <!-- Edit Dialog -->
    <div v-if="showEditDialog" class="dialog-overlay" @click.self="showEditDialog = false">
      <div class="dialog" style="max-width: 540px">
        <h3>Edit Rule</h3>
        <form @submit.prevent="handleEdit">
          <div class="form-group">
            <label>Name</label>
            <input v-model="editForm.name" required />
          </div>
          <div class="form-group">
            <label>Event</label>
            <select v-model="editForm.event_public_id" required>
              <option value="" disabled>Select an event</option>
              <option v-for="ev in eventStore.events" :key="ev.public_id" :value="ev.public_id">
                {{ ev.name }}
              </option>
            </select>
          </div>
          <div style="display: flex; gap: 0.75rem">
            <div class="form-group" style="flex: 1">
              <label>Operator</label>
              <select v-model="editForm.operator" required>
                <option v-for="(label, key) in operatorLabels" :key="key" :value="key">{{ label }}</option>
              </select>
            </div>
            <div class="form-group" style="flex: 1">
              <label>Threshold</label>
              <input v-model.number="editForm.threshold" type="number" step="any" required />
            </div>
            <div v-if="editForm.operator === 'between' || editForm.operator === 'not_between'" class="form-group" style="flex: 1">
              <label>Threshold High</label>
              <input v-model.number="editForm.threshold_high" type="number" step="any" required />
            </div>
          </div>
          <div style="display: flex; gap: 0.75rem">
            <div class="form-group" style="flex: 1">
              <label>Action Type</label>
              <select v-model="editForm.action_type" required>
                <option value="webhook">webhook</option>
                <option value="log">log</option>
              </select>
            </div>
            <div class="form-group" style="flex: 1">
              <label>Cooldown (seconds)</label>
              <input v-model.number="editForm.cooldown_seconds" type="number" min="0" required />
            </div>
          </div>
          <div v-if="editForm.action_type === 'webhook'" class="form-group">
            <label>Webhook Event Type</label>
            <select v-model="editForm.webhook_event_type">
              <option value="">None</option>
              <option value="sensor.threshold_exceeded">sensor.threshold_exceeded</option>
              <option value="sensor.reading">sensor.reading</option>
              <option value="experiment.started">experiment.started</option>
              <option value="experiment.stopped">experiment.stopped</option>
              <option value="system.health_changed">system.health_changed</option>
            </select>
          </div>
          <div class="form-group">
            <label>Active</label>
            <select v-model="editForm.enabled">
              <option :value="true">Yes</option>
              <option :value="false">No</option>
            </select>
          </div>
          <div class="dialog-actions">
            <button type="button" class="btn-secondary" @click="showEditDialog = false">Cancel</button>
            <button type="submit" class="btn-primary">Save</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, reactive, computed } from 'vue'
import { useRuleStore } from '@/stores/rules'
import { useEventStore } from '@/stores/events'
import { useNotification } from '@/composables/useNotification'
import { useFormatters } from '@/composables/useFormatters'
import type { Rule, RuleOperator, RuleActionType } from '@/types'

const ruleStore = useRuleStore()
const eventStore = useEventStore()
const { success, error } = useNotification()
const { formatDate } = useFormatters()

const showCreateDialog = ref(false)
const showEditDialog = ref(false)
const editingRule = ref<Rule | null>(null)
const page = ref(1)

const operatorLabels: Record<RuleOperator, string> = {
  gt: '>',
  lt: '<',
  gte: '>=',
  lte: '<=',
  eq: '==',
  between: 'between',
  not_between: 'not between',
}

const eventNameMap = computed(() => {
  const map: Record<string, string> = {}
  for (const ev of eventStore.events) {
    map[ev.public_id] = ev.name
  }
  return map
})

const form = reactive({
  name: '',
  event_public_id: '',
  operator: 'gt' as RuleOperator,
  threshold: 0,
  threshold_high: 0 as number | null,
  action_type: 'log' as RuleActionType,
  webhook_event_type: '' as string | null,
  cooldown_seconds: 60,
  enabled: true,
})

const editForm = reactive({
  name: '',
  event_public_id: '',
  operator: 'gt' as RuleOperator,
  threshold: 0,
  threshold_high: 0 as number | null,
  action_type: 'log' as RuleActionType,
  webhook_event_type: '' as string | null,
  cooldown_seconds: 60,
  enabled: true,
})

function resetForm() {
  Object.assign(form, {
    name: '',
    event_public_id: '',
    operator: 'gt',
    threshold: 0,
    threshold_high: 0,
    action_type: 'log',
    webhook_event_type: '',
    cooldown_seconds: 60,
    enabled: true,
  })
}

function changePage(delta: number) {
  page.value += delta
  ruleStore.fetchRules(page.value)
}

async function handleCreate() {
  try {
    await ruleStore.createRule({
      name: form.name,
      event_public_id: form.event_public_id,
      operator: form.operator,
      threshold: form.threshold,
      threshold_high: form.operator === 'between' || form.operator === 'not_between' ? form.threshold_high : null,
      action_type: form.action_type,
      webhook_event_type: form.webhook_event_type || null,
      cooldown_seconds: form.cooldown_seconds,
      enabled: form.enabled,
    })
    success('Rule created', `"${form.name}" was added successfully.`)
    showCreateDialog.value = false
    resetForm()
  } catch (err: unknown) {
    error('Failed to create rule', (err as Error).message)
  }
}

function openEdit(rule: Rule) {
  editingRule.value = rule
  Object.assign(editForm, {
    name: rule.name,
    event_public_id: rule.event_public_id,
    operator: rule.operator,
    threshold: rule.threshold,
    threshold_high: rule.threshold_high ?? 0,
    action_type: rule.action_type,
    webhook_event_type: rule.webhook_event_type ?? '',
    cooldown_seconds: rule.cooldown_seconds,
    enabled: rule.enabled,
  })
  showEditDialog.value = true
}

async function handleEdit() {
  if (!editingRule.value) return
  try {
    await ruleStore.updateRule(editingRule.value.public_id, {
      name: editForm.name,
      event_public_id: editForm.event_public_id,
      operator: editForm.operator,
      threshold: editForm.threshold,
      threshold_high: editForm.operator === 'between' || editForm.operator === 'not_between' ? editForm.threshold_high : null,
      action_type: editForm.action_type,
      webhook_event_type: editForm.webhook_event_type || null,
      cooldown_seconds: editForm.cooldown_seconds,
      enabled: editForm.enabled,
    })
    success('Rule updated', `"${editForm.name}" was saved.`)
    showEditDialog.value = false
    editingRule.value = null
  } catch (err: unknown) {
    error('Failed to update rule', (err as Error).message)
  }
}

async function confirmDelete(rule: Rule) {
  if (confirm(`Delete rule "${rule.name}"?`)) {
    try {
      await ruleStore.deleteRule(rule.public_id)
      success('Rule deleted', `"${rule.name}" was removed.`)
    } catch (err: unknown) {
      error('Failed to delete rule', (err as Error).message)
    }
  }
}

onMounted(() => {
  ruleStore.fetchRules(page.value)
  eventStore.fetchEvents()
})
</script>

<style lang="scss" scoped>
@import '@/assets/styles/views-shared';
</style>
