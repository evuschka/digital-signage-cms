<script setup>
import { ref, computed, onMounted } from 'vue';
import { useAuth } from './composables/useAuth.js';
import { useHelpers } from './composables/useHelpers.js';
import { useMedia } from './composables/useMedia.js';
import { usePlaylists } from './composables/usePlaylists.js';
import { useSchedules } from './composables/useSchedules.js';
import { useUsers } from './composables/useUsers.js';
import { useReports } from './composables/useReports.js';

// Вспомогательные функции
const { isImage, isVideo, formatSize, formatDate, getRemainingDays } = useHelpers();

// Уведомления (тосты)
const toasts = ref([]); 
let toastIdCounter = 0;
const showToast = (message, type = 'info') => {
    const id = toastIdCounter++;
    toasts.value.push({ id, message, type });
    setTimeout(() => { toasts.value = toasts.value.filter(t => t.id !== id); }, 4500);
};

const safeJson = async (res) => {
    try { return await res.json(); } 
    catch (e) { return { detail: "Ошибка сервера" }; }
};

// Всплывающее окно подтверждения
const confirmDialog = ref({ show: false, x: 0, y: 0, text: '', onConfirm: null, isBelow: false });
const requestConfirm = (e, text, callback) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const posX = rect.left + rect.width / 2;
    const isNearTop = rect.top < 120;
    const posY = isNearTop ? rect.bottom : rect.top;
    confirmDialog.value = { show: true, x: posX, y: posY, text: text, onConfirm: callback, isBelow: isNearTop };
};

// Инициализация модулей логики
const auth = useAuth();
const users = useUsers(auth.authHeader, showToast, safeJson);
const media = useMedia(auth.authHeader, auth.login, showToast, safeJson);
const playlists = usePlaylists(auth.authHeader, showToast, isImage, isVideo, safeJson, () => media.files.value);
const schedules = useSchedules(auth.authHeader, showToast, requestConfirm, safeJson);
const reports = useReports(auth.authHeader, showToast, safeJson);

// Достаем рефы графиков наружу для правильного привязывания в шаблоне
const { chartStatusRef, chartCityRef } = reports;

const currentTab = ref('media');

// Функция загрузки всех данных
const loadAllData = async () => {
    if (auth.login.value === 'admin_main') {
        await users.fetchAdminUsers();
        if (users.adminRequests.value.length > 0) auth.showAdminAlertModal.value = true;
    }
    media.fetchFiles(); 
    media.fetchStats(); 
    media.fetchTrash();
    schedules.fetchScreens(); 
    schedules.fetchSchedules();
    reports.fetchMonitoring(); 
    if (auth.login.value === 'admin_main') playlists.fetchPlaylists();
};

// Загрузка при старте (если уже авторизован)
onMounted(async () => {
    if (auth.isAuthenticated.value) {
        await loadAllData();
    }
});

// Обработка входа
const authenticate = async () => {
    const success = await auth.doLogin();
    if (success) {
        await loadAllData();
    }
};

// Обработка выхода
const logoutHandler = () => {
    auth.doLogout();
    media.files.value = []; 
    media.trashFiles.value = [];
    schedules.schedules.value = []; 
    playlists.playlists.value = [];
    currentTab.value = 'media'; 
    auth.showAdminAlertModal.value = false;
};

// Переключение вкладок
const switchTab = (tab) => {
    currentTab.value = tab;
    if (tab === 'reports') { 
        reports.fetchAnalytics(); 
        reports.fetchHistory(); 
        reports.fetchStorageHistory(); 
    }
    if (tab === 'users') users.fetchAdminUsers();
    if (tab === 'playlists' && auth.login.value === 'admin_main') playlists.fetchPlaylists();
    if (tab === 'schedule' && auth.login.value === 'admin_main') playlists.fetchPlaylists();
};

const getPlaylistName = (id) => playlists.playlists.value.find(p => p.id === id)?.name || 'Неизвестный';

// ==========================================
// ЛОГИКА ПРОФИЛЯ
// ==========================================
const profileForm = ref({ oldPassword: '', newPassword: '', confirmPassword: '', error: '', success: '' });

const updatePassword = async () => {
    profileForm.value.error = ''; profileForm.value.success = '';
    if (!profileForm.value.oldPassword || !profileForm.value.newPassword) {
        profileForm.value.error = 'Заполните все поля'; return;
    }
    if (profileForm.value.newPassword !== profileForm.value.confirmPassword) {
        profileForm.value.error = 'Новые пароли не совпадают'; return;
    }
    try {
        const res = await fetch('/change-password/', {
            method: 'POST',
            headers: { 'Authorization': auth.authHeader.value, 'Content-Type': 'application/json' },
            body: JSON.stringify({ old_password: profileForm.value.oldPassword, new_password: profileForm.value.newPassword })
        });
        const data = await safeJson(res);
        if (res.ok) {
            profileForm.value.success = 'Пароль успешно изменен! Пожалуйста, войдите с новым паролем.';
            profileForm.value.oldPassword = ''; profileForm.value.newPassword = ''; profileForm.value.confirmPassword = '';
            setTimeout(() => logoutHandler(), 2000);
        } else {
            profileForm.value.error = data.detail || 'Ошибка смены пароля';
        }
    } catch (e) { profileForm.value.error = 'Ошибка сети'; }
};

// ==========================================
// ЛОГИКА ЦЕЛЕВЫХ ЭКРАНОВ (РАСПИСАНИЕ И ПЛЕЕР)
// ==========================================
const fallbackScreens = {
    moscow: ['Москва-Экран-1', 'Москва-Экран-2', 'Москва-Экран-3'],
    spb: ['СПБ-Экран-1', 'СПБ-Экран-2'],
    novocheboksarsk: ['Новочебоксарск-Экран-1'],
    yartsevo: ['Ярцево-Экран-1'],
    azov: ['Азов-Экран-1'],
    orenburg: ['Оренбург-Экран-1'],
    chernyakhovsk: ['Черняховск-Экран-1']
};

const currentScreens = computed(() => {
    const city = schedules.newSchedule.value.city;
    if (!city || city === 'global') return [];
    
    const apiMap = schedules.allScreensMap?.value || {};
    if (Object.keys(apiMap).length > 0 && apiMap[city]) {
        return apiMap[city];
    }
    return fallbackScreens[city] || [];
});

const toggleSelectAllScreens = () => {
    const screens = currentScreens.value;
    if (!screens.length) return;
    
    if (schedules.newSchedule.value.screens.length === screens.length) {
        schedules.newSchedule.value.screens = []; 
    } else {
        schedules.newSchedule.value.screens = [...screens]; 
    }
};

const handleCityChange = () => {
    schedules.newSchedule.value.screens = []; 
    if (schedules.onCityChange) schedules.onCityChange();
};

// ==========================================
// ЛОГИКА ПЛЕЕРА ТРАНСЛЯЦИЙ (ЭТАП 9)
// ==========================================
const monitorSelectedCity = ref('moscow');
const monitorSelectedScreen = ref('Москва-Экран-1');

const handleMonitorCityChange = () => {
    const apiMap = schedules.allScreensMap?.value || {};
    const screens = apiMap[monitorSelectedCity.value] || fallbackScreens[monitorSelectedCity.value] || [];
    monitorSelectedScreen.value = screens.length > 0 ? screens[0] : '';
};

// Ищем активное расписание для выбранного города и экрана
const activeMonitorSchedule = computed(() => {
    if (!monitorSelectedCity.value || !monitorSelectedScreen.value) return null;
    
    // Перебираем расписания в поисках "Активен" для нужного таргета
    const list = schedules.schedules?.value || [];
    return list.find(s => {
        if (s.status !== 'Активен') return false;
        if (s.city !== 'global' && s.city !== monitorSelectedCity.value) return false;
        
        // Если указаны конкретные экраны, проверяем их
        if (s.screens && s.screens.length > 0) {
            if (!s.screens.includes(monitorSelectedScreen.value)) return false;
        }
        return true;
    });
});

const getFileUrl = (fileName) => {
    const found = media.files.value.find(f => f.name === fileName);
    return found ? found.url : '';
};
</script>

<template>
<div class="bg-white text-emerald-950 min-h-screen flex flex-col font-sans">
    <div class="flex h-screen overflow-hidden relative">
        
        <!-- Тосты (Уведомления) -->
        <div class="fixed top-6 right-6 z-[9999] flex flex-col gap-3 pointer-events-none">
            <transition-group 
                enter-active-class="transition duration-300 ease-out transform" enter-from-class="opacity-0 translate-x-8" enter-to-class="opacity-100 translate-x-0"
                leave-active-class="transition duration-200 ease-in transform" leave-from-class="opacity-100 translate-x-0" leave-to-class="opacity-0 translate-x-8">
                <div v-for="toast in toasts" :key="toast.id" 
                     class="px-4 py-3 rounded-lg shadow-xl border flex items-center gap-3 w-80 pointer-events-auto backdrop-blur-sm"
                     :class="{
                        'bg-emerald-50/90 text-emerald-900 border-emerald-200': toast.type === 'success',
                        'bg-red-50/90 text-red-900 border-red-200': toast.type === 'error',
                        'bg-amber-50/90 text-amber-900 border-amber-200': toast.type === 'warning' || toast.type === 'info'
                     }">
                    <span v-if="toast.type === 'success'" class="text-emerald-500 text-lg shrink-0">✅</span>
                    <span v-if="toast.type === 'error'" class="text-red-500 text-lg shrink-0">❌</span>
                    <span v-if="toast.type === 'warning' || toast.type === 'info'" class="text-amber-500 text-lg shrink-0">⚠️</span>
                    <p class="text-sm font-medium leading-tight">{{ toast.message }}</p>
                </div>
            </transition-group>
        </div>

        <!-- Экран авторизации -->
        <div v-if="!auth.isAuthenticated.value" class="w-full max-w-md mx-auto mt-16 bg-emerald-50 p-8 rounded-xl border border-emerald-200 shadow-xl self-start">
            <h2 class="text-2xl font-bold mb-6 text-emerald-800 text-center">Вход в систему</h2>
            
            <div v-if="!auth.isResetMode.value">
                <!-- Принудительно светлые фоны -->
                <input v-model="auth.login.value" type="text" placeholder="Логин (например, user_msk)" class="w-full mb-4 px-4 py-2 bg-white text-emerald-950 border border-emerald-300 rounded focus:outline-none focus:border-emerald-600 text-sm">
                <input v-model="auth.password.value" type="password" @keyup.enter="authenticate" placeholder="Пароль" class="w-full mb-4 px-4 py-2 bg-white text-emerald-950 border border-emerald-300 rounded focus:outline-none focus:border-emerald-600 text-sm">
                <button @click="authenticate" class="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-medium py-2 rounded transition text-sm mb-3">Войти</button>
                <div class="text-center">
                    <button @click="auth.isResetMode.value = true; auth.resetForm.value.success = ''" class="text-xs text-emerald-700 hover:underline">Забыли пароль?</button>
                </div>
            </div>
            
            <div v-else class="space-y-3">
                <p class="text-xs text-emerald-800">Введите ваш логин для отправки запроса администратору:</p>
                <input v-model="auth.resetForm.value.username" type="text" placeholder="Ваш логин" class="w-full px-4 py-2 bg-white text-emerald-950 border border-emerald-300 rounded text-sm focus:outline-none focus:border-emerald-600">
                <button @click="auth.requestReset" class="w-full bg-emerald-600 hover:bg-emerald-700 text-white py-2 rounded text-sm font-medium">Отправить запрос</button>
                <button @click="auth.isResetMode.value = false" class="w-full bg-emerald-200 hover:bg-emerald-300 text-emerald-900 py-2 rounded text-sm">Назад ко входу</button>
                <p v-if="auth.resetForm.value.success" class="text-xs text-emerald-700 bg-emerald-100 p-2 rounded mt-2 text-center">{{ auth.resetForm.value.success }}</p>
            </div>
            
            <p v-if="auth.authError.value" class="mt-4 text-red-600 text-xs text-center">{{ auth.authError.value }}</p>
        </div>

        <template v-else>
            <div v-if="auth.showAdminAlertModal.value && auth.login.value === 'admin_main'" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
                <div class="bg-white p-6 rounded-xl max-w-md w-full border border-emerald-200 shadow-2xl text-center">
                    <div class="text-amber-600 text-3xl mb-2">🔔</div>
                    <h3 class="text-lg font-bold text-emerald-900 mb-2">Внимание, запросы сброса!</h3>
                    <p class="text-xs text-emerald-700 mb-4">Есть активные запросы на сброс пароля от региональных пользователей.</p>
                    <div class="bg-amber-50 p-3 rounded mb-6 text-left max-h-32 overflow-y-auto border border-amber-200">
                        <div v-for="req in users.adminRequests.value" :key="req.username" class="text-xs text-amber-900 mb-1">
                            • Пользователь: <span class="font-semibold">{{ req.username }}</span> ({{ req.time }})
                        </div>
                    </div>
                    <button @click="auth.showAdminAlertModal.value = false; switchTab('users')" class="w-full bg-emerald-600 hover:bg-emerald-700 text-white py-2 rounded text-sm font-medium">Перейти к управлению</button>
                </div>
            </div>

            <aside class="w-64 bg-emerald-50 border-r border-emerald-200 flex flex-col hidden md:flex h-full relative z-20">
                <div class="p-4 border-b border-emerald-200 text-left">
                    <h1 class="text-xl font-bold tracking-tight text-emerald-800">DS CMS</h1>
                    <p class="text-emerald-700 text-xs mt-1">Роль: {{ auth.login.value === 'admin_main' ? 'Администратор' : 'Рег. пользователь' }}</p>
                </div>
                
                <nav class="flex-1 p-4 space-y-2 overflow-y-auto pb-12">
                    <a href="#" @click.prevent="switchTab('media')" :class="currentTab === 'media' ? 'bg-emerald-600 text-white font-medium shadow-sm' : 'text-emerald-900 hover:bg-emerald-100/60'" class="block w-full text-left px-4 py-2 rounded-lg transition text-sm">📁 Медиатека</a>
                    <a href="#" v-if="auth.login.value === 'admin_main'" @click.prevent="switchTab('playlists')" :class="currentTab === 'playlists' ? 'bg-emerald-600 text-white font-medium shadow-sm' : 'text-emerald-900 hover:bg-emerald-100/60'" class="block w-full text-left px-4 py-2 rounded-lg transition text-sm">📑 Плейлисты</a>
                    <a href="#" v-if="auth.login.value === 'admin_main'" @click.prevent="switchTab('import')" :class="currentTab === 'import' ? 'bg-emerald-600 text-white font-medium shadow-sm' : 'text-emerald-900 hover:bg-emerald-100/60'" class="block w-full text-left px-4 py-2 rounded-lg transition text-sm">📥 Импорт файлов</a>
                    <a href="#" v-if="auth.login.value === 'admin_main'" @click.prevent="switchTab('trash')" :class="currentTab === 'trash' ? 'bg-emerald-600 text-white font-medium shadow-sm' : 'text-emerald-900 hover:bg-emerald-100/60'" class="block w-full text-left px-4 py-2 rounded-lg transition text-sm">🗑️ Корзина</a>
                    <a href="#" @click.prevent="switchTab('schedule')" :class="currentTab === 'schedule' ? 'bg-emerald-600 text-white font-medium shadow-sm' : 'text-emerald-900 hover:bg-emerald-100/60'" class="block w-full text-left px-4 py-2 rounded-lg transition text-sm">📅 Расписания</a>
                    <a href="#" @click.prevent="switchTab('monitoring')" :class="currentTab === 'monitoring' ? 'bg-emerald-600 text-white font-medium shadow-sm' : 'text-emerald-900 hover:bg-emerald-100/60'" class="block w-full text-left px-4 py-2 rounded-lg transition text-sm">🖥️ Мониторинг сети</a>
                    <a href="#" v-if="auth.login.value === 'admin_main'" @click.prevent="switchTab('reports')" :class="currentTab === 'reports' ? 'bg-emerald-600 text-white font-medium shadow-sm' : 'text-emerald-900 hover:bg-emerald-100/60'" class="block w-full text-left px-4 py-2 rounded-lg transition text-sm">📊 Отчёты</a>
                    <a href="#" v-if="auth.login.value === 'admin_main'" @click.prevent="switchTab('users')" :class="currentTab === 'users' ? 'bg-emerald-600 text-white font-medium shadow-sm' : 'text-emerald-900 hover:bg-emerald-100/60'" class="block w-full text-left px-4 py-2 rounded-lg transition text-sm">👥 Пользователи <span v-if="users.adminRequests.value.length > 0" class="bg-red-500 text-white text-[10px] px-1.5 py-0.5 rounded-full ml-1">{{ users.adminRequests.value.length }}</span></a>
                    <a href="#" @click.prevent="switchTab('profile')" :class="currentTab === 'profile' ? 'bg-emerald-600 text-white font-medium shadow-sm' : 'text-emerald-900 hover:bg-emerald-100/60'" class="block w-full text-left px-4 py-2 rounded-lg transition text-sm">👤 Профиль</a>
                </nav>
                
                <div class="p-4 border-t border-emerald-200 bg-emerald-100/40 text-left bg-emerald-50">
                    <div class="mb-4">
                        <p class="text-xs text-emerald-800 font-semibold mb-1 flex justify-between"><span>Хранилище</span><span>{{ media.storageStats.value.percent }}%</span></p>
                        <div class="w-full bg-emerald-200 rounded-full h-1.5 mb-1">
                            <div :class="media.storageStats.value.percent > 90 ? 'bg-red-500' : 'bg-emerald-500'" class="h-1.5 rounded-full" :style="{ width: media.storageStats.value.percent + '%' }"></div>
                        </div>
                        <p class="text-[10px] text-emerald-600">{{ formatSize(media.storageStats.value.used) }} из 100 ГБ</p>
                    </div>
                    <button @click="requestConfirm($event, 'Вы действительно хотите выйти из системы?', logoutHandler)" class="w-full bg-red-100 hover:bg-red-200 text-red-800 border border-red-300 px-4 py-2 rounded-lg text-sm transition font-medium text-center">Выйти</button>
                </div>
            </aside>

            <main class="flex-1 p-8 overflow-y-auto bg-white h-full text-sm text-left">
                
                <!-- Вкладка: Пользователи -->
                <div v-if="currentTab === 'users' && auth.login.value === 'admin_main'" class="space-y-6">
                    <div class="bg-emerald-50 border border-emerald-200 rounded-xl p-6 shadow-sm">
                        <div class="flex justify-between items-center mb-6">
                            <h2 class="text-xl font-semibold text-emerald-900">Управление учетными записями</h2>
                            <div class="flex gap-2">
                                <button @click="users.showAddUserModal.value = true" class="text-xs bg-emerald-600 hover:bg-emerald-700 text-white px-3 py-1.5 rounded-md font-medium shadow-sm">+ Новый пользователь</button>
                                <button @click="users.fetchAdminUsers" class="text-xs bg-emerald-200 hover:bg-emerald-300 text-emerald-900 px-3 py-1.5 rounded-md font-medium">Обновить</button>
                            </div>
                        </div>

                        <div v-if="users.showAddUserModal.value" class="bg-emerald-100/50 border border-emerald-200 rounded-xl p-6 shadow-md mb-6">
                            <h3 class="text-lg font-medium mb-4 text-emerald-800">Создание нового пользователя</h3>
                            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
                                <div>
                                    <label class="block text-xs text-emerald-700 mb-1 font-medium">Логин (Username)</label>
                                    <input v-model="users.newUserForm.value.username" type="text" placeholder="Например: user_kazan" class="w-full bg-white border border-emerald-300 rounded p-2 text-sm">
                                </div>
                                <div>
                                    <label class="block text-xs text-emerald-700 mb-1 font-medium">Первичный пароль</label>
                                    <input v-model="users.newUserForm.value.password" type="text" placeholder="Пароль для входа" class="w-full bg-white border border-emerald-300 rounded p-2 text-sm">
                                </div>
                                <div>
                                    <label class="block text-xs text-emerald-700 mb-1 font-medium">Роль</label>
                                    <select v-model="users.newUserForm.value.role" class="w-full bg-white border border-emerald-300 rounded p-2 text-sm">
                                        <option value="regional">Региональный (Филиал)</option>
                                        <option value="admin">Администратор (Полный доступ)</option>
                                    </select>
                                </div>
                                <div>
                                    <label class="block text-xs text-emerald-700 mb-1 font-medium">Филиал (Город)</label>
                                    <select v-model="users.newUserForm.value.city_id" class="w-full bg-white border border-emerald-300 rounded p-2 text-sm">
                                        <option value="global">Глобальная сеть (Все города)</option>
                                        <option value="moscow">Москва</option>
                                        <option value="spb">Санкт-Петербург</option>
                                        <option value="novocheboksarsk">Новочебоксарск</option>
                                        <option value="yartsevo">Ярцево</option>
                                        <option value="azov">Азов</option>
                                        <option value="orenburg">Оренбург</option>
                                        <option value="chernyakhovsk">Черняховск</option>
                                    </select>
                                </div>
                            </div>
                            <div class="flex justify-end gap-3">
                                <button @click="users.showAddUserModal.value = false" class="bg-emerald-200 text-emerald-900 px-4 py-2 rounded text-sm">Отмена</button>
                                <button @click="users.createUser" class="bg-emerald-600 text-white px-4 py-2 rounded text-sm">Создать пользователя</button>
                            </div>
                        </div>

                        <div v-if="users.adminRequests.value.length > 0" class="mb-8 bg-amber-50 border border-amber-300 rounded-lg p-4">
                            <h3 class="text-sm font-bold text-amber-900 mb-3">🔔 Запросы на сброс пароля от пользователей:</h3>
                            <div class="space-y-2">
                                <div v-for="req in users.adminRequests.value" :key="req.username" class="bg-white border border-amber-200 p-3 rounded flex justify-between items-center text-xs">
                                    <div>
                                        <p class="font-semibold text-emerald-900">Пользователь: <span class="text-emerald-700 font-bold">{{ req.username }}</span></p>
                                        <p class="text-slate-500 text-[10px]">Время запроса: {{ req.time }}</p>
                                    </div>
                                    <button @click="requestConfirm($event, `Сбросить пароль для ${req.username}?`, () => users.forceReset(req.username))" class="bg-amber-600 hover:bg-amber-700 text-white text-xs px-3 py-1.5 rounded transition font-medium">Выдать новый пароль</button>
                                </div>
                            </div>
                        </div>
                        <h3 class="text-sm font-semibold text-emerald-900 mb-3">Все пользователи системы</h3>
                        <div class="bg-white border border-emerald-200 rounded-lg overflow-hidden">
                            <table class="w-full text-sm text-left text-emerald-900">
                                <thead class="text-xs text-emerald-800 uppercase bg-emerald-100/70 border-b border-emerald-200">
                                    <tr>
                                        <th class="px-6 py-3">Логин</th>
                                        <th class="px-6 py-3">Роль</th>
                                        <th class="px-6 py-3">Филиал / Город</th>
                                        <th class="px-6 py-3">Действия</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr v-for="(info, uname) in users.adminUsers.value" :key="uname" class="border-b border-emerald-200 hover:bg-emerald-50">
                                        <td class="px-6 py-4 font-medium">{{ uname }}</td>
                                        <td class="px-6 py-4">{{ info.role === 'admin' ? 'Администратор' : 'Региональный' }}</td>
                                        <td class="px-6 py-4">{{ info.city_id }}</td>
                                        <td class="px-6 py-4 flex gap-2">
                                            <button @click="requestConfirm($event, `Сбросить пароль для ${uname}?`, () => users.forceReset(uname))" class="bg-emerald-600 hover:bg-emerald-700 text-white text-xs px-3 py-1.5 rounded transition">Сбросить пароль</button>
                                            <button v-if="uname !== auth.login.value" @click="requestConfirm($event, `Точно удалить пользователя ${uname}?`, () => users.deleteUser(uname))" class="bg-red-50 hover:bg-red-100 text-red-700 text-xs px-3 py-1.5 rounded border border-red-200 transition">Удалить</button>
                                        </td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>

                <!-- Вкладка: Профиль -->
                <div v-if="currentTab === 'profile'">
                    <section class="bg-emerald-50 border border-emerald-200 rounded-xl p-6 shadow-sm max-w-xl mx-auto">
                        <h2 class="text-xl font-semibold text-emerald-900 mb-6">Настройки профиля</h2>
                        <div class="mb-8 p-4 bg-white rounded-lg border border-emerald-200">
                            <p class="text-sm text-emerald-600 mb-2">Текущий пользователь:</p>
                            <p class="font-semibold text-emerald-900 text-lg">{{ auth.login.value }}</p>
                            <p class="text-sm text-emerald-700 mt-1">Роль: {{ auth.login.value === 'admin_main' ? 'Администратор' : 'Региональный менеджер' }}</p>
                        </div>
                        <div class="p-5 bg-white rounded-lg border border-emerald-200">
                            <h3 class="font-medium text-emerald-900 mb-4">Смена пароля</h3>
                            <!-- ПРИНУДИТЕЛЬНЫЙ СВЕТЛЫЙ ФОН: bg-white text-emerald-950 -->
                            <input v-model="profileForm.oldPassword" type="password" placeholder="Текущий пароль" class="w-full mb-3 px-4 py-2 bg-white text-emerald-950 placeholder-gray-400 border border-emerald-300 rounded focus:outline-none focus:border-emerald-600 text-sm">
                            <input v-model="profileForm.newPassword" type="password" placeholder="Новый пароль" class="w-full mb-3 px-4 py-2 bg-white text-emerald-950 placeholder-gray-400 border border-emerald-300 rounded focus:outline-none focus:border-emerald-600 text-sm">
                            <input v-model="profileForm.confirmPassword" type="password" placeholder="Повторите новый пароль" class="w-full mb-4 px-4 py-2 bg-white text-emerald-950 placeholder-gray-400 border border-emerald-300 rounded focus:outline-none focus:border-emerald-600 text-sm">
                            
                            <button @click="updatePassword" class="w-full bg-emerald-600 hover:bg-emerald-700 text-white py-2 rounded text-sm transition font-medium">Сохранить новый пароль</button>
                            <p v-if="profileForm.error" class="mt-3 text-red-600 text-sm">{{ profileForm.error }}</p>
                            <p v-if="profileForm.success" class="mt-3 text-emerald-600 text-sm font-medium">{{ profileForm.success }}</p>
                        </div>
                    </section>
                </div>

                <!-- Вкладка: Медиатека -->
                <div v-if="currentTab === 'media'">
                    <section class="bg-emerald-50 border border-emerald-200 rounded-xl p-6 shadow-sm">
                        <div class="flex justify-between items-center mb-6">
                            <h2 class="text-xl font-semibold text-emerald-900">Интерфейс управления контентом</h2>
                            <button @click="media.fetchFiles(); media.fetchStats()" class="text-xs bg-emerald-200 hover:bg-emerald-300 text-emerald-900 px-3 py-1.5 rounded-md font-medium">Обновить</button>
                        </div>
                        <div class="flex flex-col md:flex-row gap-3 mb-6 bg-white p-4 rounded-lg border border-emerald-200 shadow-sm">
                            <input v-model="media.searchQuery.value" type="text" placeholder="Поиск по имени файла..." class="flex-1 bg-white border border-emerald-300 rounded-lg p-2 text-sm focus:outline-none focus:border-emerald-600">
                            <select v-if="auth.login.value === 'admin_main'" v-model="media.filterCity.value" class="w-full md:w-48 bg-white border border-emerald-300 rounded-lg p-2 text-sm focus:outline-none focus:border-emerald-600">
                                <option value="all">Все папки офисов</option>
                                <option value="global">Глобальная (global)</option>
                                <option value="moscow">Москва</option>
                                <option value="spb">Санкт-Петербург</option>
                                <option value="novocheboksarsk">Новочебоксарск</option>
                                <option value="yartsevo">Ярцево</option>
                                <option value="azov">Азов</option>
                                <option value="orenburg">Оренбург</option>
                                <option value="chernyakhovsk">Черняховск</option>
                            </select>
                            <select v-model="media.sortBy.value" class="w-full md:w-56 bg-white border border-emerald-300 rounded-lg p-2 text-sm focus:outline-none focus:border-emerald-600">
                                <option value="date_desc">Сначала новые</option>
                                <option value="date_asc">Сначала старые</option>
                                <option value="name_asc">По имени (А - Я)</option>
                                <option value="name_desc">По имени (Я - А)</option>
                                <option value="size_desc">Размер (большие сверху)</option>
                                <option value="size_asc">Размер (маленькие сверху)</option>
                            </select>
                        </div>
                        <div v-if="media.filteredAndSortedFiles.value.length === 0" class="text-center py-8 text-emerald-700 bg-white rounded-lg border border-dashed border-emerald-200">Контент не найден.</div>
                        <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                            <div v-for="file in media.filteredAndSortedFiles.value" :key="file.name" class="bg-white border border-emerald-200 p-4 rounded-lg flex flex-col gap-3 shadow-sm hover:shadow-md transition">
                                <div class="flex items-center gap-3">
                                    <div class="shrink-0 w-16 h-16 bg-slate-100 border border-emerald-100 rounded flex items-center justify-center overflow-hidden">
                                        <img v-if="isImage(file.name)" :src="file.url" class="object-cover w-full h-full">
                                        <video v-else-if="isVideo(file.name)" :src="file.url" class="object-cover w-full h-full" muted></video>
                                        <span v-else class="text-xs font-bold text-emerald-400">ФАЙЛ</span>
                                    </div>
                                    <div class="overflow-hidden">
                                        <p class="font-medium text-sm text-emerald-900 truncate" :title="file.name">{{ file.name }}</p>
                                        <p class="text-[11px] text-emerald-600 mt-0.5">Размер: {{ formatSize(file.size) }}</p>
                                        <p class="text-[11px] text-emerald-600">{{ formatDate(file.last_modified) }}</p>
                                    </div>
                                </div>
                                <div class="flex gap-2 mt-auto">
                                    <a :href="file.url" target="_blank" class="flex-1 text-center bg-emerald-100 hover:bg-emerald-200 text-emerald-800 text-xs px-3 py-1.5 rounded transition font-medium">Смотреть</a>
                                    <button v-if="auth.login.value === 'admin_main'" @click="requestConfirm($event, 'Переместить файл в корзину?', () => media.deleteFile(file.name))" class="flex-1 bg-red-50 hover:bg-red-100 text-red-700 text-xs px-3 py-1.5 rounded border border-red-200 transition">В корзину</button>
                                </div>
                            </div>
                        </div>
                    </section>
                </div>

                <!-- Вкладка: Плейлисты -->
                <div v-if="currentTab === 'playlists' && auth.login.value === 'admin_main'" class="space-y-6">
                    <div class="flex justify-between items-center">
                        <h2 class="text-xl font-semibold text-emerald-900">Управление плейлистами (Фото/Видео ряды)</h2>
                        <button @click="playlists.showPlaylistModal.value = true" class="bg-emerald-600 text-white px-4 py-2 rounded-lg text-sm shadow-sm">+ Создать плейлист</button>
                    </div>

                    <div v-if="playlists.showPlaylistModal.value" class="bg-emerald-50 border border-emerald-200 rounded-xl p-6 shadow-md">
                        <h3 class="text-lg font-medium mb-4 text-emerald-800">Конструктор плейлиста</h3>
                        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
                            <div>
                                <label class="block text-xs text-emerald-700 mb-1 font-medium">Название плейлиста</label>
                                <input v-model="playlists.newPlaylist.value.name" type="text" placeholder="Например: Утренний показ" class="w-full bg-white border border-emerald-300 rounded p-2 text-sm">
                            </div>
                            <div>
                                <label class="block text-xs text-emerald-700 mb-1 font-medium">Филиал (Город)</label>
                                <select v-model="playlists.newPlaylist.value.city" class="w-full bg-white border border-emerald-300 rounded p-2 text-sm">
                                    <option value="global">Вся сеть</option>
                                    <option value="moscow">Москва</option>
                                    <option value="spb">Санкт-Петербург</option>
                                    <option value="novocheboksarsk">Новочебоксарск</option>
                                    <option value="yartsevo">Ярцево</option>
                                    <option value="azov">Азов</option>
                                    <option value="orenburg">Оренбург</option>
                                    <option value="chernyakhovsk">Черняховск</option>
                                </select>
                            </div>
                            <div>
                                <label class="block text-xs text-emerald-700 mb-1 font-medium">Пауза между файлами (сек)</label>
                                <input v-model.number="playlists.newPlaylist.value.interval" type="number" min="0" class="w-full bg-white border border-emerald-300 rounded p-2 text-sm">
                            </div>
                            <div>
                                <label class="block text-xs text-emerald-700 mb-1 font-medium">Количество повторов</label>
                                <input v-model.number="playlists.newPlaylist.value.repeats" type="number" min="1" class="w-full bg-white border border-emerald-300 rounded p-2 text-sm">
                            </div>
                        </div>

                        <div class="bg-white p-4 rounded-lg border border-emerald-200 mb-4">
                            <h4 class="text-xs font-semibold text-emerald-900 mb-2">Состав плейлиста:</h4>
                            <div class="flex gap-2 mb-3">
                                <select v-model="playlists.selectedFileToAdd.value" class="flex-1 bg-white border border-emerald-300 rounded p-2 text-sm">
                                    <option v-for="f in media.files.value" :key="f.name" :value="f.name">{{ f.name }}</option>
                                </select>
                                <button @click="playlists.addFileToPlaylist" class="bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2 rounded text-sm">Добавить файл</button>
                            </div>

                            <div v-if="playlists.newPlaylist.value.items.length === 0" class="text-xs text-emerald-600 py-4 text-center">Плейлист пока пуст. Добавьте файлы.</div>
                            <div v-else class="space-y-2">
                                <div v-for="(item, idx) in playlists.newPlaylist.value.items" :key="idx" class="flex items-center justify-between bg-emerald-50/50 p-2.5 rounded border border-emerald-200 text-xs">
                                    <div class="flex items-center gap-2">
                                        <div class="flex flex-col gap-0.5">
                                            <button @click="playlists.movePlaylistItem(idx, -1)" :disabled="idx === 0" class="text-[10px] bg-white border px-1 rounded disabled:opacity-30 hover:bg-emerald-100">▲</button>
                                            <button @click="playlists.movePlaylistItem(idx, 1)" :disabled="idx === playlists.newPlaylist.value.items.length - 1" class="text-[10px] bg-white border px-1 rounded disabled:opacity-30 hover:bg-emerald-100">▼</button>
                                        </div>
                                        <span class="font-bold text-emerald-800 ml-1">#{{ idx + 1 }}</span>
                                        <span class="font-medium text-emerald-950">{{ item.file }}</span>
                                        <span v-if="isVideo(item.file)" class="bg-purple-100 text-purple-800 text-[10px] px-1.5 py-0.5 rounded">Видео</span>
                                        <span v-else class="bg-blue-100 text-blue-800 text-[10px] px-1.5 py-0.5 rounded">Фото</span>
                                    </div>
                                    <div class="flex items-center gap-3">
                                        <div v-if="isImage(item.file)" class="flex items-center gap-1.5">
                                            <span class="text-emerald-700">Время показа (сек):</span>
                                            <input v-model.number="item.duration" type="number" min="1" class="w-16 bg-white border border-emerald-300 rounded p-1 text-center">
                                        </div>
                                        <div v-else class="text-slate-500 italic">Длительность: по видеоряду</div>
                                        <button @click="playlists.removePlaylistItem(idx)" class="text-red-600 hover:text-red-800 font-bold px-2 py-1 bg-red-50 rounded border border-red-200">✕</button>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div class="flex justify-end gap-3">
                            <button @click="playlists.showPlaylistModal.value = false" class="bg-emerald-200 text-emerald-900 px-4 py-2 rounded text-sm">Отмена</button>
                            <button @click="playlists.savePlaylist" class="bg-emerald-600 text-white px-4 py-2 rounded text-sm">Сохранить плейлист</button>
                        </div>
                    </div>

                    <!-- Модальное окно предпросмотра -->
                    <div v-if="playlists.showPreviewModal.value" class="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
                        <div class="bg-white rounded-xl shadow-2xl max-w-2xl w-full overflow-hidden flex flex-col border border-emerald-300">
                            <div class="bg-emerald-800 text-white px-4 py-3 flex justify-between items-center">
                                <h3 class="font-semibold text-sm">Предпросмотр плейлиста: {{ playlists.previewPlaylistName.value }}</h3>
                                <button @click="playlists.closePreview" class="text-white hover:text-gray-200 font-bold text-lg">✕</button>
                            </div>
                            <div class="p-6 flex flex-col items-center justify-center bg-black min-h-[350px] relative">
                                <div v-if="playlists.previewCurrentItem.value">
                                    <img v-if="isImage(playlists.previewCurrentItem.value.file)" :src="getFileUrl(playlists.previewCurrentItem.value.file)" class="max-h-[300px] object-contain rounded">
                                    <video v-else-if="isVideo(playlists.previewCurrentItem.value.file)" :src="getFileUrl(playlists.previewCurrentItem.value.file)" autoplay controls class="max-h-[300px] rounded"></video>
                                </div>
                                <div class="absolute bottom-3 left-4 text-white text-xs bg-black/60 px-3 py-1 rounded">
                                    Слайд {{ playlists.previewIndex.value + 1 }} из {{ playlists.previewItems.value.length }} | Файл: {{ playlists.previewCurrentItem.value ? playlists.previewCurrentItem.value.file : '' }}
                                </div>
                            </div>
                            <div class="bg-gray-100 px-4 py-3 flex justify-between items-center">
                                <span class="text-xs text-gray-600">Эмуляция экрана вещания с учетом пауз и длительности</span>
                                <button @click="playlists.closePreview" class="bg-gray-300 hover:bg-gray-400 text-gray-800 text-xs px-4 py-2 rounded font-medium">Закрыть предпросмотр</button>
                            </div>
                        </div>
                    </div>

                    <div class="bg-emerald-50 border border-emerald-200 rounded-xl p-6 shadow-sm">
                        <div v-if="playlists.playlists.value.length === 0" class="text-center py-8 text-emerald-600 bg-white rounded-lg border border-dashed border-emerald-200">Плейлисты еще не созданы.</div>
                        <div v-else class="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div v-for="pl in playlists.playlists.value" :key="pl.id" class="bg-white border border-emerald-200 p-4 rounded-lg shadow-sm flex flex-col justify-between">
                                <div>
                                    <div class="flex justify-between items-start mb-2">
                                        <h3 class="font-bold text-emerald-900 text-base">{{ pl.name }}</h3>
                                        <span class="bg-emerald-100 text-emerald-800 text-[10px] px-2 py-0.5 rounded uppercase font-semibold">{{ pl.city }}</span>
                                    </div>
                                    <p class="text-xs text-emerald-700 mb-1">Пауза: {{ pl.interval }} сек | Повторов: {{ pl.repeats }}</p>
                                    <p class="text-xs font-semibold text-emerald-900 mt-2">Файлов в ряду: {{ pl.items.length }}</p>
                                    <ul class="text-[11px] text-slate-600 list-disc list-inside mt-1 max-h-20 overflow-y-auto">
                                        <li v-for="(it, i) in pl.items" :key="i">{{ it.file }} <span v-if="isImage(it.file)">({{ it.duration }}с)</span><span v-else>(видео)</span></li>
                                    </ul>
                                </div>
                                <div class="mt-4 pt-3 border-t border-emerald-100 flex justify-between items-center">
                                    <button @click="playlists.startPreview(pl)" class="bg-emerald-100 hover:bg-emerald-200 text-emerald-800 text-xs px-3 py-1.5 rounded font-medium transition">▶ Предпросмотр</button>
                                    <button v-if="auth.login.value === 'admin_main'" @click="requestConfirm($event, 'Удалить этот плейлист?', () => playlists.deletePlaylist(pl.id))" class="text-red-600 hover:text-red-800 text-xs font-medium">Удалить</button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Вкладка: Импорт файлов -->
                <div v-if="currentTab === 'import' && auth.login.value === 'admin_main'" class="space-y-6">
                    <div class="bg-emerald-50 border border-emerald-200 rounded-xl p-6 shadow-sm">
                        <h2 class="text-xl font-semibold mb-2 text-emerald-900">Импорт контента</h2>
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mt-6">
                            
                            <!-- Блок загрузки -->
                            <div class="space-y-4 bg-white p-5 rounded-lg border border-emerald-200 shadow-sm">
                                <h3 class="text-sm font-semibold text-emerald-900">Параметры</h3>
                                <div>
                                    <label class="block text-xs text-emerald-700 mb-1 font-medium">Целевой филиал:</label>
                                    <select v-model="media.selectedCity.value" class="w-full bg-white border border-emerald-300 text-sm rounded-lg p-2.5 focus:outline-none focus:border-emerald-600">
                                        <option value="global">Вся сеть (Все города)</option>
                                        <option value="moscow">Москва</option>
                                        <option value="spb">Санкт-Петербург</option>
                                        <option value="novocheboksarsk">Новочебоксарск</option>
                                        <option value="yartsevo">Ярцево</option>
                                        <option value="azov">Азов</option>
                                        <option value="orenburg">Оренбург</option>
                                        <option value="chernyakhovsk">Черняховск</option>
                                    </select>
                                </div>
                                <div>
                                    <label class="block text-xs text-emerald-700 mb-1 font-medium">Файл:</label>
                                    <input type="file" @change="media.handleFileSelect" class="block w-full text-xs text-emerald-800 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:bg-emerald-600 file:text-white cursor-pointer">
                                </div>
                                <div v-if="media.uploading.value" class="w-full bg-emerald-100 rounded-full h-2">
                                  <div class="bg-emerald-600 h-2 rounded-full transition-all duration-300" :style="{ width: media.uploadProgress.value + '%' }"></div>
                                </div>
                                <button @click="media.uploadFile" :disabled="!media.selectedFile.value || media.uploading.value" class="w-full bg-emerald-600 hover:bg-emerald-700 disabled:bg-emerald-300 text-white font-medium px-4 py-2.5 rounded-lg transition text-sm">
                                    {{ media.uploading.value ? `Загрузка... ${media.uploadProgress.value}%` : 'Начать импорт' }}
                                </button>
                                <p v-if="media.uploadError.value" class="text-red-600 text-xs mt-2">{{ media.uploadError.value }}</p>
                            </div>
                            
                            <!-- Журнал загрузки -->
                            <div class="bg-white p-5 rounded-lg border border-emerald-200 shadow-sm">
                                <h3 class="text-sm font-semibold text-emerald-900 mb-3">Журнал обработки</h3>
                                <div v-if="media.importLogs.value.length === 0" class="text-xs text-emerald-600 py-12 text-center border border-dashed border-emerald-200 rounded-lg">Отчет пуст.</div>
                                <div v-else class="space-y-2 max-h-64 overflow-y-auto">
                                    <div v-for="(log, idx) in media.importLogs.value" :key="idx" class="p-3 rounded text-xs border" :class="log.success ? 'bg-emerald-50 border-emerald-200 text-emerald-900' : 'bg-red-50 border-red-200 text-red-900'">
                                        <p class="font-semibold">{{ log.filename }} — <span>{{ log.success ? 'Успешно' : 'Ошибка' }}</span></p>
                                        <p class="mt-0.5">{{ log.text }}</p>
                                    </div>
                                </div>
                            </div>

                        </div>
                    </div>
                </div>

                <!-- Вкладка: Корзина -->
                <div v-if="currentTab === 'trash' && auth.login.value === 'admin_main'">
                    <div class="bg-emerald-50 border border-emerald-200 rounded-xl p-6 shadow-sm">
                        <div class="flex justify-between items-center mb-4">
                            <h2 class="text-xl font-semibold text-emerald-900">Корзина (хранение до 30 дней)</h2>
                            <button 
                                @click="media.trashFiles.value.length > 0 ? requestConfirm($event, 'Очистить корзину навсегда?', media.emptyTrash) : showToast('Корзина уже пуста!', 'info')" 
                                :class="media.trashFiles.value.length === 0 ? 'opacity-50 cursor-not-allowed' : 'hover:bg-red-200 cursor-pointer'" 
                                class="text-xs bg-red-100 text-red-800 px-4 py-2 rounded-md border border-red-200 font-bold transition">
                                🗑️ Очистить всё
                            </button>
                        </div>
                        <div v-if="media.trashFiles.value.length === 0" class="text-center py-12 text-emerald-600 border border-dashed border-emerald-200 rounded-lg bg-white">Корзина пуста.</div>
                        <div v-else class="space-y-3">
                            <div v-for="file in media.trashFiles.value" :key="file.name" class="bg-white border border-emerald-200 p-4 rounded-lg flex justify-between items-center shadow-sm">
                                <div>
                                    <p class="font-medium text-emerald-900 text-sm">{{ file.name }}</p>
                                    <p class="text-[11px] text-emerald-600 mt-0.5">
                                        Удалено: {{ formatDate(file.deleted_at) }} | 
                                        <span class="font-semibold text-amber-700">{{ getRemainingDays(file.deleted_at) }}</span>
                                    </p>
                                </div>
                                <button @click="media.restoreFile(file.name)" class="bg-emerald-600 hover:bg-emerald-700 text-white text-xs px-4 py-2 rounded-md shadow-sm">Восстановить</button>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Вкладка: РАСПИСАНИЯ -->
                <div v-if="currentTab === 'schedule'" class="space-y-6">
                    <div class="flex justify-between items-center">
                        <h2 class="text-xl font-semibold text-emerald-900">График трансляций (Smart Planner)</h2>
                        <button v-if="auth.login.value === 'admin_main'" @click="schedules.openScheduleModal" class="bg-emerald-600 text-white px-4 py-2 rounded-lg text-sm shadow-sm hover:bg-emerald-700 transition cursor-pointer border-0">+ Запланировать</button>
                    </div>

                    <div v-if="schedules.showAddModal.value" class="bg-emerald-50 border border-emerald-200 rounded-xl p-6 shadow-md">
                        <h3 class="text-lg font-medium mb-4 text-emerald-800">Новый запуск</h3>
                        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
                            
                            <div class="sm:col-span-2 flex gap-4 bg-white p-3 rounded-lg border border-emerald-200">
                                <label class="flex items-center gap-2 text-xs font-medium cursor-pointer">
                                    <input type="radio" value="file" v-model="schedules.scheduleType.value" @change="schedules.newSchedule.value.playlist_id = null" class="accent-emerald-600"> Отдельный файл
                                </label>
                                <label class="flex items-center gap-2 text-xs font-medium cursor-pointer">
                                    <input type="radio" value="playlist" v-model="schedules.scheduleType.value" @change="schedules.newSchedule.value.file = ''" class="accent-emerald-600"> Плейлист
                                </label>
                            </div>

                            <div class="sm:col-span-2">
                                <label class="block text-xs text-emerald-700 mb-1 font-medium">{{ schedules.scheduleType.value === 'file' ? 'Выберите файл' : 'Выберите плейлист' }}</label>
                                <select v-if="schedules.scheduleType.value === 'file'" v-model="schedules.newSchedule.value.file" class="w-full bg-white border border-emerald-300 rounded p-2.5 text-sm">
                                    <option v-for="f in media.files.value" :key="f.name" :value="f.name">{{ f.name }}</option>
                                </select>
                                <select v-else v-model="schedules.newSchedule.value.playlist_id" class="w-full bg-white border border-emerald-300 rounded p-2.5 text-sm">
                                    <option :value="null">-- Выберите плейлист --</option>
                                    <option v-for="pl in playlists.playlists.value" :key="pl.id" :value="pl.id">📑 {{ pl.name }}</option>
                                </select>
                            </div>

                            <div class="sm:col-span-2">
                                <label class="block text-xs text-emerald-700 mb-1 font-medium">Филиал (Город)</label>
                                <select v-model="schedules.newSchedule.value.city" @change="handleCityChange" class="w-full bg-white border border-emerald-300 rounded p-2.5 text-sm">
                                    <option value="global">Вся сеть</option>
                                    <option value="moscow">Москва</option>
                                    <option value="spb">Санкт-Петербург</option>
                                    <option value="novocheboksarsk">Новочебоксарск</option>
                                    <option value="yartsevo">Ярцево</option>
                                    <option value="azov">Азов</option>
                                    <option value="orenburg">Оренбург</option>
                                    <option value="chernyakhovsk">Черняховск</option>
                                </select>
                            </div>

                            <!-- БЛОК ВЫБОРА ЦЕЛЕВЫХ ЭКРАНОВ -->
                            <div v-if="schedules.newSchedule.value.city && schedules.newSchedule.value.city !== 'global' && currentScreens.length > 0" class="sm:col-span-2 bg-emerald-100/50 p-4 rounded-lg border border-emerald-200">
                                <div class="flex justify-between items-center mb-2">
                                    <label class="block text-xs font-semibold text-emerald-800">Целевые экраны:</label>
                                    <button type="button" @click="toggleSelectAllScreens" class="text-xs text-emerald-600 hover:text-emerald-800 underline bg-transparent border-0 cursor-pointer font-medium">Выбрать все / Снять</button>
                                </div>
                                <div class="flex flex-wrap gap-2.5 mt-1">
                                    <label v-for="scr in currentScreens" :key="scr" class="flex items-center gap-2 text-xs bg-white px-3 py-2 rounded-md border border-emerald-200 cursor-pointer hover:border-emerald-400 select-none shadow-sm transition">
                                        <input type="checkbox" :value="scr" v-model="schedules.newSchedule.value.screens" class="accent-emerald-600 w-3.5 h-3.5 rounded">
                                        <span class="font-medium text-emerald-950">{{ scr }}</span>
                                    </label>
                                </div>
                            </div>
                            
                            <div>
                                <label class="block text-xs text-emerald-700 mb-1 font-medium">Время начала</label>
                                <input id="time_start_picker" type="text" placeholder="Выберите дату и время" class="w-full bg-white border border-emerald-300 rounded p-2 text-sm cursor-pointer">
                            </div>
                            <div>
                                <label class="block text-xs text-emerald-700 mb-1 font-medium">Время окончания</label>
                                <input id="time_end_picker" type="text" placeholder="Выберите дату и время" class="w-full bg-white border border-emerald-300 rounded p-2 text-sm cursor-pointer">
                            </div>
                        </div>
                        <div class="flex justify-end gap-3 pt-2">
                            <button @click="schedules.showAddModal.value = false" class="bg-emerald-200 text-emerald-900 px-4 py-2 rounded text-sm hover:bg-emerald-300 transition">Отмена</button>
                            <button @click="schedules.addSchedule($event)" class="bg-emerald-600 text-white px-4 py-2 rounded text-sm hover:bg-emerald-700 transition">Сохранить</button>
                        </div>
                    </div>
                    
                    <div class="bg-emerald-50 border border-emerald-200 rounded-xl p-6 shadow-sm overflow-x-auto">
                        <table v-if="schedules.schedules.value.length > 0" class="w-full text-sm text-left text-emerald-900">
                            <thead class="text-xs text-emerald-800 uppercase bg-emerald-100/70 border-b border-emerald-200">
                                <tr>
                                    <th class="px-6 py-3">Контент</th>
                                    <th class="px-6 py-3">Филиал / Экраны</th>
                                    <th class="px-6 py-3">Время (Местное)</th>
                                    <th class="px-6 py-3">Статус</th>
                                    <th v-if="auth.login.value === 'admin_main'" class="px-6 py-3">Действия</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr v-for="item in schedules.schedules.value" :key="item.id" class="border-b border-emerald-200 hover:bg-emerald-100/40 transition">
                                    <td class="px-6 py-4 font-medium">
                                        <span v-if="item.playlist_id" class="text-emerald-700 font-bold flex items-center gap-1">
                                            📑 Плейлист: {{ getPlaylistName(item.playlist_id) }}
                                        </span>
                                        <span v-else>
                                            📁 {{ item.file }}
                                        </span>
                                    </td>
                                    <td class="px-6 py-4 text-xs">
                                        <span class="font-bold text-emerald-800 uppercase">{{ item.city }}</span><br>
                                        <span class="text-[10px] text-slate-500 font-normal lowercase">{{ !item.screens || item.screens.length === 0 ? 'Все экраны' : item.screens.join(', ') }}</span>
                                    </td>
                                    <td class="px-6 py-4 text-[11px] leading-tight">
                                        С: {{ item.time_start.replace('T', ' ') }}<br>
                                        По: {{ item.time_end.replace('T', ' ') }}
                                    </td>
                                    <td class="px-6 py-4">
                                        <span class="px-2.5 py-1 rounded text-xs font-medium" :class="{
                                            'bg-emerald-300 text-emerald-800': item.status === 'Активен', 
                                            'bg-amber-200 text-amber-800': item.status === 'Ожидание', 
                                            'bg-slate-200 text-slate-600': item.status === 'Завершен'
                                        }">
                                            {{ item.status }}
                                        </span>
                                    </td>
                                    <td v-if="auth.login.value === 'admin_main'" class="px-6 py-4">
                                        <button @click="requestConfirm($event, 'Удалить из расписания?', () => schedules.deleteSchedule(item.id))" class="text-red-700 text-xs hover:underline bg-transparent border-0 cursor-pointer">Удалить</button>
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                        <div v-else class="text-center py-8 text-emerald-600 bg-white rounded-lg border border-dashed border-emerald-200">Расписание пока пусто.</div>
                    </div>
                </div>

                <!-- ВКЛАДКА МОНИТОРИНГ (С ПЛЕЕРОМ ТРАНСЛЯЦИЙ - ЭТАП 9) -->
                <div v-if="currentTab === 'monitoring'">
                    <div class="space-y-6">
                        
                        <!-- Блок 1: Статусы сети -->
                        <div class="bg-emerald-50 border border-emerald-200 rounded-xl p-6 shadow-sm">
                            <div class="flex justify-between items-center mb-6">
                                <h2 class="text-xl font-semibold text-emerald-900">Мониторинг сети экранов</h2>
                                <button @click="reports.fetchMonitoring" class="text-xs bg-emerald-200 hover:bg-emerald-300 text-emerald-900 px-3 py-1.5 rounded-md font-medium transition cursor-pointer border-0">Обновить статус</button>
                            </div>
                            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                                <div v-for="sc in reports.monitoringData.value" :key="sc.screen" class="bg-white border border-emerald-200 p-4 rounded-lg flex items-center justify-between shadow-sm">
                                    <div>
                                        <p class="font-medium text-sm text-emerald-900">{{ sc.screen }}</p>
                                        <p class="text-[11px] text-emerald-600 mt-1 uppercase tracking-wide">{{ sc.city }}</p>
                                    </div>
                                    <div class="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border" :class="sc.status === 'В сети' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-red-50 text-red-700 border-red-200'">
                                        <span class="w-2 h-2 rounded-full" :class="sc.status === 'В сети' ? 'bg-emerald-500' : 'bg-red-500'"></span>
                                        {{ sc.status }}
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- Блок 2: Плеер трансляций (Эмуляция эфира) -->
                        <div class="bg-emerald-50 border border-emerald-200 rounded-xl p-6 shadow-sm">
                            <h2 class="text-xl font-semibold text-emerald-900 mb-4">Плеер трансляций (Эфир экранов)</h2>
                            
                            <div class="flex flex-col md:flex-row gap-4 mb-6">
                                <div class="flex-1">
                                    <label class="block text-xs font-semibold text-emerald-800 mb-1">Город</label>
                                    <select v-model="monitorSelectedCity" @change="handleMonitorCityChange" class="w-full bg-white border border-emerald-300 rounded p-2.5 text-sm focus:outline-none focus:border-emerald-600">
                                        <option value="moscow">Москва</option>
                                        <option value="spb">Санкт-Петербург</option>
                                        <option value="novocheboksarsk">Новочебоксарск</option>
                                        <option value="yartsevo">Ярцево</option>
                                        <option value="azov">Азов</option>
                                        <option value="orenburg">Оренбург</option>
                                        <option value="chernyakhovsk">Черняховск</option>
                                    </select>
                                </div>
                                <div class="flex-1">
                                    <label class="block text-xs font-semibold text-emerald-800 mb-1">Экран</label>
                                    <select v-model="monitorSelectedScreen" class="w-full bg-white border border-emerald-300 rounded p-2.5 text-sm focus:outline-none focus:border-emerald-600">
                                        <option v-for="scr in (schedules.allScreensMap?.value?.[monitorSelectedCity] || fallbackScreens[monitorSelectedCity] || [])" :key="scr" :value="scr">{{ scr }}</option>
                                    </select>
                                </div>
                            </div>

                            <div class="bg-black rounded-xl overflow-hidden aspect-video relative flex flex-col items-center justify-center border-4 border-emerald-900 shadow-inner">
                                <div v-if="!activeMonitorSchedule" class="text-emerald-500 flex flex-col items-center gap-3">
                                    <span class="text-5xl opacity-50">⏸</span>
                                    <span class="text-sm font-medium tracking-wide">Нет активной трансляции</span>
                                </div>
                                <div v-else class="w-full h-full relative group">
                                    
                                    <div class="absolute inset-0 flex items-center justify-center z-0">
                                        <div v-if="activeMonitorSchedule.playlist_id" class="text-white text-center">
                                            <span class="text-6xl block mb-4">📑</span>
                                            <span class="text-xl font-bold">Воспроизведение плейлиста</span>
                                            <p class="text-emerald-400 mt-2">{{ getPlaylistName(activeMonitorSchedule.playlist_id) }}</p>
                                            <button @click="playlists.startPreview(playlists.playlists.value.find(p => p.id === activeMonitorSchedule.playlist_id))" class="mt-4 bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2 rounded text-sm transition shadow border-0 cursor-pointer">Запустить эмулятор плейлиста</button>
                                        </div>
                                        <div v-else class="w-full h-full">
                                            <img v-if="isImage(activeMonitorSchedule.file)" :src="getFileUrl(activeMonitorSchedule.file)" class="w-full h-full object-contain bg-black">
                                            <video v-else-if="isVideo(activeMonitorSchedule.file)" :src="getFileUrl(activeMonitorSchedule.file)" autoplay loop muted class="w-full h-full object-contain bg-black"></video>
                                            <div v-else class="text-white text-center mt-20">
                                                <span class="text-6xl block mb-4">📁</span>
                                                <span class="text-xl font-bold">{{ activeMonitorSchedule.file }}</span>
                                            </div>
                                        </div>
                                    </div>
                                    
                                    <div class="absolute top-4 left-4 bg-black/70 backdrop-blur-md px-3 py-1.5 rounded-lg border border-white/10 flex items-center gap-2">
                                        <div class="w-2 h-2 rounded-full bg-red-500 animate-pulse"></div>
                                        <span class="text-white text-xs font-semibold tracking-wider">LIVE эфир</span>
                                    </div>
                                    <div class="absolute bottom-0 inset-x-0 bg-gradient-to-t from-black/80 to-transparent p-4 pt-12 pointer-events-none">
                                        <p class="text-white font-bold text-lg drop-shadow-md">{{ monitorSelectedCity.toUpperCase() }} / {{ monitorSelectedScreen }}</p>
                                        <p class="text-emerald-300 text-xs drop-shadow-md mt-1">Трансляция ID: {{ activeMonitorSchedule.id }}</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- ВКЛАДКА ОТЧЕТЫ -->
                <div v-if="currentTab === 'reports' && auth.login.value === 'admin_main'">
                    <div class="space-y-6">
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                            <div class="bg-emerald-50 border border-emerald-200 rounded-xl p-6 shadow-sm flex flex-col justify-center items-center">
                                <h3 class="text-emerald-700 text-sm font-semibold uppercase tracking-wide">Запланировано показов</h3>
                                <p class="text-5xl font-bold text-emerald-900 mt-2">{{ reports.analyticsData.value.total_shows }}</p>
                            </div>
                            <div class="bg-emerald-50 border border-emerald-200 rounded-xl p-6 shadow-sm flex flex-col justify-center items-center">
                                <h3 class="text-emerald-700 text-sm font-semibold uppercase tracking-wide">Суммарное время (часы)</h3>
                                <p class="text-5xl font-bold text-emerald-900 mt-2">{{ reports.analyticsData.value.total_hours }}</p>
                            </div>
                        </div>
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                            <div class="bg-white border border-emerald-200 rounded-xl p-6 shadow-sm">
                                <h3 class="text-emerald-900 font-semibold mb-4 text-center">Статусы трансляций</h3>
                                <div class="relative h-64">
                                    <canvas ref="chartStatusRef"></canvas>
                                </div>
                            </div>
                            <div class="bg-white border border-emerald-200 rounded-xl p-6 shadow-sm">
                                <h3 class="text-emerald-900 font-semibold mb-4 text-center">Трансляции по филиалам</h3>
                                <div class="relative h-64">
                                    <canvas ref="chartCityRef"></canvas>
                                </div>
                            </div>
                        </div>

                        <!-- Системный журнал событий -->
                        <div class="bg-white border border-emerald-200 rounded-xl p-6 shadow-sm">
                            <div class="flex justify-between items-center mb-4">
                                <div>
                                    <h3 class="text-emerald-900 font-semibold">Системный журнал событий</h3>
                                    <p class="text-xs text-emerald-600 mt-0.5">Фиксация действий пользователей, системы и операций с файлами</p>
                                </div>
                                <button @click="reports.fetchHistory" class="text-xs bg-emerald-100 hover:bg-emerald-200 text-emerald-800 px-3 py-1.5 rounded-md font-medium transition cursor-pointer border-0">Обновить журнал</button>
                            </div>
                            <div class="overflow-x-auto max-h-96 overflow-y-auto border border-emerald-100 rounded-lg">
                                <table class="w-full text-sm text-left text-emerald-900">
                                    <thead class="text-xs text-emerald-800 uppercase bg-emerald-50 sticky top-0 shadow-sm z-10">
                                        <tr>
                                            <th class="px-4 py-3">Время</th>
                                            <th class="px-4 py-3">Пользователь</th>
                                            <th class="px-4 py-3">Действие</th>
                                            <th class="px-4 py-3">Детали события</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        <tr v-if="reports.activityHistory.value.length === 0">
                                            <td colspan="4" class="px-4 py-8 text-center text-emerald-600">Журнал событий пуст</td>
                                        </tr>
                                        <tr v-for="log in reports.activityHistory.value" :key="log.id" class="border-b border-emerald-50 hover:bg-emerald-50/50 text-xs transition">
                                            <td class="px-4 py-3 text-slate-500 whitespace-nowrap">{{ formatDate(log.timestamp, true) }}</td>
                                            <td class="px-4 py-3 font-semibold text-emerald-900">{{ log.username }}</td>
                                            <td class="px-4 py-3 font-medium text-emerald-700">
                                                <span class="bg-emerald-100 text-emerald-900 px-2 py-0.5 rounded text-[11px]">{{ log.action }}</span>
                                            </td>
                                            <td class="px-4 py-3 text-slate-600">{{ log.details }}</td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>
                        </div>

                        <!-- История хранилища -->
                        <div class="bg-white border border-emerald-200 rounded-xl p-6 shadow-sm mt-6">
                            <div class="flex justify-between items-center mb-4">
                                <h3 class="text-emerald-900 font-semibold">История содержимого в хранилище</h3>
                                <button @click="reports.fetchStorageHistory" class="text-xs bg-emerald-100 hover:bg-emerald-200 text-emerald-800 px-3 py-1.5 rounded-md font-medium transition cursor-pointer border-0">Обновить</button>
                            </div>
                            <div class="overflow-x-auto max-h-96 overflow-y-auto border border-emerald-100 rounded-lg">
                                <table class="w-full text-sm text-left text-emerald-900">
                                    <thead class="text-xs text-emerald-800 uppercase bg-emerald-50 sticky top-0 shadow-sm z-10">
                                        <tr>
                                            <th class="px-4 py-3">Время</th>
                                            <th class="px-4 py-3">Файл / Путь</th>
                                            <th class="px-4 py-3">Операция</th>
                                            <th class="px-4 py-3">Размер</th>
                                            <th class="px-4 py-3">Пользователь</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        <tr v-if="reports.storageHistory.value.length === 0">
                                            <td colspan="5" class="px-4 py-8 text-center text-emerald-600">История хранилища пуста</td>
                                        </tr>
                                        <tr v-for="item in reports.storageHistory.value" :key="item.id" class="border-b border-emerald-50 hover:bg-emerald-50/50 text-xs transition">
                                            <td class="px-4 py-3 text-slate-500 whitespace-nowrap">{{ formatDate(item.timestamp, true) }}</td>
                                            <td class="px-4 py-3 font-medium text-emerald-950">{{ item.filename }}</td>
                                            <td class="px-4 py-3 font-bold" :class="{
                                                'text-emerald-700': item.operation === 'ЗАГРУЗКА',
                                                'text-amber-700': item.operation === 'В КОРЗИНУ' || item.operation === 'ВОССТАНОВЛЕНИЕ',
                                                'text-red-700': item.operation === 'УДАЛЕНО НАВСЕГДА'
                                            }">{{ item.operation }}</td>
                                            <td class="px-4 py-3 text-slate-600">{{ formatSize(item.size) }}</td>
                                            <td class="px-4 py-3 font-semibold">{{ item.username }}</td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>
                        </div>

                    </div>
                </div>

            </main>
        </template>
        
        <!-- Всплывающий диалог подтверждения -->
        <div v-if="confirmDialog.show" class="fixed inset-0 z-[100]" @click="confirmDialog.show = false"></div>
        <transition 
            enter-active-class="transition duration-200 ease-out origin-bottom" enter-from-class="opacity-0 scale-90" enter-to-class="opacity-100 scale-100"
            leave-active-class="transition duration-150 ease-in origin-bottom" leave-from-class="opacity-100 scale-100" leave-to-class="opacity-0 scale-90">
            <div v-if="confirmDialog.show" :style="{ top: confirmDialog.y + 'px', left: confirmDialog.x + 'px' }" class="fixed z-[101] transform -translate-x-1/2" :class="confirmDialog.isBelow ? 'mt-[10px]' : '-translate-y-full mt-[-10px]'">
                <div class="bg-white border border-emerald-300 shadow-2xl rounded-xl p-4 w-64 relative">
                    <div class="absolute left-1/2 transform -translate-x-1/2 w-4 h-4 bg-white border-emerald-300 rotate-45" :class="confirmDialog.isBelow ? '-top-2 border-t border-l' : '-bottom-2 border-b border-r'"></div>
                    <p class="text-sm font-medium text-emerald-900 text-center mb-4 relative z-10">{{ confirmDialog.text }}</p>
                    <div class="flex justify-center gap-3 relative z-10">
                        <button @click.stop="confirmDialog.onConfirm(); confirmDialog.show = false" class="bg-emerald-600 hover:bg-emerald-700 text-white text-xs px-5 py-2 rounded-md font-medium transition shadow-sm border-0 cursor-pointer">Да</button>
                        <button @click.stop="confirmDialog.show = false" class="bg-red-50 hover:bg-red-100 text-red-700 text-xs px-5 py-2 rounded-md font-medium border border-red-200 transition cursor-pointer">Нет</button>
                    </div>
                </div>
            </div>
        </transition>

    </div>
</div>
</template>