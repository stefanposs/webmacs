import { ref, watch, onUnmounted, type Ref } from 'vue'

/**
 * Animates a number value smoothly using requestAnimationFrame.
 * Returns a reactive `displayValue` that transitions toward `targetValue`.
 */
export function useAnimatedCounter(
  targetValue: Ref<number | null>,
  options: { duration?: number; decimals?: number } = {},
) {
  const duration = options.duration ?? 400
  const decimals = options.decimals ?? 2

  const displayValue = ref<string>('--')
  let animationId: number | null = null
  let startValue = 0
  let startTime: number | null = null

  function easeOutQuad(t: number): number {
    return t * (2 - t)
  }

  function animate(timestamp: number) {
    if (startTime === null) startTime = timestamp
    const elapsed = timestamp - startTime
    const progress = Math.min(elapsed / duration, 1)
    const eased = easeOutQuad(progress)
    const target = targetValue.value ?? 0
    const current = startValue + (target - startValue) * eased

    displayValue.value = current.toFixed(decimals)

    if (progress < 1) {
      animationId = requestAnimationFrame(animate)
    } else {
      displayValue.value = target.toFixed(decimals)
      animationId = null
    }
  }

  watch(
    targetValue,
    (newVal, oldVal) => {
      if (newVal === null) {
        displayValue.value = '--'
        return
      }
      if (animationId !== null) {
        cancelAnimationFrame(animationId)
      }
      startValue = oldVal ?? 0
      startTime = null
      animationId = requestAnimationFrame(animate)
    },
    { immediate: true },
  )

  onUnmounted(() => {
    if (animationId !== null) cancelAnimationFrame(animationId)
  })

  return { displayValue }
}
