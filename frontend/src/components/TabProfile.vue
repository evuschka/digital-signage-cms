<script setup>
import { ref } from 'vue';

const props = defineProps({
    auth: Object,
    changePasswordHandler: Function
});

const passwordForm = ref({
    oldPassword: '',
    newPassword: '',
    confirmPassword: '',
    error: '',
    success: ''
});

const handlePasswordChange = async () => {
    passwordForm.value.error = '';
    passwordForm.value.success = '';

    if (!passwordForm.value.oldPassword || !passwordForm.value.newPassword || !passwordForm.value.confirmPassword) {
        passwordForm.value.error = 'Заполните все поля';
        return;
    }

    if (passwordForm.value.newPassword !== passwordForm.value.confirmPassword) {
        passwordForm.value.error = 'Новые пароли не совпадают';
        return;
    }

    // Передаем текущий и новый пароль в composable авторизации
    try {
        const success = await props.auth.updatePasswordDirect(
            passwordForm.value.oldPassword, 
            passwordForm.value.newPassword
        );
        if (success) {
            passwordForm.value.success = 'Пароль успешно изменен!';
            passwordForm.value.oldPassword = '';
            passwordForm.value.newPassword = '';
            passwordForm.value.confirmPassword = '';
        } else {
            passwordForm.value.error = 'Неверный текущий пароль или ошибка сервера';
        }
    } catch (e) {
        passwordForm.value.error = 'Ошибка при смене пароля';
    }
};
</script>

<template>
<div class="space-y-6 text-left font-sans max-w-xl">
    <div>
        <h2 class="text-xl font-bold text-emerald-900 m-0">Профиль пользователя</h2>
        <p class="text-xs text-emerald-700 mt-1">Управление учетной записью и безопасность</p>
    </div>

    <!-- Карточка информации -->
    <div class="bg-white border border-emerald-200 rounded-2xl p-6 shadow-sm space-y-4">
        <div class="flex items-center gap-3 pb-4 border-b border-emerald-100">
            <div class="w-12 h-12 rounded-full bg-emerald-100 flex items-center justify-center text-emerald-700 font-bold text-lg">
                👤
            </div>
            <div>
                <h3 class="font-bold text-emerald-950 text-sm m-0">Логин: {{ props.auth.login.value }}</h3>
                <p class="text-xs text-emerald-600 mt-0.5">Роль: {{ props.auth.login.value === 'admin_main' ? 'Администратор' : 'Региональный пользователь' }}</p>
            </div>
        </div>

        <!-- Форма смены пароля (3 строчки) -->
        <div class="space-y-4 pt-2">
            <h4 class="text-xs font-bold text-emerald-900 m-0 uppercase tracking-wider">Изменение пароля</h4>

            <div>
                <label class="block text-xs font-semibold text-emerald-900 mb-1.5">Введите текущий пароль</label>
                <input 
                    v-model="passwordForm.oldPassword" 
                    type="password" 
                    placeholder="••••••••" 
                    class="w-full px-3.5 py-2.5 bg-white text-emerald-950 border border-emerald-300 rounded-xl text-xs focus:outline-none focus:border-emerald-500 shadow-sm">
            </div>

            <div>
                <label class="block text-xs font-semibold text-emerald-900 mb-1.5">Введите новый пароль</label>
                <input 
                    v-model="passwordForm.newPassword" 
                    type="password" 
                    placeholder="••••••••" 
                    class="w-full px-3.5 py-2.5 bg-white text-emerald-950 border border-emerald-300 rounded-xl text-xs focus:outline-none focus:border-emerald-500 shadow-sm">
            </div>

            <div>
                <label class="block text-xs font-semibold text-emerald-900 mb-1.5">Повторный ввод нового пароля</label>
                <input 
                    v-model="passwordForm.confirmPassword" 
                    type="password" 
                    placeholder="••••••••" 
                    class="w-full px-3.5 py-2.5 bg-white text-emerald-950 border border-emerald-300 rounded-xl text-xs focus:outline-none focus:border-emerald-500 shadow-sm">
            </div>

            <p v-if="passwordForm.error" class="text-xs text-red-600 font-medium bg-red-50 p-2.5 rounded-xl border border-red-200">{{ passwordForm.error }}</p>
            <p v-if="passwordForm.success" class="text-xs text-emerald-700 font-medium bg-emerald-50 p-2.5 rounded-xl border border-emerald-200">{{ passwordForm.success }}</p>

            <div class="pt-2">
                <button 
                    type="button" 
                    @click="handlePasswordChange" 
                    class="px-6 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-semibold shadow-sm transition border-0 cursor-pointer">
                    Обновить пароль
                </button>
            </div>
        </div>
    </div>
</div>
</template>