<script setup>
const props = defineProps({
    auth: {
        type: Object,
        required: true
    },
    changePasswordHandler: {
        type: Function,
        required: true
    }
});
</script>

<template>
<div class="max-w-md bg-white border border-emerald-200 rounded-2xl p-6 shadow-sm text-left space-y-4">
    <h2 class="text-xl font-bold text-emerald-900 m-0">Профиль пользователя</h2>
    
    <div class="bg-emerald-50/50 p-4 rounded-xl border border-emerald-100 space-y-2 text-xs">
        <p><strong class="text-emerald-900">Ваш логин:</strong> {{ props.auth.login.value }}</p>
        <p><strong class="text-emerald-900">Роль:</strong> {{ props.auth.login.value === 'admin_main' ? 'Администратор системы' : 'Региональный оператор' }}</p>
        <p><strong class="text-emerald-900">Статус сессии:</strong> Авторизован</p>
    </div>

    <button @click="props.changePasswordHandler" class="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-medium py-2.5 rounded-lg text-xs transition shadow-sm cursor-pointer border-0">
        Изменить пароль
    </button>
</div>
</template>