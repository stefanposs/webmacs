import api from '@/services/api'
import { LoggingType } from '@/types'

type AuditPayload = Record<string, unknown> | undefined

function stringifyDetails(details?: AuditPayload): string {
  if (!details || Object.keys(details).length === 0) return ''
  try {
    return ` | details=${JSON.stringify(details)}`
  } catch {
    return ''
  }
}

/**
 * Best-effort audit logging helper.
 * Fails silently to avoid breaking UX when logging endpoint is unavailable.
 */
export function useAuditLog() {
  async function logAction(
    action: string,
    details?: AuditPayload,
    loggingType: LoggingType = LoggingType.info,
  ): Promise<void> {
    const content = `[UI_ACTION] ${action}${stringifyDetails(details)}`
    try {
      await api.post('/logging', {
        content,
        logging_type: loggingType,
      })
    } catch {
      // best-effort: never block user flow due to audit logging failures
    }
  }

  return { logAction }
}