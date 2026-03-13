import type { AutoLoginConfig } from '@/composables/useAutoLogin'

export interface LoginAttempt {
  timestamp: Date
  email: string
  success: boolean
  error?: string
  userAgent: string
  ipAddress?: string
}

export class AutoLoginService {
  private static readonly STORAGE_KEY = 'webmacs_login_attempts'
  private static readonly MAX_STORED_ATTEMPTS = 50

  // Log login attempt
  static logAttempt(attempt: Omit<LoginAttempt, 'timestamp' | 'userAgent'>): void {
    try {
      const attempts = this.getStoredAttempts()
      
      const newAttempt: LoginAttempt = {
        ...attempt,
        timestamp: new Date(),
        userAgent: navigator.userAgent
      }

      attempts.unshift(newAttempt)

      // Keep only the latest MAX_STORED_ATTEMPTS
      if (attempts.length > this.MAX_STORED_ATTEMPTS) {
        attempts.splice(this.MAX_STORED_ATTEMPTS)
      }

      localStorage.setItem(this.STORAGE_KEY, JSON.stringify(attempts))
    } catch (error) {
      console.warn('Failed to log login attempt:', error)
    }
  }

  // Get stored login attempts
  static getStoredAttempts(): LoginAttempt[] {
    try {
      const stored = localStorage.getItem(this.STORAGE_KEY)
      if (stored) {
        const parsed = JSON.parse(stored)
        return parsed.map((attempt: any) => ({
          ...attempt,
          timestamp: new Date(attempt.timestamp)
        }))
      }
    } catch (error) {
      console.warn('Failed to retrieve login attempts:', error)
    }
    return []
  }

  // Clear stored attempts
  static clearAttempts(): void {
    localStorage.removeItem(this.STORAGE_KEY)
  }

  // Get recent failed attempts for rate limiting
  static getRecentFailedAttempts(email: string, timeWindow = 15 * 60 * 1000): LoginAttempt[] {
    const attempts = this.getStoredAttempts()
    const cutoff = new Date(Date.now() - timeWindow)
    
    return attempts.filter(attempt => 
      attempt.email === email &&
      !attempt.success &&
      attempt.timestamp > cutoff
    )
  }

  // Check if account should be locked due to too many failed attempts
  static isAccountLocked(email: string, maxAttempts = 5, timeWindow = 15 * 60 * 1000): boolean {
    const recentFailures = this.getRecentFailedAttempts(email, timeWindow)
    return recentFailures.length >= maxAttempts
  }

  // Get time until account unlock
  static getUnlockTime(email: string, maxAttempts = 5, timeWindow = 15 * 60 * 1000): Date | null {
    if (!this.isAccountLocked(email, maxAttempts, timeWindow)) {
      return null
    }

    const recentFailures = this.getRecentFailedAttempts(email, timeWindow)
    if (recentFailures.length === 0) {
      return null
    }

    const oldestRelevantFailure = recentFailures[recentFailures.length - 1]
    return new Date(oldestRelevantFailure.timestamp.getTime() + timeWindow)
  }

  // Validate auto-login configuration
  static validateConfig(config: AutoLoginConfig): string[] {
    const errors: string[] = []

    if (!config.email || !config.email.includes('@')) {
      errors.push('Valid email address is required')
    }

    if (config.retryAttempts < 1 || config.retryAttempts > 10) {
      errors.push('Retry attempts must be between 1 and 10')
    }

    if (config.retryDelay < 1000 || config.retryDelay > 30000) {
      errors.push('Retry delay must be between 1 and 30 seconds')
    }

    return errors
  }

  // Generate secure auto-login token (for advanced scenarios)
  static async generateAutoLoginToken(email: string, password: string): Promise<string | null> {
    try {
      // Create a hash of email + password + timestamp for single-use tokens
      const data = `${email}:${password}:${Date.now()}`
      const encoder = new TextEncoder()
      const dataBuffer = encoder.encode(data)
      
      const hashBuffer = await crypto.subtle.digest('SHA-256', dataBuffer)
      const hashArray = Array.from(new Uint8Array(hashBuffer))
      const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('')
      
      return hashHex
    } catch (error) {
      console.error('Failed to generate auto-login token:', error)
      return null
    }
  }

  // Verify auto-login token
  static async verifyAutoLoginToken(
    email: string, 
    password: string, 
    token: string, 
    maxAge = 5 * 60 * 1000
  ): Promise<boolean> {
    try {
      // Extract timestamp from when token might have been created
      const now = Date.now()
      
      // Check multiple recent timestamps to account for slight timing differences
      for (let offset = 0; offset < maxAge; offset += 1000) {
        const testTimestamp = now - offset
        const testData = `${email}:${password}:${testTimestamp}`
        const encoder = new TextEncoder()
        const dataBuffer = encoder.encode(testData)
        
        const hashBuffer = await crypto.subtle.digest('SHA-256', dataBuffer)
        const hashArray = Array.from(new Uint8Array(hashBuffer))
        const testToken = hashArray.map(b => b.toString(16).padStart(2, '0')).join('')
        
        if (testToken === token) {
          return true
        }
      }
      
      return false
    } catch (error) {
      console.error('Failed to verify auto-login token:', error)
      return false
    }
  }
}
