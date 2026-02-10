/**
 * Composable for formatting dates and numbers consistently.
 */
export function useFormatters() {
  function formatDate(iso: string | null | undefined): string {
    if (!iso) return '—'
    return new Date(iso).toLocaleString()
  }

  function formatRelativeTime(iso: string | null | undefined): string {
    if (!iso) return '—'
    const diff = Date.now() - new Date(iso).getTime()
    const seconds = Math.floor(diff / 1000)
    if (seconds < 60) return `${seconds}s ago`
    const minutes = Math.floor(seconds / 60)
    if (minutes < 60) return `${minutes}m ago`
    const hours = Math.floor(minutes / 60)
    if (hours < 24) return `${hours}h ago`
    return formatDate(iso)
  }

  function formatNumber(value: number | string | null | undefined, decimals = 2): string {
    if (value == null) return '—'
    const num = typeof value === 'string' ? parseFloat(value) : value
    return isNaN(num) ? '—' : num.toFixed(decimals)
  }

  return { formatDate, formatRelativeTime, formatNumber }
}
