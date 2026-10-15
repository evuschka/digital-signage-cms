<script setup>
import { ref, onMounted } from 'vue';

const props = defineProps({
    auth: Object,
    schedules: Object,
    toast: Function
});

const passwordForm = ref({
    oldPassword: '',
    newPassword: '',
    confirmPassword: '',
    error: '',
    success: ''
});

// Состояние для редактирования имени экрана
const editingScreenId = ref(null);
const editScreenName = ref('');

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

const startEditScreen = (screen) => {
    editingScreenId.value = screen.id;
    editScreenName.value = screen.name;
};

const saveScreenName = async (screenId) => {
    if (!editScreenName.value.trim()) {
        props.toast('Имя экрана не может быть пустым', 'warning');
        return;
    }
    
    try {
        const res = await fetch(`/screens/${screenId}`, {
            method: 'PUT',
            headers: { 
                'Authorization': props.auth.authHeader.value,
                'Content-Type': 'application/json' 
            },
            body: JSON.stringify({ name: editScreenName.value })
        });
        
        if (res.ok) {
            props.toast('Имя экрана обновлено', 'success');
            editingScreenId.value = null;
            // Обновляем список экранов через composable
            if (props.schedules && props.schedules.fetchScreens) {
                props.schedules.fetchScreens();
            }
        } else {
            const data = await res.json();
            props.toast(data.detail || 'Ошибка переименования', 'error');
        }
    } catch (e) {
        props.toast('Ошибка сети', 'error');
    }
};

const cancelEditScreen = () => {
    editingScreenId.value = null;
    editScreenName.value = '';
};

onMounted(() => {
    if (props.schedules && props.schedules.fetchScreens) {
        props.schedules.fetchScreens();
    }
});
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

        <!-- УПРАВЛЕНИЕ ЭКРАНАМИ (Только для регионального пользователя) -->
        <div v-if="props.auth.login.value !== 'admin_main'" class="pt-2 pb-4 border-b border-emerald-100">
            <h4 class="text-xs font-bold text-emerald-900 m-0 uppercase tracking-wider mb-3">Мои экраны</h4>
            <p class="text-[11px] text-emerald-600 mb-3">Здесь вы можете задать понятные названия для своих экранов (например, "Витрина").</p>
            
            <div v-if="!props.schedules.availableScreens.value || props.schedules.availableScreens.value.length === 0" class="text-xs text-slate-500 italic bg-slate-50 p-2 rounded">
                У вашего филиала пока нет экранов. Обратитесь к администратору.
            </div>
            <div v-else class="space-y-2">
                <div v-for="screen in props.schedules.rawScreens.value" :key="screen.id" class="flex items-center justify-between bg-emerald-50/50 p-2 border border-emerald-100 rounded-lg">
                    <div v-if="editingScreenId === screen.id" class="flex items-center gap-2 w-full">
                        <input v-model="editScreenName" type="text" class="flex-1 px-2 py-1 text-xs border border-emerald-300 rounded outline-none focus:border-emerald-500">
                        <button @click="saveScreenName(screen.id)" class="text-[10px] bg-emerald-600 text-white px-2 py-1 rounded hover:bg-emerald-700">Сохранить</button>
                        <button @click="cancelEditScreen" class="text-[10px] bg-slate-200 text-slate-700 px-2 py-1 rounded hover:bg-slate-300">Отмена</button>
                    </div>
                    <div v-else class="flex items-center justify-between w-full px-1">
                        <span class="text-sm font-medium text-emerald-900">{{ screen.name }}</span>
                        <button @click="startEditScreen(screen)" class="text-xs text-emerald-600 hover:text-emerald-800 font-medium">✏️ Изменить</button>
                    </div>
                </div>
            </div>
        </div>

        <!-- Форма смены пароля -->
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