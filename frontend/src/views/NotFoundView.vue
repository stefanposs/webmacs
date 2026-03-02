<template>
  <div class="not-found">
    <div class="not-found__illustration">
      <div class="not-found__robot">
        <div class="robot__head">
          <div class="robot__eye robot__eye--left"></div>
          <div class="robot__eye robot__eye--right"></div>
          <div class="robot__mouth"></div>
        </div>
        <div class="robot__antenna"></div>
      </div>
    </div>
    <h1 class="not-found__code">404</h1>
    <p class="not-found__title">Lost in the system</p>
    <p class="not-found__desc">
      The page you're looking for doesn't exist or has been moved.
    </p>
    <div class="not-found__actions">
      <router-link to="/" class="not-found__btn not-found__btn--primary">
        <i class="pi pi-home" /> Go to Dashboard
      </router-link>
      <button class="not-found__btn not-found__btn--ghost" @click="$router.back()">
        <i class="pi pi-arrow-left" /> Go Back
      </button>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.not-found {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 70vh;
  text-align: center;
  padding: 2rem;
}

/* Robot illustration */
.not-found__illustration {
  margin-bottom: 1.5rem;
}

.not-found__robot {
  position: relative;
  width: 80px;
  height: 80px;
}

.robot__head {
  width: 80px;
  height: 64px;
  background: linear-gradient(135deg, var(--wm-primary) 0%, var(--wm-secondary, #8b5cf6) 100%);
  border-radius: var(--wm-radius-xl, 16px);
  position: relative;
  box-shadow: 0 8px 24px rgba(59, 130, 246, 0.3);
}

.robot__eye {
  width: 12px;
  height: 12px;
  background: #fff;
  border-radius: 50%;
  position: absolute;
  top: 22px;
  animation: blink 3s ease-in-out infinite;

  &--left { left: 18px; }
  &--right { right: 18px; }
}

.robot__mouth {
  width: 24px;
  height: 4px;
  background: rgba(255, 255, 255, 0.6);
  border-radius: 2px;
  position: absolute;
  bottom: 14px;
  left: 50%;
  transform: translateX(-50%);
}

.robot__antenna {
  width: 4px;
  height: 14px;
  background: var(--wm-accent, #f59e0b);
  border-radius: 2px;
  position: absolute;
  top: -14px;
  left: 50%;
  transform: translateX(-50%);

  &::after {
    content: '';
    width: 10px;
    height: 10px;
    background: var(--wm-accent, #f59e0b);
    border-radius: 50%;
    position: absolute;
    top: -6px;
    left: 50%;
    transform: translateX(-50%);
    animation: pulse 2s ease-in-out infinite;
  }
}

@keyframes blink {
  0%, 90%, 100% { transform: scaleY(1); }
  95% { transform: scaleY(0.1); }
}

@keyframes pulse {
  0%, 100% { opacity: 0.5; transform: translateX(-50%) scale(1); }
  50% { opacity: 1; transform: translateX(-50%) scale(1.3); }
}

.not-found__code {
  font-size: 5rem;
  font-weight: 900;
  background: linear-gradient(135deg, var(--wm-primary) 0%, var(--wm-secondary, #8b5cf6) 100%);
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  line-height: 1;
  margin-bottom: 0.25rem;
  letter-spacing: -0.04em;
}

.not-found__title {
  font-size: 1.35rem;
  font-weight: 700;
  color: var(--wm-text);
  margin-bottom: 0.5rem;
}

.not-found__desc {
  font-size: 0.95rem;
  color: var(--wm-text-muted);
  max-width: 340px;
  line-height: 1.6;
  margin-bottom: 2rem;
}

.not-found__actions {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
  justify-content: center;
}

.not-found__btn {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.6rem 1.25rem;
  border-radius: var(--wm-radius);
  font-size: 0.88rem;
  font-weight: 600;
  text-decoration: none;
  cursor: pointer;
  border: none;
  transition: all var(--wm-transition);

  &--primary {
    background: var(--wm-primary);
    color: #fff;
    box-shadow: 0 2px 8px rgba(59, 130, 246, 0.3);

    &:hover { background: var(--wm-primary-dark); transform: translateY(-1px); }
  }

  &--ghost {
    background: transparent;
    color: var(--wm-text-secondary);
    border: 1px solid var(--wm-border);

    &:hover { background: var(--wm-bg); border-color: var(--wm-text-muted); }
  }
}
</style>
