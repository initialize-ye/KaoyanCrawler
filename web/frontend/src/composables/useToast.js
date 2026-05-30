import { ref, reactive } from 'vue'

const toasts = ref([])
let toastId = 0

/**
 * Toast通知组合式函数
 */
export function useToast() {
  const addToast = (options) => {
    const id = ++toastId
    const toast = {
      id,
      type: options.type || 'info', // success, error, warning, info
      title: options.title || '',
      message: options.message || '',
      duration: options.duration || 3000,
      closable: options.closable !== false,
      icon: options.icon || null,
    }

    toasts.value.push(toast)

    // 自动关闭
    if (toast.duration > 0) {
      setTimeout(() => {
        removeToast(id)
      }, toast.duration)
    }

    return id
  }

  const removeToast = (id) => {
    const index = toasts.value.findIndex(t => t.id === id)
    if (index > -1) {
      toasts.value.splice(index, 1)
    }
  }

  const success = (message, title = '成功') => {
    return addToast({ type: 'success', title, message, icon: 'check_circle' })
  }

  const error = (message, title = '错误') => {
    return addToast({ type: 'error', title, message, icon: 'error', duration: 5000 })
  }

  const warning = (message, title = '警告') => {
    return addToast({ type: 'warning', title, message, icon: 'warning' })
  }

  const info = (message, title = '提示') => {
    return addToast({ type: 'info', title, message, icon: 'info' })
  }

  return {
    toasts,
    addToast,
    removeToast,
    success,
    error,
    warning,
    info,
  }
}
