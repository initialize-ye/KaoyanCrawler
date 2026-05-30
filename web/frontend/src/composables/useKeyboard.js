import { onMounted, onUnmounted } from 'vue'

/**
 * 键盘快捷键组合式函数
 * @param {Object} shortcuts - 快捷键映射 { 'ctrl+k': () => {}, 'escape': () => {} }
 */
export function useKeyboard(shortcuts = {}) {
  const handleKeyDown = (e) => {
    const key = []

    if (e.ctrlKey || e.metaKey) key.push('ctrl')
    if (e.shiftKey) key.push('shift')
    if (e.altKey) key.push('alt')

    // 特殊键映射
    const keyMap = {
      ' ': 'space',
      'Escape': 'escape',
      'Enter': 'enter',
      'Backspace': 'backspace',
      'Delete': 'delete',
      'ArrowUp': 'up',
      'ArrowDown': 'down',
      'ArrowLeft': 'left',
      'ArrowRight': 'right',
      'Tab': 'tab',
    }

    const mainKey = keyMap[e.key] || e.key.toLowerCase()
    key.push(mainKey)

    const combo = key.join('+')

    if (shortcuts[combo]) {
      e.preventDefault()
      shortcuts[combo](e)
    }
  }

  onMounted(() => {
    window.addEventListener('keydown', handleKeyDown)
  })

  onUnmounted(() => {
    window.removeEventListener('keydown', handleKeyDown)
  })
}

/**
 * 常用快捷键预设
 */
export const SHORTCUTS = {
  SEARCH: 'ctrl+k',
  REFRESH: 'ctrl+r',
  NEW_CRAWL: 'ctrl+n',
  ESCAPE: 'escape',
  SAVE: 'ctrl+s',
  EXPORT: 'ctrl+e',
}
