<script setup>
defineProps({ auth: Object });
</script>

<template>
    <div class="auth-card">
        <h2>Вход в систему</h2>
        <input v-model="auth.login.value" type="text" placeholder="Логин (например, admin_main)" @keyup.enter="auth.doLogin">
        <input v-model="auth.password.value" type="password" placeholder="Пароль" @keyup.enter="auth.doLogin">
        <button @click="auth.doLogin">Войти</button>
        <p v-if="auth.authError.value" class="error-msg">{{ auth.authError.value }}</p>
    </div>
</template>

<style scoped>
.auth-card {
    max-width: 380px;
    margin: 100px auto;
    background: #f0fdf4;
    padding: 32px;
    border-radius: 12px;
    border: 1px solid #bbf7d0;
    box-shadow: 0 10px 25px rgba(0, 0, 0, 0.05);
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}
h2 {
    text-align: center;
    color: #065f46;
    margin-bottom: 24px;
    font-size: 22px;
}
input {
    width: 100%;
    padding: 12px 14px;
    margin-bottom: 16px;
    background: #ffffff;
    color: #065f46;
    border: 1px solid #6ee7b7;
    border-radius: 6px;
    box-sizing: border-box;
    font-size: 14px;
}
input:focus {
    outline: none;
    border-color: #059669;
}
button {
    width: 100%;
    padding: 12px;
    background: #059669;
    color: white;
    border: none;
    border-radius: 6px;
    font-size: 15px;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.2s;
}
button:hover {
    background: #047857;
}
.error-msg {
    margin-top: 16px;
    color: #dc2626;
    font-size: 13px;
    text-align: center;
}
</style>