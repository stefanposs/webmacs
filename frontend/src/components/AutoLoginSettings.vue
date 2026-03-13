<template>
  <Card>
    <template #title>
      <div class="flex items-center gap-2">
        <i class="pi pi-sign-in text-xl"></i>
        Auto-Login Settings
      </div>
    </template>

    <template #content>
      <div class="flex flex-col gap-4">
        <!-- Enable/Disable Toggle -->
        <div class="flex items-center justify-between">
          <label for="auto-login-toggle" class="font-medium">
            Enable Auto-Login
          </label>
          <ToggleButton
            id="auto-login-toggle"
            v-model="config.enabled"
            onLabel="Enabled"
            offLabel="Disabled"
            @change="handleConfigChange"
          />
        </div>

        <!-- Email Field -->
        <div class="flex flex-col gap-2">
          <label for="auto-email" class="font-medium">Email</label>
          <InputText
            id="auto-email"
            v-model="config.email"
            :disabled="!config.enabled"
            placeholder="admin@webmacs.local"
            @input="handleConfigChange"
          />
        </div>

        <!-- Password Field -->
        <div class="flex flex-col gap-2">
          <label for="auto-password" class="font-medium">Password</label>
          <Password
            id="auto-password"
            v-model="tempPassword"
            :disabled="!config.enabled"
            placeholder="Enter password for auto-login"
            :feedback="false"
            toggle-mask
            @input="handlePasswordChange"
          />
          <small class="text-gray-500">
            Password is stored securely in session storage
          </small>
        </div>

        <!-- Remember Me -->
        <div class="flex items-center gap-2">
          <Checkbox
            id="remember-me"
            v-model="config.rememberMe"
            :disabled="!config.enabled"
            binary
            @change="handleConfigChange"
          />
          <label for="remember-me" class="font-medium">
            Remember credentials across browser sessions
          </label>
        </div>

        <!-- Advanced Settings -->
        <Accordion>
          <AccordionTab header="Advanced Settings">
            <div class="flex flex-col gap-4">
              <!-- Retry Attempts -->
              <div class="flex flex-col gap-2">
                <label for="retry-attempts" class="font-medium">
                  Retry Attempts
                </label>
                <InputNumber
                  id="retry-attempts"
                  v-model="config.retryAttempts"
                  :disabled="!config.enabled"
                  :min="1"
                  :max="10"
                  @input="handleConfigChange"
                />
              </div>

              <!-- Retry Delay -->
              <div class="flex flex-col gap-2">
                <label for="retry-delay" class="font-medium">
                  Retry Delay (ms)
                </label>
                <InputNumber
                  id="retry-delay"
                  v-model="config.retryDelay"
                  :disabled="!config.enabled"
                  :min="1000"
                  :max="10000"
                  :step="500"
                  @input="handleConfigChange"
                />
              </div>
            </div>
          </AccordionTab>
        </Accordion>

        <!-- Status Display -->
        <div class="p-3 border rounded-md bg-gray-50 dark:bg-gray-800">
          <div class="flex items-center gap-2 mb-2">
            <i class="pi pi-info-circle"></i>
            <span class="font-medium">Auto-Login Status</span>
          </div>
          
          <div class="text-sm space-y-1">
            <div>
              Status: 
              <Badge
                :value="autoLogin.isAutoLoggingIn.value ? 'Logging In...' : 
                       config.enabled ? 'Enabled' : 'Disabled'"
                :severity="autoLogin.isAutoLoggingIn.value ? 'info' : 
                          config.enabled ? 'success' : 'secondary'"
              />
            </div>
            <div>
              Attempts: {{ autoLogin.autoLoginAttempts.value }} / {{ autoLogin.maxRetries.value }}
            </div>
          </div>
        </div>

        <!-- Action Buttons -->
        <div class="flex gap-2">
          <Button
            label="Test Auto-Login"
            icon="pi pi-play"
            :disabled="!config.enabled || !config.email || !tempPassword || autoLogin.isAutoLoggingIn.value"
            @click="testAutoLogin"
          />
          
          <Button
            label="Reset Settings"
            icon="pi pi-refresh"
            severity="secondary"
            @click="resetSettings"
          />
        </div>
      </div>
    </template>
  </Card>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useAutoLogin } from '@/composables/useAutoLogin'
import { useNotification } from '@/composables/useNotification'
import type { AutoLoginConfig } from '@/composables/useAutoLogin'

import Card from 'primevue/card'
import ToggleButton from 'primevue/togglebutton'
import InputText from 'primevue/inputtext'
import Password from 'primevue/password'
import Checkbox from 'primevue/checkbox'
import InputNumber from 'primevue/inputnumber'
import Accordion from 'primevue/accordion'
import AccordionTab from 'primevue/accordiontab'
import Badge from 'primevue/badge'
import Button from 'primevue/button'

const autoLogin = useAutoLogin()
const { success: showSuccess, error: showError } = useNotification()

const config = ref<AutoLoginConfig>({
  enabled: false,
  email: '',
  rememberMe: true,
  retryAttempts: 3,
  retryDelay: 2000
})

const tempPassword = ref('')

// Load configuration on mount
onMounted(() => {
  config.value = autoLogin.loadAutoLoginConfig()
  const stored = autoLogin.getStoredCredentials()
  if (stored?.password) {
    tempPassword.value = stored.password
  }
})

// Handle configuration changes
const handleConfigChange = () => {
  autoLogin.saveAutoLoginConfig(config.value)
  
  if (config.value.enabled && config.value.email && tempPassword.value) {
    autoLogin.enableAutoLogin(
      config.value.email, 
      tempPassword.value, 
      config.value.rememberMe
    )
  } else if (!config.value.enabled) {
    autoLogin.disableAutoLogin()
  }
}

// Handle password changes
const handlePasswordChange = () => {
  if (config.value.enabled && config.value.email && tempPassword.value) {
    autoLogin.enableAutoLogin(
      config.value.email, 
      tempPassword.value, 
      config.value.rememberMe
    )
  }
}

// Test auto-login functionality
const testAutoLogin = async () => {
  if (!config.value.email || !tempPassword.value) {
    showError('Please enter email and password')
    return
  }

  try {
    const success = await autoLogin.performAutoLogin({
      email: config.value.email,
      password: tempPassword.value
    })
    
    if (success) {
      showSuccess('Auto-login test successful')
    } else {
      showError('Auto-login test failed')
    }
  } catch (error) {
    showError('Auto-login test failed: ' + (error as Error).message)
  }
}

// Reset all settings
const resetSettings = () => {
  config.value = {
    enabled: false,
    email: '',
    rememberMe: true,
    retryAttempts: 3,
    retryDelay: 2000
  }
  tempPassword.value = ''
  autoLogin.disableAutoLogin()
  showSuccess('Auto-login settings reset')
}
</script>
