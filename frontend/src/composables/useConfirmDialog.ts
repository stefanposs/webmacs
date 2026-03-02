import { ref, readonly } from 'vue'

export interface ConfirmOptions {
  title: string
  message: string
  confirmLabel?: string
  cancelLabel?: string
  variant?: 'danger' | 'warning' | 'info'
  icon?: string
}

const visible = ref(false)
const options = ref<ConfirmOptions>({
  title: '',
  message: '',
})
let resolveFn: ((value: boolean) => void) | null = null

export function useConfirmDialog() {
  function confirm(opts: ConfirmOptions): Promise<boolean> {
    options.value = opts
    visible.value = true
    return new Promise<boolean>((resolve) => {
      resolveFn = resolve
    })
  }

  function handleConfirm() {
    visible.value = false
    resolveFn?.(true)
    resolveFn = null
  }

  function handleCancel() {
    visible.value = false
    resolveFn?.(false)
    resolveFn = null
  }

  return {
    visible: readonly(visible),
    options: readonly(options),
    confirm,
    handleConfirm,
    handleCancel,
  }
}
