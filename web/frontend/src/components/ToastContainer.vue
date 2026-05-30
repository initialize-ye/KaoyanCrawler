<template>
  <div class="toast-container">
    <TransitionGroup name="toast">
      <div
        v-for="toast in toasts"
        :key="toast.id"
        class="toast"
        :class="`toast--${toast.type}`"
        @click="removeToast(toast.id)"
      >
        <div class="toast__icon">
          <span class="material-icons">{{ toast.icon }}</span>
        </div>
        <div class="toast__content">
          <div v-if="toast.title" class="toast__title">{{ toast.title }}</div>
          <div class="toast__message">{{ toast.message }}</div>
        </div>
        <button v-if="toast.closable" class="toast__close" @click.stop="removeToast(toast.id)">
          <span class="material-icons">close</span>
        </button>
      </div>
    </TransitionGroup>
  </div>
</template>

<script setup>
import { useToast } from '../composables/useToast'

const { toasts, removeToast } = useToast()
</script>

<style scoped>
.toast-container {
  position: fixed;
  top: 80px;
  right: 24px;
  z-index: 10000;
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-width: 420px;
  width: 100%;
  pointer-events: none;
}

.toast {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 16px;
  background: var(--google-surface);
  border-radius: var(--google-radius-md);
  box-shadow: var(--google-elevation-3);
  pointer-events: auto;
  cursor: pointer;
  transition: all var(--google-transition-normal);
  animation: slideIn 0.3s ease-out;
}

.toast:hover {
  box-shadow: var(--google-elevation-4);
  transform: translateX(-4px);
}

.toast__icon {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.toast__icon .material-icons {
  font-size: 24px;
}

.toast--success .toast__icon {
  color: var(--google-green);
}

.toast--error .toast__icon {
  color: var(--google-red);
}

.toast--warning .toast__icon {
  color: var(--google-yellow-dark);
}

.toast--info .toast__icon {
  color: var(--google-blue);
}

.toast__content {
  flex: 1;
  min-width: 0;
}

.toast__title {
  font-family: var(--google-font);
  font-size: 14px;
  font-weight: 500;
  color: var(--google-text-primary);
  margin-bottom: 4px;
}

.toast__message {
  font-size: 13px;
  color: var(--google-text-secondary);
  line-height: 1.5;
}

.toast__close {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border-radius: var(--google-radius-full);
  border: none;
  background: transparent;
  color: var(--google-text-tertiary);
  cursor: pointer;
  transition: all var(--google-transition-fast);
  flex-shrink: 0;
}

.toast__close:hover {
  background: var(--google-gray-100);
  color: var(--google-text-primary);
}

.toast__close .material-icons {
  font-size: 18px;
}

/* 动画 */
.toast-enter-active {
  animation: slideIn 0.3s ease-out;
}

.toast-leave-active {
  animation: slideOut 0.2s ease-in;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateX(100px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

@keyframes slideOut {
  from {
    opacity: 1;
    transform: translateX(0);
  }
  to {
    opacity: 0;
    transform: translateX(100px);
  }
}

@media (max-width: 768px) {
  .toast-container {
    top: auto;
    bottom: 24px;
    left: 16px;
    right: 16px;
    max-width: none;
  }
}
</style>
