<template>
  <div v-if="visible" class="confetti-container">
    <div v-for="i in 50" :key="i" class="confetti-piece" :class="`confetti-piece--${getColorGroup(i)}`" :style="getConfettiStyle(i)" />
  </div>
</template>

<script setup>
import { ref, onBeforeUnmount } from 'vue'

const visible = ref(false)
let hideTimer = null

const colorGroups = ['blue-teal', 'green-blue', 'amber-red']

const getColorGroup = (i) => colorGroups[i % colorGroups.length]

const getConfettiStyle = (i) => {
  const left = Math.random() * 100
  const delay = Math.random() * 0.5
  const size = Math.random() * 8 + 6
  const duration = Math.random() * 1 + 1.5
  const rotation = Math.random() * 360

  return {
    left: `${left}%`,
    width: `${size}px`,
    height: `${size * 0.6}px`,
    animationDelay: `${delay}s`,
    animationDuration: `${duration}s`,
    transform: `rotate(${rotation}deg)`,
  }
}

const show = () => {
  visible.value = true
  if (hideTimer) clearTimeout(hideTimer)
  hideTimer = setTimeout(() => {
    visible.value = false
    hideTimer = null
  }, 2500)
}

onBeforeUnmount(() => {
  if (hideTimer) clearTimeout(hideTimer)
})

defineExpose({ show })
</script>

<style scoped>
.confetti-container {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 9999;
  overflow: hidden;
}

.confetti-piece {
  position: absolute;
  top: -20px;
  border-radius: 2px;
  animation: confetti-fall linear forwards;
}

.confetti-piece--blue-teal {
  background-color: var(--color-blue-500);
}

.confetti-piece--green-blue {
  background-color: var(--color-green-500);
}

.confetti-piece--amber-red {
  background-color: var(--color-amber-500);
}

@keyframes confetti-fall {
  0% {
    transform: translateY(0) rotate(0deg);
    opacity: 1;
  }
  100% {
    transform: translateY(100vh) rotate(720deg);
    opacity: 0;
  }
}

@media (prefers-reduced-motion: reduce) {
  .confetti-piece {
    animation: none;
    display: none;
  }
}
</style>
