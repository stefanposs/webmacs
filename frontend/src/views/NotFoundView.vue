<template>
  <div class="not-found">
    <h1>404</h1>
    <p>Page not found</p>
    <router-link to="/" class="btn-primary">Go to Dashboard</router-link>
  </div>
</template>

<style scoped>
.not-found {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
  text-align: center;
}

.not-found h1 {
  font-size: 4rem;
  color: #94a3b8;
}

.not-found p {
  font-size: 1.25rem;
  color: #64748b;
  margin-bottom: 2rem;
}
</style>
