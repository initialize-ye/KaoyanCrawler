<template>
  <div class="empty-state">
    <div class="empty-state__illustration">
      <span class="material-icons-outlined empty-state__icon">{{ icon }}</span>
    </div>
    <div class="empty-state__content">
      <h3 class="empty-state__title">{{ title }}</h3>
      <p class="empty-state__description">{{ description }}</p>
    </div>
    <div v-if="actionText" class="empty-state__action">
      <button class="google-btn google-btn--primary" @click="$emit('action')">
        <span class="material-icons">{{ actionIcon }}</span>
        {{ actionText }}
      </button>
    </div>
  </div>
</template>

<script setup>
defineProps({
  icon: {
    type: String,
    default: 'inbox',
  },
  title: {
    type: String,
    default: '暂无数据',
  },
  description: {
    type: String,
    default: '开始采集数据以查看结果',
  },
  actionText: {
    type: String,
    default: '',
  },
  actionIcon: {
    type: String,
    default: 'add',
  },
})

defineEmits(['action'])
</script>

<style scoped>
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 64px 24px;
  text-align: center;
}

.empty-state__illustration {
  width: 120px;
  height: 120px;
  background: var(--google-gray-100);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 24px;
  animation: float 3s ease-in-out infinite;
}

@keyframes float {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-10px);
  }
}

.empty-state__icon {
  font-size: 56px;
  color: var(--google-gray-400);
}

.empty-state__content {
  margin-bottom: 24px;
}

.empty-state__title {
  font-family: var(--google-font);
  font-size: 18px;
  font-weight: 500;
  color: var(--google-text-primary);
  margin-bottom: 8px;
}

.empty-state__description {
  font-size: 14px;
  color: var(--google-text-secondary);
  line-height: 1.6;
  max-width: 400px;
}

.empty-state__action {
  display: flex;
  gap: 12px;
}
</style>
