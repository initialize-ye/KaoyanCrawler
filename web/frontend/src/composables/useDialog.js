import { computed } from 'vue'
import { useResponsive } from './useResponsive'

export function useDialog(desktopWidth = '600px') {
  const { isMobile } = useResponsive()

  const dialogWidth = computed(() => isMobile.value ? '95%' : desktopWidth)

  return { isMobile, dialogWidth }
}
