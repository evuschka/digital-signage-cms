<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';
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

// Инициализация модулей
const auth = useAuth();
const users = useUsers(auth.authHeader, showToast, safeJson);
const media = useMedia(auth.authHeader, auth.login, showToast, safeJson);
const playlists = usePlaylists(auth.authHeader, showToast, isImage, isVideo, safeJson, () => media.files.value);
const schedules = useSchedules(auth.authHeader, showToast, requestConfirm, safeJson);
const reports = useReports(auth.authHeader, showToast, safeJson);

const { chartStatusRef, chartCityRef } = reports;
const currentTab = ref(''); 

// ==========================================
// ЛОГИКА АРХИВА РАСПИСАНИЙ
// ==========================================
const showArchive = ref(false);

const isScheduleArchived = (schedule) => {
    if (schedule.status !== 'Завершен') return false;
    try {
        const endDate = new Date(schedule.time_end);
        const now = new Date();
        const diffDays = Math.floor((now - endDate) / (1000 * 60 * 60 * 24));
        return diffDays >= 5;
    } catch (e) {
        return false;
    }
};

const displaySchedules = computed(() => {
    const list = schedules.schedules?.value || [];
    if (showArchive.value) {
        return list.filter(s => isScheduleArchived(s));
    } else {
        return list.filter(s => !isScheduleArchived(s));
    }
});

// ==========================================
// ЛОГИКА ФОНОВОЙ ЗАГЛУШКИ (ИЗОЛИРОВАННАЯ ЗАГРУЗКА)
// ==========================================
const fallbackFile = ref('');
const fallbackFileInput = ref(null);
const isFallbackUploading = ref(false);
const fallbackUploadProgress = ref(0);

const fetchFallback = async () => {
    try {
        const res = await fetch('/settings/fallback');
        const data = await safeJson(res);
        if (data.file) fallbackFile.value = data.file;
    } catch (e) {}
};

const uploadFallback = () => {
    const input = fallbackFileInput.value;
    if (!input || !input.files || input.files.length === 0) {
        showToast('Выберите файл для загрузки', 'warning');
        return;
    }
    
    const file = input.files[0];
    const formData = new FormData();
    formData.append('file', file);
    
    isFallbackUploading.value = true;
    fallbackUploadProgress.value = 0;
    
    const xhr = new XMLHttpRequest();
    xhr.open('POST', '/settings/fallback/upload', true);
    xhr.setRequestHeader('Authorization', auth.authHeader.value);
    
    xhr.upload.onprogress = (e) => {
        if (e.lengthComputable) {
            fallbackUploadProgress.value = Math.round((e.loaded / e.total) * 100);
        }
    };
    
    xhr.onload = () => {
        isFallbackUploading.value = false;
        if (xhr.status === 200) {
            const res = JSON.parse(xhr.responseText);
            fallbackFile.value = res.file;
            showToast('Заглушка успешно загружена и применена', 'success');
            input.value = ''; 
            media.fetchStats(); 
        } else {
            showToast('Ошибка загрузки', 'error');
        }
    };
    
    xhr.onerror = () => {
        isFallbackUploading.value = false;
        showToast('Сетевая ошибка при загрузке', 'error');
    };
    
    xhr.send(formData);
};

const clearFallback = async () => {
    try {
        const res = await fetch('/settings/fallback', {
            method: 'POST',
            headers: { 'Authorization': auth.authHeader.value, 'Content-Type': 'application/json' },
            body: JSON.stringify({ file: '' })
        });
        if (res.ok) {
            fallbackFile.value = '';
            showToast('Заглушка очищена. Теперь будет черный экран.', 'info');
        }
    } catch (e) {
        showToast('Ошибка', 'error');
    }
};

// ==========================================
// ЛОГИКА ДОСТУПА ПО QR-КОДУ (РЕЖИМ ЗРИТЕЛЯ)
// ==========================================
const urlParams = new URLSearchParams(window.location.search);
const viewerId = urlParams.get('viewer_id');
const viewerHash = urlParams.get('hash');
const isMobileViewer = ref(!!viewerId);

const mobileData = ref(null);
const mobileError = ref('');
const mobileIndex = ref(0);
let mobileTimer = null;
const isMuted = ref(true);

const loadMobileViewer = async () => {
    try {
        const res = await fetch(`/public-broadcast/${viewerId}?hash=${encodeURIComponent(viewerHash)}`);
        if (!res.ok) {
            const err = await safeJson(res);
            mobileError.value = err.detail || 'Доступ запрещен';
            return;
        }
        mobileData.value = await safeJson(res);
        playMobileItem();
    } catch (e) {
        mobileError.value = 'Ошибка подключения к эфиру';
    }
};

const playMobileItem = () => {
    if (!mobileData.value || !mobileData.value.items.length) return;
    const item = mobileData.value.items[mobileIndex.value];
    if (isImage(item.file)) {
        mobileTimer = setTimeout(nextMobileItem, (item.duration || 10) * 1000);
    }
};

const nextMobileItem = () => {
    mobileIndex.value = (mobileIndex.value + 1) % mobileData.value.items.length;
    playMobileItem();
};

const showQrModal = ref(false);
const currentQrUrl = ref('');

const openQr = async (schedule) => {
    const hash = btoa(`signage_${schedule.id}_secure`); 
    let host = window.location.hostname;
    
    if (host === 'localhost' || host === '127.0.0.1') {
        let guessedIp = host;
        try {
            const res = await fetch('/server-ip/', { headers: { 'Authorization': auth.authHeader.value } });
            if (res.ok) {
                const data = await res.json();
                if (data.ip && data.ip !== '127.0.0.1') {
                    guessedIp = data.ip; 
                }
            }
        } catch (e) {
            console.error("Не удалось получить сетевой IP сервера", e);
        }
        
        const userIp = prompt("Подтвердите IP-адрес для зрителей (Wi-Fi):", guessedIp === '172.19.0.1' ? '172.20.10.4' : guessedIp);
        
        if (userIp) {
            host = userIp.trim(); 
        } else {
            return; 
        }
    }
    
    const port = window.location.port ? `:${window.location.port}` : '';
    const baseUrl = `${window.location.protocol}//${host}${port}`; 
    
    currentQrUrl.value = `${baseUrl}/?viewer_id=${schedule.id}&hash=${hash}`;
    showQrModal.value = true;
};

// Функция загрузки всех данных
const loadAllData = async () => {
    if (auth.login.value === 'admin_main') {
        await users.fetchAdminUsers();
        if (users.adminRequests.value.length > 0) auth.showAdminAlertModal.value = true;
        reports.fetchMonitoring();
    }
    media.fetchFiles(); 
    media.fetchStats(); 
    playlists.fetchPlaylists(); 
    schedules.fetchScreens(); 
    schedules.fetchSchedules();
    fetchFallback();
    if (auth.login.value === 'admin_main') media.fetchTrash();
};

// Загрузка при старте
let clockInterval = null;
onMounted(async () => {
    if (isMobileViewer.value) {
        await loadMobileViewer();
        return; 
    }
    if (auth.isAuthenticated.value) {
        currentTab.value = auth.login.value === 'admin_main' ? 'media' : 'broadcasts';
        await loadAllData();
    }
    if (clockInterval) clearInterval(clockInterval);
    clockInterval = setInterval(updateLocalClock, 1000);
});
onUnmounted(() => { if (clockInterval) clearInterval(clockInterval); });

// ОБРАБОТКА ВХОДА
const authenticate = async () => {
    const success = await auth.doLogin();
    if (success) {
        try { await fetch('/log-login/', { method: 'POST', headers: { 'Authorization': auth.authHeader.value } }); } 
        catch (e) { console.error("Ошибка записи лога", e); }
        currentTab.value = auth.login.value === 'admin_main' ? 'media' : 'broadcasts';
        await loadAllData();
    }
};

// ОБРАБОТКА ВЫХОДА
const logoutHandler = async () => {
    if (auth.isAuthenticated.value) {
        try { await fetch('/log-logout/', { method: 'POST', headers: { 'Authorization': auth.authHeader.value } }); } 
        catch (e) { console.error("Ошибка записи лога", e); }
    }
    auth.doLogout();
    media.files.value = []; media.trashFiles.value = [];
    schedules.schedules.value = []; playlists.playlists.value = [];
    currentTab.value = ''; auth.showAdminAlertModal.value = false;
};

// Переключение вкладок
const switchTab = (tab) => {
    currentTab.value = tab;
    if (tab === 'reports') { reports.fetchAnalytics(); reports.fetchHistory(); reports.fetchStorageHistory(); }
    if (tab === 'users') users.fetchAdminUsers();
    if (tab === 'broadcasts') schedules.fetchSchedules();
};

const getPlaylistName = (id) => {
    const list = playlists.playlists.value || [];
    const pl = list.find(p => String(p.id) === String(id));
    return pl ? pl.name : 'Неизвестный';
};

const getFileUrl = (fileName) => {
    if (!fileName) return '';
    const list = media.files?.value || [];
    const fileObj = list.find(f => f.name === fileName);
    if (fileObj && fileObj.url) return fileObj.url;
    const parts = fileName.split('/');
    return `/media-file/${parts.map(p => encodeURIComponent(p)).join('/')}`;
};

// ==========================================
// ЛОГИКА ЖИВОГО ПЛЕЕРА ДЛЯ ТРАНСЛЯЦИЙ (FULLSCREEN)
// ==========================================
const activeLiveBroadcast = ref(null);
const liveItems = ref([]);
const liveIndex = ref(0);
let liveTimer = null;

const startLiveBroadcast = (schedule) => {
    activeLiveBroadcast.value = schedule;
    liveIndex.value = 0;
    if (schedule.playlist_id) {
        const pl = playlists.playlists.value.find(p => String(p.id) === String(schedule.playlist_id));
        liveItems.value = pl && pl.items ? pl.items : [];
    } else {
        liveItems.value = [{ file: schedule.file, duration: 10 }];
    }
    if(liveItems.value.length > 0) playLiveItem();
    else { showToast("Нет файлов", "error"); stopLiveBroadcast(); }
};

const playLiveItem = () => {
    if (!activeLiveBroadcast.value || liveItems.value.length === 0) return;
    const item = liveItems.value[liveIndex.value];
    if (!item) return;
    if (isImage(item.file)) liveTimer = setTimeout(nextLiveItem, (item.duration || 10) * 1000);
};

const nextLiveItem = () => {
    if (!activeLiveBroadcast.value) return;
    liveIndex.value = (liveIndex.value + 1) % liveItems.value.length;
    playLiveItem();
};

const stopLiveBroadcast = () => {
    activeLiveBroadcast.value = null; liveItems.value = [];
    if (liveTimer) clearTimeout(liveTimer);
};


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
// ЛОГИКА ЦЕЛЕВЫХ ЭКРАНОВ И ВРЕМЕНИ
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
    if (Object.keys(apiMap).length > 0 && apiMap[city]) return apiMap[city];
    return fallbackScreens[city] || [];
});

const toggleSelectAllScreens = () => {
    const screens = currentScreens.value;
    if (!screens.length) return;
    if (schedules.newSchedule.value.screens.length === screens.length) schedules.newSchedule.value.screens = []; 
    else schedules.newSchedule.value.screens = [...screens]; 
};

const handleCityChange = () => {
    schedules.newSchedule.value.screens = []; 
    updateLocalClock();
    if (schedules.onCityChange) schedules.onCityChange();
};

const cityTimezones = {
    global: { label: 'МСК', offset: 3 },
    moscow: { label: 'МСК', offset: 3 },
    spb: { label: 'МСК', offset: 3 },
    novocheboksarsk: { label: 'МСК', offset: 3 },
    yartsevo: { label: 'МСК', offset: 3 },
    azov: { label: 'МСК', offset: 3 },
    orenburg: { label: 'МСК+2', offset: 5 },
    chernyakhovsk: { label: 'МСК-1', offset: 2 }
};

const localCityTimeDisplay = ref('');
const updateLocalClock = () => {
    if (!schedules.showAddModal.value) return; 
    const selectedCity = schedules.newSchedule.value.city || 'global';
    const selectedOffset = cityTimezones[selectedCity]?.offset || 3;
    const now = new Date();
    const utcTime = now.getTime() + (now.getTimezoneOffset() * 60000);
    const cityDate = new Date(utcTime + (3600000 * selectedOffset));
    localCityTimeDisplay.value = cityDate.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
};

// ==========================================
// ЛОГИКА ПЛЕЕРА ТРАНСЛЯЦИЙ ДЛЯ АДМИНА (МОНИТОРИНГ)
// ==========================================
const monitorSelectedCity = ref('moscow');
const monitorSelectedScreen = ref('Москва-Экран-1');

const handleMonitorCityChange = () => {
    const apiMap = schedules.allScreensMap?.value || {};
    const screens = apiMap[monitorSelectedCity.value] || fallbackScreens[monitorSelectedCity.value] || [];
    monitorSelectedScreen.value = screens.length > 0 ? screens[0] : '';
};

// Встроенная логика Фоновой заглушки
const activeMonitorSchedule = computed(() => {
    if (!monitorSelectedCity.value || !monitorSelectedScreen.value) return null;
    const list = schedules.schedules?.value || [];
    const active = list.find(s => {
        if (s.status !== 'Активен') return false;
        if (s.city !== 'global' && s.city !== monitorSelectedCity.value) return false;
        if (s.screens && s.screens.length > 0) {
            if (!s.screens.includes(monitorSelectedScreen.value)) return false;
        }
        return true;
    });
    
    if (active) return active;
    
    if (fallbackFile.value) {
        return { id: 'ЗАГЛУШКА', file: fallbackFile.value, is_fallback: true };
    }
    
    return null;
});
</script>

<template>
<div class="bg-white text-emerald-950 min-h-screen flex flex-col font-sans">
    
    <!-- РЕЖИМ МОБИЛЬНОГО ЗРИТЕЛЯ (ОТКРЫТИЕ ПО QR-КОДУ) -->
    <div v-if="isMobileViewer" class="h-screen w-screen bg-black flex flex-col items-center justify-center text-white fixed inset-0 z-[99999]">
        <div v-if="mobileError" class="text-red-500 flex flex-col items-center gap-4 text-center px-6">
            <span class="text-6xl">🔒</span>
            <h2 class="text-xl font-bold">{{ mobileError }}</h2>
            <p class="text-sm text-gray-400">Попробуйте отсканировать код заново.</p>
        </div>
        <div v-else-if="!mobileData" class="animate-pulse text-emerald-400 flex flex-col items-center gap-3">
            <span class="text-4xl animate-spin">⏳</span>
            Подключение к эфиру...
        </div>
        <div v-else class="w-full h-full relative flex items-center justify-center" @click="isMuted = false">
            <video v-if="isVideo(mobileData.items[mobileIndex].file)" 
                   :src="getFileUrl(mobileData.items[mobileIndex].file)" 
                   autoplay :muted="isMuted" playsinline class="w-full h-full object-contain" 
                   @ended="nextMobileItem"></video>
                   
            <img v-else 
                 :src="getFileUrl(mobileData.items[mobileIndex].file)" 
                 class="w-full h-full object-contain">
                 
            <div v-if="isVideo(mobileData.items[mobileIndex].file) && isMuted" 
                 class="absolute bottom-16 bg-white/20 backdrop-blur-md px-5 py-3 rounded-full text-white text-xs font-bold tracking-wide border border-white/30 animate-bounce shadow-lg">
                👆 Коснитесь экрана, чтобы включить звук
            </div>
                 
            <div class="absolute top-4 left-4 bg-black/60 px-3 py-1 rounded-full text-[10px] uppercase font-bold flex items-center gap-2 tracking-widest backdrop-blur-md border border-white/10 pointer-events-none">
                <span class="w-2 h-2 rounded-full bg-red-500 animate-pulse shadow-[0_0_8px_rgba(239,68,68,1)]"></span>
                Прямой эфир
            </div>
        </div>
    </div>
    
    <!-- СТАНДАРТНАЯ СИСТЕМА УПРАВЛЕНИЯ (СКРЫВАЕТСЯ ДЛЯ ЗРИТЕЛЕЙ) -->
    <template v-else>
        
        <!-- ПОЛНОЭКРАННЫЙ ЖИВОЙ ПЛЕЕР ДЛЯ ТРАНСЛЯЦИЙ -->
        <div v-if="activeLiveBroadcast" class="fixed inset-0 z-[10000] bg-black flex flex-col justify-center items-center">
            <button @click="stopLiveBroadcast" class="absolute top-6 right-6 z-[10001] bg-white/10 hover:bg-red-600 text-white border border-white/20 rounded-lg px-6 py-3 font-bold opacity-0 hover:opacity-100 transition-all duration-300 cursor-pointer shadow-2xl backdrop-blur-md uppercase tracking-wider">
                ✖ Закрыть трансляцию
            </button>
            <video v-if="liveItems.length > 0 && isVideo(liveItems[liveIndex].file)" 
                   :src="getFileUrl(liveItems[liveIndex].file)" 
                   autoplay muted class="w-full h-full object-contain" 
                   @ended="nextLiveItem"></video>
            <img v-else-if="liveItems.length > 0 && isImage(liveItems[liveIndex].file)" 
                 :src="getFileUrl(liveItems[liveIndex].file)" 
                 class="w-full h-full object-contain">
        </div>

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
                    <input v-model="auth.login.value" type="text" placeholder="Логин (например, user_msk)" class="w-full mb-4 px-4 py-2 bg-white text-emerald-950 border border-emerald-300 rounded focus:outline-none focus:border-emerald-600 text-sm">
                    <input v-model="auth.password.value" type="password" @keyup.enter="authenticate" placeholder="Пароль" class="w-full mb-4 px-4 py-2 bg-white text-emerald-950 border border-emerald-300 rounded focus:outline-none focus:border-emerald-600 text-sm">
                    <button @click="authenticate" class="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-medium py-2 rounded transition text-sm mb-3 cursor-pointer border-0">Войти</button>
                    <div class="text-center">
                        <button @click="auth.isResetMode.value = true; auth.resetForm.value.success = ''" class="text-xs text-emerald-700 hover:underline cursor-pointer bg-transparent border-0">Забыли пароль?</button>
                    </div>
                </div>
                
                <div v-else class="space-y-3">
                    <p class="text-xs text-emerald-800">Введите ваш логин для отправки запроса администратору:</p>
                    <input v-model="auth.resetForm.value.username" type="text" placeholder="Ваш логин" class="w-full px-4 py-2 bg-white text-emerald-950 border border-emerald-300 rounded text-sm focus:outline-none focus:border-emerald-600">
                    <button @click="auth.requestReset" class="w-full bg-emerald-600 hover:bg-emerald-700 text-white py-2 rounded text-sm font-medium cursor-pointer border-0">Отправить запрос</button>
                    <button @click="auth.isResetMode.value = false" class="w-full bg-emerald-200 hover:bg-emerald-300 text-emerald-900 py-2 rounded text-sm cursor-pointer border-0">Назад ко входу</button>
                    <p v-if="auth.resetForm.value.success" class="text-xs text-emerald-700 bg-emerald-100 p-2 rounded mt-2 text-center">{{ auth.resetForm.value.success }}</p>
                </div>
                <p v-if="auth.authError.value" class="mt-4 text-red-600 text-xs text-center">{{ auth.authError.value }}</p>
            </div>

            <template v-else>
                <!-- Алерт для админа о сбросе паролей -->
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
                        <button @click="auth.showAdminAlertModal.value = false; switchTab('users')" class="w-full bg-emerald-600 hover:bg-emerald-700 text-white py-2 rounded text-sm font-medium cursor-pointer border-0">Перейти к управлению</button>
                    </div>
                </div>

                <!-- БОКОВОЕ МЕНЮ (САЙДБАР) -->
                <aside class="w-64 bg-emerald-50 border-r border-emerald-200 flex flex-col hidden md:flex h-full relative z-20">
                    <div class="p-4 border-b border-emerald-200 text-left">
                        <svg class="h-6 w-auto max-w-full" viewBox="0 0 975 80" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M18.75 64C13.5 64 9.04167 62.4583 5.375 59.375C1.79167 56.2083 0 52.4167 0 48V16C0 11.5833 1.79167 7.83333 5.375 4.75C9.04167 1.58333 13.5 0 18.75 0H75V16H28.125C25.5417 16 23.2917 16.7917 21.375 18.375C19.625 19.9583 18.75 21.8333 18.75 24V40C18.75 42.25 19.625 44.1667 21.375 45.75C23.2917 47.25 25.5417 48 28.125 48H75V64H18.75ZM130.375 48C132.958 48 135.167 47.25 137 45.75C138.833 44.1667 139.75 42.25 139.75 40V24C139.75 21.8333 138.833 19.9583 137 18.375C135.167 16.7917 132.958 16 130.375 16H111.625C109.042 16 106.792 16.7917 104.875 18.375C103.125 19.9583 102.25 21.8333 102.25 24V40C102.25 42.25 103.125 44.1667 104.875 45.75C106.792 47.25 109.042 48 111.625 48H130.375ZM102.25 64C97 64 92.5417 62.4583 88.875 59.375C85.2917 56.2083 83.5 52.4167 83.5 48V16C83.5 11.5833 85.2917 7.83333 88.875 4.75C92.5417 1.58333 97 0 102.25 0H139.75C144.917 0 149.333 1.58333 153 4.75C156.667 7.91667 158.5 11.6667 158.5 16V48C158.5 52.5 156.667 56.2917 153 59.375C149.333 62.4583 144.917 64 139.75 64H102.25ZM167 64V16C167 11.5833 168.792 7.83333 172.375 4.75C176.042 1.58333 180.5 0 185.75 0H242V64H223.25V16H195.125C192.542 16 190.292 16.7917 188.375 18.375C186.625 19.9583 185.75 21.8333 185.75 24V64H167ZM278.625 64V16H250.5V0H325.5V16H297.375V64H278.625ZM352.75 64C347.5 64 343.042 62.4583 339.375 59.375C335.792 56.2083 334 52.4167 334 48V0H409V16H352.75V24H409V40H352.75V48H409V64H352.75ZM417.5 64V56L445.625 32L417.5 8V0H436.25L455 16L473.75 0H492.5V8L464.375 32L492.5 56V64H473.75L455 48L436.25 64H417.5ZM501 64V48H519.75V64H501ZM528.125 64V0H603.125C608.292 0 612.708 1.58333 616.375 4.75C620.042 7.91667 621.875 11.6667 621.875 16V64H603.125V24C603.125 21.8333 602.208 19.9583 600.375 18.375C598.542 16.7917 596.333 16 593.75 16H584.375V64H565.625V16H546.875V64H528.125ZM686.625 24V16H649.125V24H686.625ZM649.125 64C643.875 64 639.417 62.4583 635.75 59.375C632.167 56.2083 630.375 52.4167 630.375 48V16C630.375 11.5833 632.167 7.83333 635.75 4.75C639.417 1.58333 643.875 0 649.125 0H686.625C691.792 0 696.208 1.58333 699.875 4.75C703.542 7.91667 705.375 11.6667 705.375 16V32C705.375 34.25 704.458 36.1667 702.625 37.75C700.792 39.25 698.583 40 696 40H649.125V48H705.375V64H649.125ZM788.875 48V24C788.875 21.8333 787.958 19.9583 786.125 18.375C784.292 16.7917 782.083 16 779.5 16H760.75C758.167 16 755.958 16.7917 754.125 18.375C752.292 19.9583 751.375 21.8333 751.375 24V48H788.875ZM723.25 80V48H732.625V16C732.625 11.5833 734.458 7.83333 738.125 4.75C741.708 1.58333 746.125 0 751.375 0H788.875C794.042 0 798.458 1.58333 802.125 4.75C805.792 7.91667 807.625 11.6667 807.625 16V48H817V80H798.25V64H742V80H723.25ZM816.125 64V0H834.875V40L872.375 8V0H891.125V64H872.375V32L834.875 64H816.125ZM955.875 48V40H918.375V48H955.875ZM918.375 64C913.125 64 908.667 62.4583 905 59.375C901.417 56.2083 899.625 52.4167 899.625 48V32C899.625 29.8333 900.5 27.9583 902.25 26.375C904.083 24.7917 906.333 24 909 24H955.875V16H899.625V0H955.875C961.042 0 965.458 1.58333 969.125 4.75C972.792 7.91667 974.625 11.6667 974.625 16V48C974.625 52.5 972.792 56.2917 969.125 59.375C965.458 62.4583 961.042 64 955.875 64H918.375Z" fill="#065F46"/>
    </svg>
                        <p class="text-emerald-700 text-xs mt-1">Роль: {{ auth.login.value === 'admin_main' ? 'Администратор' : 'Рег. пользователь' }}</p>
                    </div>
                    
                    <nav class="flex-1 p-4 space-y-2 overflow-y-auto pb-12">
                        <!-- ВКЛАДКА ТОЛЬКО ДЛЯ РЕГИОНАЛЬНЫХ -->
                        <a href="#" v-if="auth.login.value !== 'admin_main'" @click.prevent="switchTab('broadcasts')" :class="currentTab === 'broadcasts' ? 'bg-emerald-600 text-white font-medium shadow-sm' : 'text-emerald-900 hover:bg-emerald-100/60'" class="block w-full text-left px-4 py-2 rounded-lg transition text-sm flex items-center justify-between">
                            <span>▶️ Трансляции</span>
                            <span v-if="schedules.schedules.value.some(s => s.status === 'Активен')" class="w-2 h-2 rounded-full bg-red-500 animate-pulse"></span>
                        </a>

                        <!-- ВКЛАДКА ТОЛЬКО ДЛЯ АДМИНА -->
                        <a href="#" v-if="auth.login.value === 'admin_main'" @click.prevent="switchTab('media')" :class="currentTab === 'media' ? 'bg-emerald-600 text-white font-medium shadow-sm' : 'text-emerald-900 hover:bg-emerald-100/60'" class="block w-full text-left px-4 py-2 rounded-lg transition text-sm">📁 Медиатека</a>
                        <a href="#" v-if="auth.login.value === 'admin_main'" @click.prevent="switchTab('playlists')" :class="currentTab === 'playlists' ? 'bg-emerald-600 text-white font-medium shadow-sm' : 'text-emerald-900 hover:bg-emerald-100/60'" class="block w-full text-left px-4 py-2 rounded-lg transition text-sm">📑 Плейлисты</a>
                        <a href="#" v-if="auth.login.value === 'admin_main'" @click.prevent="switchTab('import')" :class="currentTab === 'import' ? 'bg-emerald-600 text-white font-medium shadow-sm' : 'text-emerald-900 hover:bg-emerald-100/60'" class="block w-full text-left px-4 py-2 rounded-lg transition text-sm">📥 Импорт файлов</a>
                        <a href="#" v-if="auth.login.value === 'admin_main'" @click.prevent="switchTab('trash')" :class="currentTab === 'trash' ? 'bg-emerald-600 text-white font-medium shadow-sm' : 'text-emerald-900 hover:bg-emerald-100/60'" class="block w-full text-left px-4 py-2 rounded-lg transition text-sm">🗑️ Корзина</a>
                        
                        <!-- ОБЩИЕ ВКЛАДКИ -->
                        <a href="#" @click.prevent="switchTab('schedule')" :class="currentTab === 'schedule' ? 'bg-emerald-600 text-white font-medium shadow-sm' : 'text-emerald-900 hover:bg-emerald-100/60'" class="block w-full text-left px-4 py-2 rounded-lg transition text-sm">📅 Расписания</a>
                        
                        <!-- ВКЛАДКИ ТОЛЬКО ДЛЯ АДМИНА -->
                        <a href="#" v-if="auth.login.value === 'admin_main'" @click.prevent="switchTab('monitoring')" :class="currentTab === 'monitoring' ? 'bg-emerald-600 text-white font-medium shadow-sm' : 'text-emerald-900 hover:bg-emerald-100/60'" class="block w-full text-left px-4 py-2 rounded-lg transition text-sm">🖥️ Мониторинг сети</a>
                        <a href="#" v-if="auth.login.value === 'admin_main'" @click.prevent="switchTab('reports')" :class="currentTab === 'reports' ? 'bg-emerald-600 text-white font-medium shadow-sm' : 'text-emerald-900 hover:bg-emerald-100/60'" class="block w-full text-left px-4 py-2 rounded-lg transition text-sm">📊 Отчёты</a>
                        <a href="#" v-if="auth.login.value === 'admin_main'" @click.prevent="switchTab('users')" :class="currentTab === 'users' ? 'bg-emerald-600 text-white font-medium shadow-sm' : 'text-emerald-900 hover:bg-emerald-100/60'" class="block w-full text-left px-4 py-2 rounded-lg transition text-sm">👥 Пользователи <span v-if="users.adminRequests.value.length > 0" class="bg-red-500 text-white text-[10px] px-1.5 py-0.5 rounded-full ml-1">{{ users.adminRequests.value.length }}</span></a>
                        
                        <!-- ПРОФИЛЬ -->
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
                        <button @click="requestConfirm($event, 'Вы действительно хотите выйти из системы?', logoutHandler)" class="w-full bg-red-100 hover:bg-red-200 text-red-800 border border-red-300 px-4 py-2 rounded-lg text-sm transition font-medium text-center cursor-pointer border-0">Выйти</button>
                    </div>
                </aside>

                <main class="flex-1 p-8 overflow-y-auto bg-white h-full text-sm text-left">

                    <!-- НОВАЯ ВКЛАДКА: ТРАНСЛЯЦИИ (ТОЛЬКО ДЛЯ РЕГИОНАЛЬНЫХ МЕНЕДЖЕРОВ) -->
                    <div v-if="currentTab === 'broadcasts' && auth.login.value !== 'admin_main'" class="space-y-6">
                        <div class="bg-emerald-50 border border-emerald-200 rounded-xl p-6 shadow-sm">
                            <div class="flex justify-between items-center mb-6">
                                <h2 class="text-xl font-semibold text-emerald-900">Ваш пульт управления трансляциями</h2>
                                <button @click="schedules.fetchSchedules" class="text-xs bg-emerald-200 hover:bg-emerald-300 text-emerald-900 px-3 py-1.5 rounded-md font-medium cursor-pointer border-0 shadow-sm transition">🔄 Обновить графики</button>
                            </div>
                            
                            <div v-if="schedules.schedules.value.filter(s => s.status !== 'Завершен').length === 0" class="text-center py-12 text-emerald-600 bg-white border border-dashed border-emerald-200 rounded-lg shadow-sm">
                                <span class="text-4xl block mb-3 opacity-50">☕</span>
                                Нет активных или ожидающих трансляций для вашего филиала.
                            </div>
                            
                            <div v-else class="grid grid-cols-1 lg:grid-cols-2 gap-5">
                                <div v-for="item in schedules.schedules.value.filter(s => s.status !== 'Завершен')" :key="item.id" 
                                     class="bg-white border p-5 rounded-xl flex flex-col gap-4 shadow-sm transition-all duration-300"
                                     :class="item.status === 'Активен' ? 'border-emerald-400 ring-2 ring-emerald-400/50 shadow-emerald-100' : 'border-emerald-200 hover:shadow-md'">
                                     
                                     <div class="flex justify-between items-start">
                                         <div class="pr-2">
                                             <div class="flex items-center gap-2 mb-1">
                                                 <span v-if="item.playlist_id" class="text-xl">📑</span>
                                                 <span v-else class="text-xl">📁</span>
                                                 <h3 class="text-emerald-900 font-bold text-lg leading-tight line-clamp-2" :title="item.playlist_id ? getPlaylistName(item.playlist_id) : item.file">
                                                     {{ item.playlist_id ? getPlaylistName(item.playlist_id) : item.file }}
                                                 </h3>
                                             </div>
                                             <p class="text-[11px] font-medium text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded inline-block">
                                                 Целевые экраны: {{ !item.screens || item.screens.length === 0 ? 'Все экраны филиала' : item.screens.join(', ') }}
                                             </p>
                                         </div>
                                         <div class="shrink-0 text-right">
                                             <span class="px-3 py-1 rounded-full text-xs font-bold shadow-sm uppercase tracking-wider inline-flex items-center gap-1.5" 
                                                   :class="item.status === 'Активен' ? 'bg-red-500 text-white' : 'bg-amber-100 text-amber-800 border border-amber-200'">
                                                 <span v-if="item.status === 'Активен'" class="w-1.5 h-1.5 rounded-full bg-white animate-pulse"></span>
                                                 {{ item.status === 'Активен' ? 'В эфире' : 'Ожидание' }}
                                             </span>
                                         </div>
                                     </div>
                                     
                                     <div class="grid grid-cols-2 gap-2 text-[11px] text-slate-600 bg-slate-50 border border-slate-100 p-3 rounded-lg">
                                        <div>
                                            <p class="text-slate-400 uppercase tracking-wide text-[9px] font-bold mb-0.5">Время старта</p>
                                            <p class="font-medium text-slate-800 text-sm">{{ item.time_start.replace('T', ' ') }}</p>
                                        </div>
                                        <div>
                                            <p class="text-slate-400 uppercase tracking-wide text-[9px] font-bold mb-0.5">Время окончания</p>
                                            <p class="font-medium text-slate-800 text-sm">{{ item.time_end.replace('T', ' ') }}</p>
                                        </div>
                                     </div>
                                     
                                     <div class="mt-auto flex flex-col gap-2">
                                        <button @click="startLiveBroadcast(item)" 
                                                :disabled="item.status !== 'Активен'"
                                                class="w-full py-3 rounded-lg text-sm font-bold uppercase tracking-widest transition-all border-0 flex items-center justify-center gap-2"
                                                :class="item.status === 'Активен' ? 'bg-emerald-600 hover:bg-emerald-700 text-white cursor-pointer shadow-lg hover:shadow-xl hover:-translate-y-0.5' : 'bg-slate-100 text-slate-400 cursor-not-allowed border border-slate-200'">
                                            <span class="text-lg leading-none">▶</span> 
                                            {{ item.status === 'Активен' ? 'Запустить на экран' : 'Ждите начала эфира' }}
                                        </button>
                                        <button v-if="item.status === 'Активен'" @click="openQr(item)" class="w-full py-2.5 rounded-lg text-[11px] font-bold uppercase tracking-widest bg-blue-50 text-blue-700 hover:bg-blue-100 border border-blue-200 transition-all cursor-pointer flex items-center justify-center gap-2">
                                            📱 Сгенерировать QR-код для зрителей
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Вкладка: Пользователи (Только Админ) -->
                    <div v-if="currentTab === 'users' && auth.login.value === 'admin_main'" class="space-y-6">
                        <div class="bg-emerald-50 border border-emerald-200 rounded-xl p-6 shadow-sm">
                            <div class="flex justify-between items-center mb-6">
                                <h2 class="text-xl font-semibold text-emerald-900">Управление учетными записями</h2>
                                <div class="flex gap-2">
                                    <button @click="users.showAddUserModal.value = true" class="text-xs bg-emerald-600 hover:bg-emerald-700 text-white px-3 py-1.5 rounded-md font-medium shadow-sm cursor-pointer border-0">+ Новый пользователь</button>
                                    <button @click="users.fetchAdminUsers" class="text-xs bg-emerald-200 hover:bg-emerald-300 text-emerald-900 px-3 py-1.5 rounded-md font-medium cursor-pointer border-0">Обновить</button>
                                </div>
                            </div>

                            <div v-if="users.showAddUserModal.value" class="bg-emerald-100/50 border border-emerald-200 rounded-xl p-6 shadow-md mb-6">
                                <h3 class="text-lg font-medium mb-4 text-emerald-800">Создание нового пользователя</h3>
                                <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
                                    <div>
                                        <label class="block text-xs text-emerald-700 mb-1 font-medium">Логин (Username)</label>
                                        <input v-model="users.newUserForm.value.username" type="text" placeholder="Например: user_kazan" class="w-full bg-white text-emerald-950 border border-emerald-300 rounded p-2 text-sm focus:outline-none focus:border-emerald-600">
                                    </div>
                                    <div>
                                        <label class="block text-xs text-emerald-700 mb-1 font-medium">Первичный пароль</label>
                                        <input v-model="users.newUserForm.value.password" type="text" placeholder="Пароль для входа" class="w-full bg-white text-emerald-950 border border-emerald-300 rounded p-2 text-sm focus:outline-none focus:border-emerald-600">
                                    </div>
                                    <div>
                                        <label class="block text-xs text-emerald-700 mb-1 font-medium">Роль</label>
                                        <select v-model="users.newUserForm.value.role" class="w-full bg-white text-emerald-950 border border-emerald-300 rounded p-2 text-sm focus:outline-none focus:border-emerald-600">
                                            <option value="regional">Региональный (Филиал)</option>
                                            <option value="admin">Администратор (Полный доступ)</option>
                                        </select>
                                    </div>
                                    <div>
                                        <label class="block text-xs text-emerald-700 mb-1 font-medium">Филиал (Город)</label>
                                        <select v-model="users.newUserForm.value.city_id" class="w-full bg-white text-emerald-950 border border-emerald-300 rounded p-2 text-sm focus:outline-none focus:border-emerald-600">
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
                                    <button @click="users.showAddUserModal.value = false" class="bg-emerald-200 text-emerald-900 px-4 py-2 rounded text-sm cursor-pointer border-0">Отмена</button>
                                    <button @click="users.createUser" class="bg-emerald-600 text-white px-4 py-2 rounded text-sm cursor-pointer border-0">Создать пользователя</button>
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
                                        <button @click="requestConfirm($event, `Сбросить пароль для ${req.username}?`, () => users.forceReset(req.username))" class="bg-amber-600 hover:bg-amber-700 text-white text-xs px-3 py-1.5 rounded transition font-medium cursor-pointer border-0">Выдать новый пароль</button>
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
                                                <button @click="requestConfirm($event, `Сбросить пароль для ${uname}?`, () => users.forceReset(uname))" class="bg-emerald-600 hover:bg-emerald-700 text-white text-xs px-3 py-1.5 rounded transition cursor-pointer border-0">Сбросить пароль</button>
                                                <button v-if="uname !== auth.login.value" @click="requestConfirm($event, `Точно удалить пользователя ${uname}?`, () => users.deleteUser(uname))" class="bg-red-50 hover:bg-red-100 text-red-700 text-xs px-3 py-1.5 rounded border border-red-200 transition cursor-pointer">Удалить</button>
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
                                <input v-model="profileForm.oldPassword" type="password" placeholder="Текущий пароль" class="w-full mb-3 px-4 py-2 bg-white text-emerald-950 placeholder-gray-400 border border-emerald-300 rounded focus:outline-none focus:border-emerald-600 text-sm">
                                <input v-model="profileForm.newPassword" type="password" placeholder="Новый пароль" class="w-full mb-3 px-4 py-2 bg-white text-emerald-950 placeholder-gray-400 border border-emerald-300 rounded focus:outline-none focus:border-emerald-600 text-sm">
                                <input v-model="profileForm.confirmPassword" type="password" placeholder="Повторите новый пароль" class="w-full mb-4 px-4 py-2 bg-white text-emerald-950 placeholder-gray-400 border border-emerald-300 rounded focus:outline-none focus:border-emerald-600 text-sm">
                                
                                <button @click="updatePassword" class="w-full bg-emerald-600 hover:bg-emerald-700 text-white py-2 rounded text-sm transition font-medium cursor-pointer border-0">Сохранить новый пароль</button>
                                <p v-if="profileForm.error" class="mt-3 text-red-600 text-sm">{{ profileForm.error }}</p>
                                <p v-if="profileForm.success" class="mt-3 text-emerald-600 text-sm font-medium">{{ profileForm.success }}</p>
                            </div>
                        </section>
                    </div>

                    <!-- Вкладка: Медиатека (Только Админ) -->
                    <div v-if="currentTab === 'media' && auth.login.value === 'admin_main'">
                        <section class="bg-emerald-50 border border-emerald-200 rounded-xl p-6 shadow-sm">
                            <div class="flex justify-between items-center mb-6">
                                <h2 class="text-xl font-semibold text-emerald-900">Интерфейс управления контентом</h2>
                                <button @click="media.fetchFiles(); media.fetchStats()" class="text-xs bg-emerald-200 hover:bg-emerald-300 text-emerald-900 px-3 py-1.5 rounded-md font-medium cursor-pointer border-0">Обновить</button>
                            </div>
                            <div class="flex flex-col md:flex-row gap-3 mb-6 bg-white p-4 rounded-lg border border-emerald-200 shadow-sm">
                                <input v-model="media.searchQuery.value" type="text" placeholder="Поиск по имени файла..." class="flex-1 bg-white text-emerald-950 border border-emerald-300 rounded-lg p-2 text-sm focus:outline-none focus:border-emerald-600">
                                <select v-model="media.filterCity.value" class="w-full md:w-48 bg-white text-emerald-950 border border-emerald-300 rounded-lg p-2 text-sm focus:outline-none focus:border-emerald-600">
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
                                <select v-model="media.sortBy.value" class="w-full md:w-56 bg-white text-emerald-950 border border-emerald-300 rounded-lg p-2 text-sm focus:outline-none focus:border-emerald-600">
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
                                        <a :href="file.url" target="_blank" class="flex-1 text-center bg-emerald-100 hover:bg-emerald-200 text-emerald-800 text-xs px-3 py-1.5 rounded transition font-medium cursor-pointer">Смотреть</a>
                                        <button @click="requestConfirm($event, 'Переместить файл в корзину?', () => media.deleteFile(file.name))" class="flex-1 bg-red-50 hover:bg-red-100 text-red-700 text-xs px-3 py-1.5 rounded border border-red-200 transition cursor-pointer">В корзину</button>
                                    </div>
                                </div>
                            </div>
                        </section>
                    </div>

                    <!-- Вкладка: Плейлисты (Только Админ) -->
                    <div v-if="currentTab === 'playlists' && auth.login.value === 'admin_main'" class="space-y-6">
                        <div class="flex justify-between items-center">
                            <h2 class="text-xl font-semibold text-emerald-900">Управление плейлистами (Фото/Видео ряды)</h2>
                            <button @click="playlists.openCreateModal()" class="bg-emerald-600 text-white px-4 py-2 rounded-lg text-sm shadow-sm hover:bg-emerald-700 transition cursor-pointer border-0">+ Создать плейлист</button>
                        </div>

                        <div v-if="playlists.showPlaylistModal.value" class="bg-emerald-50 border border-emerald-200 rounded-xl p-6 shadow-md">
                            <h3 class="text-lg font-medium mb-4 text-emerald-800">
                                {{ playlists.editingPlaylistId && playlists.editingPlaylistId.value ? 'Редактирование плейлиста' : 'Создание нового плейлиста' }}
                            </h3>
                            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
                                <div>
                                    <label class="block text-xs text-emerald-700 mb-1 font-medium">Название плейлиста</label>
                                    <input v-model="playlists.newPlaylist.value.name" type="text" placeholder="Например: Утренний показ" class="w-full bg-white text-emerald-950 border border-emerald-300 rounded p-2 text-sm focus:outline-none focus:border-emerald-600">
                                </div>
                                <div>
                                    <label class="block text-xs text-emerald-700 mb-1 font-medium">Филиал (Город)</label>
                                    <select v-model="playlists.newPlaylist.value.city" class="w-full bg-white text-emerald-950 border border-emerald-300 rounded p-2 text-sm focus:outline-none focus:border-emerald-600">
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
                                    <input v-model.number="playlists.newPlaylist.value.interval" type="number" min="0" class="w-full bg-white text-emerald-950 border border-emerald-300 rounded p-2 text-sm focus:outline-none focus:border-emerald-600">
                                </div>
                                <div>
                                    <label class="block text-xs text-emerald-700 mb-1 font-medium">Количество повторов</label>
                                    <input v-model.number="playlists.newPlaylist.value.repeats" type="number" min="1" class="w-full bg-white text-emerald-950 border border-emerald-300 rounded p-2 text-sm focus:outline-none focus:border-emerald-600">
                                </div>
                            </div>

                            <div class="bg-white p-4 rounded-lg border border-emerald-200 mb-4">
                                <h4 class="text-xs font-semibold text-emerald-900 mb-2">Состав плейлиста:</h4>
                                <div class="flex gap-2 mb-3">
                                    <select v-model="playlists.selectedFileToAdd.value" class="flex-1 bg-white text-emerald-950 border border-emerald-300 rounded p-2 text-sm focus:outline-none focus:border-emerald-600">
                                        <option v-for="f in media.files.value" :key="f.name" :value="f.name">{{ f.name }}</option>
                                    </select>
                                    <button @click="playlists.addFileToPlaylist" class="bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2 rounded text-sm cursor-pointer border-0">Добавить файл</button>
                                </div>

                                <div v-if="playlists.newPlaylist.value.items.length === 0" class="text-xs text-emerald-600 py-4 text-center">Плейлист пока пуст. Добавьте файлы.</div>
                                <div v-else class="space-y-2">
                                    <div v-for="(item, idx) in playlists.newPlaylist.value.items" :key="idx" class="flex items-center justify-between bg-emerald-50/50 p-2.5 rounded border border-emerald-200 text-xs">
                                        <div class="flex items-center gap-2">
                                            <div class="flex flex-col gap-0.5">
                                                <button @click="playlists.movePlaylistItem(idx, -1)" :disabled="idx === 0" class="text-[10px] bg-white border px-1 rounded disabled:opacity-30 hover:bg-emerald-100 cursor-pointer">▲</button>
                                                <button @click="playlists.movePlaylistItem(idx, 1)" :disabled="idx === playlists.newPlaylist.value.items.length - 1" class="text-[10px] bg-white border px-1 rounded disabled:opacity-30 hover:bg-emerald-100 cursor-pointer">▼</button>
                                            </div>
                                            <span class="font-bold text-emerald-800 ml-1">#{{ idx + 1 }}</span>
                                            <span class="font-medium text-emerald-950 truncate max-w-[150px] lg:max-w-[200px]" :title="item.file">{{ item.file }}</span>
                                            <span v-if="isVideo(item.file)" class="bg-purple-100 text-purple-800 text-[10px] px-1.5 py-0.5 rounded">Видео</span>
                                            <span v-else class="bg-blue-100 text-blue-800 text-[10px] px-1.5 py-0.5 rounded">Фото</span>
                                        </div>
                                        <div class="flex items-center gap-3">
                                            <div v-if="isImage(item.file)" class="flex items-center gap-1.5">
                                                <span class="text-emerald-700 hidden sm:inline">Время:</span>
                                                <input v-model.number="item.duration" type="number" min="1" class="w-14 bg-white text-emerald-950 border border-emerald-300 rounded p-1 text-center focus:outline-none focus:border-emerald-600">
                                            </div>
                                            <div v-else class="text-slate-500 italic hidden sm:inline">По видеоряду</div>
                                            <button @click="playlists.removePlaylistItem(idx)" class="text-red-600 hover:text-red-800 font-bold px-2 py-1 bg-red-50 rounded border border-red-200 cursor-pointer">✕</button>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <div class="flex justify-end gap-3">
                                <button @click="playlists.showPlaylistModal.value = false" class="bg-emerald-200 text-emerald-900 px-4 py-2 rounded text-sm hover:bg-emerald-300 transition cursor-pointer border-0">Отмена</button>
                                <button @click="playlists.savePlaylist" class="bg-emerald-600 text-white px-4 py-2 rounded text-sm hover:bg-emerald-700 transition cursor-pointer border-0">
                                    {{ playlists.editingPlaylistId && playlists.editingPlaylistId.value ? 'Сохранить изменения' : 'Сохранить плейлист' }}
                                </button>
                            </div>
                        </div>

                        <!-- Модальное окно предпросмотра -->
                        <div v-if="playlists.showPreviewModal.value" class="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
                            <div class="bg-white rounded-xl shadow-2xl max-w-2xl w-full overflow-hidden flex flex-col border border-emerald-300">
                                <div class="bg-emerald-800 text-white px-4 py-3 flex justify-between items-center">
                                    <h3 class="font-semibold text-sm">Предпросмотр плейлиста: {{ playlists.previewPlaylistName.value }}</h3>
                                    <button @click="playlists.closePreview" class="text-white hover:text-gray-200 font-bold text-lg cursor-pointer border-0 bg-transparent">✕</button>
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
                                    <button @click="playlists.closePreview" class="bg-gray-300 hover:bg-gray-400 text-gray-800 text-xs px-4 py-2 rounded font-medium cursor-pointer border-0">Закрыть предпросмотр</button>
                                </div>
                            </div>
                        </div>

                        <div class="bg-emerald-50 border border-emerald-200 rounded-xl p-6 shadow-sm">
                            <div v-if="playlists.playlists.value.length === 0" class="text-center py-8 text-emerald-600 bg-white rounded-lg border border-dashed border-emerald-200">Плейлисты еще не созданы.</div>
                            <div v-else class="grid grid-cols-1 xl:grid-cols-2 gap-4">
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
                                        <button @click="playlists.startPreview(pl)" class="bg-emerald-100 hover:bg-emerald-200 text-emerald-800 text-xs px-3 py-1.5 rounded font-medium transition cursor-pointer border-0">▶ Предпросмотр</button>
                                        <div class="flex gap-3">
                                            <button @click="playlists.openEditModal(pl)" class="text-blue-600 hover:text-blue-800 text-xs font-medium cursor-pointer bg-transparent border-0 hover:underline">✏️ Редактировать</button>
                                            <button @click="requestConfirm($event, 'Удалить этот плейлист?', () => playlists.deletePlaylist(pl.id))" class="text-red-600 hover:text-red-800 text-xs font-medium cursor-pointer bg-transparent border-0 hover:underline">🗑️ Удалить</button>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Вкладка: Импорт файлов (Только Админ) -->
                    <div v-if="currentTab === 'import' && auth.login.value === 'admin_main'" class="space-y-6">
                        <div class="bg-emerald-50 border border-emerald-200 rounded-xl p-6 shadow-sm">
                            <h2 class="text-xl font-semibold mb-2 text-emerald-900">Импорт контента</h2>
                            <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mt-6">
                                <!-- Блок загрузки -->
                                <div class="space-y-4 bg-white p-5 rounded-lg border border-emerald-200 shadow-sm">
                                    <h3 class="text-sm font-semibold text-emerald-900">Параметры</h3>
                                    <div>
                                        <label class="block text-xs text-emerald-700 mb-1 font-medium">Целевой филиал:</label>
                                        <select v-model="media.selectedCity.value" class="w-full bg-white text-emerald-950 border border-emerald-300 text-sm rounded-lg p-2.5 focus:outline-none focus:border-emerald-600">
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
                                    <button @click="media.uploadFile" :disabled="!media.selectedFile.value || media.uploading.value" class="w-full bg-emerald-600 hover:bg-emerald-700 disabled:bg-emerald-300 text-white font-medium px-4 py-2.5 rounded-lg transition text-sm cursor-pointer border-0">
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

                    <!-- Вкладка: Корзина (Только Админ) -->
                    <div v-if="currentTab === 'trash' && auth.login.value === 'admin_main'">
                        <div class="bg-emerald-50 border border-emerald-200 rounded-xl p-6 shadow-sm">
                            <div class="flex justify-between items-center mb-4">
                                <h2 class="text-xl font-semibold text-emerald-900">Корзина (хранение до 30 дней)</h2>
                                <button 
                                    @click="media.trashFiles.value.length > 0 ? requestConfirm($event, 'Очистить корзину навсегда?', media.emptyTrash) : showToast('Корзина уже пуста!', 'info')" 
                                    :class="media.trashFiles.value.length === 0 ? 'opacity-50 cursor-not-allowed' : 'hover:bg-red-200 cursor-pointer'" 
                                    class="text-xs bg-red-100 text-red-800 px-4 py-2 rounded-md border border-red-200 font-bold transition border-0">
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
                                    <button @click="media.restoreFile(file.name)" class="bg-emerald-600 hover:bg-emerald-700 text-white text-xs px-4 py-2 rounded-md shadow-sm cursor-pointer border-0">Восстановить</button>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Вкладка: РАСПИСАНИЯ -->
                    <div v-if="currentTab === 'schedule'" class="space-y-6">
                        
                        <!-- ШАПКА С КНОПКОЙ АРХИВА -->
                        <div class="flex justify-between items-center">
                            <h2 class="text-xl font-semibold text-emerald-900">
                                {{ showArchive ? '🗄 Архив трансляций (старше 5 дней)' : 'График трансляций (Smart Planner)' }}
                            </h2>
                            <div class="flex gap-3">
                                <button @click="showArchive = !showArchive" class="bg-emerald-100 text-emerald-800 hover:bg-emerald-200 px-4 py-2 rounded-lg text-sm shadow-sm transition cursor-pointer border-0 font-medium">
                                    {{ showArchive ? '← К активному графику' : '🗄 Архив' }}
                                </button>
                                <button v-if="auth.login.value === 'admin_main' && !showArchive" @click="schedules.openScheduleModal" class="bg-emerald-600 text-white px-4 py-2 rounded-lg text-sm shadow-sm hover:bg-emerald-700 transition cursor-pointer border-0">+ Запланировать</button>
                            </div>
                        </div>

                        <!-- ПАНЕЛЬ ЗАГЛУШКИ (Только для Админа) -->
                        <div v-if="auth.login.value === 'admin_main' && !showArchive" class="bg-slate-800 border border-slate-700 rounded-xl p-5 shadow-lg mb-6 flex flex-col md:flex-row items-center justify-between gap-4">
                            <div>
                                <h3 class="font-bold text-white text-base flex items-center gap-2">📺 Фоновое вещание (Заглушка)</h3>
                                <p class="text-xs text-slate-300 mt-1">Отдельный файл, который играет, когда нет активных трансляций.</p>
                                <p v-if="fallbackFile" class="text-[11px] text-emerald-400 mt-2 font-mono bg-black/30 px-2 py-1 rounded inline-block">Текущая: {{ fallbackFile.split('/').pop() }}</p>
                                <p v-else class="text-[11px] text-amber-400 mt-2 font-mono bg-black/30 px-2 py-1 rounded inline-block">Заглушка не установлена</p>
                            </div>
                            <div class="flex flex-col gap-2 w-full md:w-auto">
                                <div class="flex items-center gap-3">
                                    <input type="file" ref="fallbackFileInput" accept="video/mp4,video/webm,image/jpeg,image/png" class="block w-full text-xs text-slate-300 file:mr-3 file:py-1.5 file:px-3 file:rounded file:border-0 file:text-xs file:font-semibold file:bg-slate-600 file:text-white hover:file:bg-slate-500 cursor-pointer bg-slate-900 rounded border border-slate-600">
                                    <button @click="uploadFallback" :disabled="isFallbackUploading" class="bg-emerald-600 hover:bg-emerald-700 disabled:bg-emerald-800 disabled:text-emerald-300 text-white px-5 py-2 rounded text-sm cursor-pointer border-0 shadow-sm transition font-medium whitespace-nowrap">
                                        {{ isFallbackUploading ? 'Загрузка...' : 'Загрузить' }}
                                    </button>
                                    <button v-if="fallbackFile" @click="clearFallback" class="bg-red-500/20 hover:bg-red-500/40 text-red-400 px-3 py-2 rounded text-sm cursor-pointer border border-red-500/30 transition">✕</button>
                                </div>
                                <div v-if="isFallbackUploading" class="w-full bg-slate-700 rounded-full h-1 mt-1">
                                    <div class="bg-emerald-500 h-1 rounded-full transition-all duration-300" :style="{ width: fallbackUploadProgress + '%' }"></div>
                                </div>
                            </div>
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
                                    <select v-if="schedules.scheduleType.value === 'file'" v-model="schedules.newSchedule.value.file" class="w-full bg-white text-emerald-950 border border-emerald-300 rounded p-2.5 text-sm focus:outline-none focus:border-emerald-600">
                                        <option value="">-- Выберите файл --</option>
                                        <option v-for="f in media.files.value" :key="f.name" :value="f.name">{{ f.name }}</option>
                                    </select>
                                    <select v-else v-model="schedules.newSchedule.value.playlist_id" class="w-full bg-white text-emerald-950 border border-emerald-300 rounded p-2.5 text-sm focus:outline-none focus:border-emerald-600">
                                        <option :value="null">-- Выберите плейлист --</option>
                                        <option v-for="pl in playlists.playlists.value" :key="pl.id" :value="pl.id">📑 {{ pl.name }}</option>
                                    </select>
                                </div>

                                <div class="sm:col-span-2">
                                    <label class="block text-xs text-emerald-700 mb-1 font-medium">Филиал (Город)</label>
                                    <select v-model="schedules.newSchedule.value.city" @change="handleCityChange" class="w-full bg-white text-emerald-950 border border-emerald-300 rounded p-2.5 text-sm focus:outline-none focus:border-emerald-600">
                                        <option value="global">Вся сеть</option>
                                        <option value="moscow">Москва</option>
                                        <option value="spb">Санкт-Петербург</option>
                                        <option value="novocheboksarsk">Новочебоксарск</option>
                                        <option value="yartsevo">Ярцево</option>
                                        <option value="azov">Азов</option>
                                        <option value="orenburg">Оренбург</option>
                                        <option value="chernyakhovsk">Черняховск</option>
                                    </select>
                                    
                                    <div class="mt-2 p-2 bg-emerald-100 border border-emerald-200 rounded flex items-center gap-2 text-xs text-emerald-800 shadow-inner">
                                        <span>🌍</span>
                                        <span>
                                            Часовой пояс: <strong>{{ cityTimezones[schedules.newSchedule.value.city || 'global']?.label || 'МСК' }}</strong>. 
                                            Текущее время в филиале: <strong class="text-emerald-950 text-[13px] font-mono">{{ localCityTimeDisplay }}</strong>
                                        </span>
                                    </div>
                                </div>

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
                                    <label class="block text-xs text-emerald-700 mb-1 font-medium">Время начала (Местное время филиала)</label>
                                    <input id="time_start_picker" type="text" placeholder="Выберите дату и время" class="w-full bg-white text-emerald-950 border border-emerald-300 rounded p-2 text-sm cursor-pointer focus:outline-none focus:border-emerald-600">
                                </div>
                                <div>
                                    <label class="block text-xs text-emerald-700 mb-1 font-medium">Время окончания (Местное время филиала)</label>
                                    <input id="time_end_picker" type="text" placeholder="Выберите дату и время" class="w-full bg-white text-emerald-950 border border-emerald-300 rounded p-2 text-sm cursor-pointer focus:outline-none focus:border-emerald-600">
                                </div>
                            </div>
                            <div class="flex justify-end gap-3 pt-2">
                                <button @click="schedules.showAddModal.value = false" class="bg-emerald-200 text-emerald-900 px-4 py-2 rounded text-sm hover:bg-emerald-300 transition cursor-pointer border-0">Отмена</button>
                                <button @click="schedules.addSchedule($event)" class="bg-emerald-600 text-white px-4 py-2 rounded text-sm hover:bg-emerald-700 transition cursor-pointer border-0">Сохранить</button>
                            </div>
                        </div>
                        
                        <div class="bg-emerald-50 border border-emerald-200 rounded-xl p-6 shadow-sm overflow-x-auto">
                            <table v-if="displaySchedules.length > 0" class="w-full text-sm text-left text-emerald-900">
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
                                    <tr v-for="item in displaySchedules" :key="item.id" class="border-b border-emerald-200 hover:bg-emerald-100/40 transition">
                                        <td class="px-6 py-4 font-medium" :class="showArchive ? 'opacity-70' : ''">
                                            <span v-if="item.playlist_id" class="text-emerald-700 font-bold flex items-center gap-1">
                                                📑 Плейлист: {{ getPlaylistName(item.playlist_id) }}
                                            </span>
                                            <span v-else>📁 {{ item.file }}</span>
                                        </td>
                                        <td class="px-6 py-4 text-xs" :class="showArchive ? 'opacity-70' : ''">
                                            <span class="font-bold text-emerald-800 uppercase">{{ item.city }}</span><br>
                                            <span class="text-[10px] text-slate-500 font-normal lowercase">{{ !item.screens || item.screens.length === 0 ? 'Все экраны' : item.screens.join(', ') }}</span>
                                        </td>
                                        <td class="px-6 py-4 text-[11px] leading-tight" :class="showArchive ? 'opacity-70' : ''">
                                            <div class="flex flex-col gap-0.5">
                                                <span>С: {{ item.time_start.replace('T', ' ') }}</span>
                                                <span>По: {{ item.time_end.replace('T', ' ') }}</span>
                                                <span class="mt-1 bg-slate-200 text-slate-800 px-1.5 py-0.5 rounded w-max text-[9px] font-bold shadow-sm">
                                                    Пояс: {{ cityTimezones[item.city]?.label || 'МСК' }}
                                                </span>
                                            </div>
                                        </td>
                                        <td class="px-6 py-4">
                                            <span class="px-2.5 py-1 rounded text-xs font-medium" :class="{
                                                'bg-emerald-300 text-emerald-800': item.status === 'Активен', 
                                                'bg-amber-200 text-amber-800': item.status === 'Ожидание', 
                                                'bg-slate-200 text-slate-600': item.status === 'Завершен'
                                            }">{{ item.status }}</span>
                                        </td>
                                        <td v-if="auth.login.value === 'admin_main'" class="px-6 py-4">
                                            <button v-if="item.status === 'Активен'" @click="openQr(item)" class="text-blue-600 text-xs hover:underline bg-transparent border-0 cursor-pointer mr-3">QR-код</button>
                                            <button @click="requestConfirm($event, 'Удалить из расписания?', () => schedules.deleteSchedule(item.id))" class="text-red-700 text-xs hover:underline bg-transparent border-0 cursor-pointer">Удалить</button>
                                        </td>
                                    </tr>
                                </tbody>
                            </table>
                            <div v-else class="text-center py-8 text-emerald-600 bg-white rounded-lg border border-dashed border-emerald-200">
                                {{ showArchive ? 'В архиве пока нет старых трансляций.' : 'Расписание пока пусто.' }}
                            </div>
                        </div>
                    </div>

                    <!-- ВКЛАДКА МОНИТОРИНГ (Только Админ) -->
                    <div v-if="currentTab === 'monitoring' && auth.login.value === 'admin_main'">
                        <div class="space-y-6">
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

                            <!-- Плеер трансляций для админа -->
                            <div class="bg-emerald-50 border border-emerald-200 rounded-xl p-6 shadow-sm">
                                <h2 class="text-xl font-semibold text-emerald-900 mb-4">Плеер трансляций (Эфир экранов)</h2>
                                
                                <div class="flex flex-col md:flex-row gap-4 mb-6">
                                    <div class="flex-1">
                                        <label class="block text-xs font-semibold text-emerald-800 mb-1">Город</label>
                                        <select v-model="monitorSelectedCity" @change="handleMonitorCityChange" class="w-full bg-white text-emerald-950 border border-emerald-300 rounded p-2.5 text-sm focus:outline-none focus:border-emerald-600">
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
                                        <select v-model="monitorSelectedScreen" class="w-full bg-white text-emerald-950 border border-emerald-300 rounded p-2.5 text-sm focus:outline-none focus:border-emerald-600">
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
                                                <button @click="startLiveBroadcast(activeMonitorSchedule)" class="mt-4 bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2 rounded text-sm transition shadow border-0 cursor-pointer">Запустить эмулятор плейлиста</button>
                                            </div>
                                            <div v-else class="w-full h-full">
                                                <img v-if="isImage(activeMonitorSchedule.file)" :src="getFileUrl(activeMonitorSchedule.file)" class="w-full h-full object-contain bg-black">
                                                <video v-else-if="isVideo(activeMonitorSchedule.file)" :src="getFileUrl(activeMonitorSchedule.file)" autoplay loop muted class="w-full h-full object-contain bg-black"></video>
                                            </div>
                                        </div>
                                        
                                        <div class="absolute top-4 left-4 bg-black/70 backdrop-blur-md px-3 py-1.5 rounded-lg border border-white/10 flex items-center gap-2">
                                            <div v-if="!activeMonitorSchedule.is_fallback" class="w-2 h-2 rounded-full bg-red-500 animate-pulse shadow-[0_0_8px_rgba(239,68,68,1)]"></div>
                                            <div v-else class="w-2 h-2 rounded-full bg-slate-400"></div>
                                            <span class="text-white text-xs font-semibold tracking-wider">
                                                {{ activeMonitorSchedule.is_fallback ? 'ФОНОВОЕ ВИДЕО' : 'LIVE ЭФИР' }}
                                            </span>
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

                    <!-- ВКЛАДКА ОТЧЕТЫ (Только Админ) -->
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

                            <!-- СИСТЕМНЫЙ ЖУРНАЛ СОБЫТИЙ -->
                            <div class="bg-white border border-emerald-200 rounded-xl p-6 shadow-sm">
                                <div class="flex justify-between items-center mb-4">
                                    <div>
                                        <h3 class="text-emerald-900 font-semibold">Системный журнал событий</h3>
                                        <p class="text-xs text-emerald-600 mt-0.5">Фиксация действий пользователей, входов в систему и операций с файлами</p>
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
                                                    <span :class="{
                                                        'bg-blue-100 text-blue-900': log.action === 'Вход',
                                                        'bg-slate-200 text-slate-800': log.action === 'Выход',
                                                        'bg-emerald-100 text-emerald-900': log.action !== 'Вход' && log.action !== 'Выход'
                                                    }" class="px-2 py-0.5 rounded text-[11px] font-bold">{{ log.action }}</span>
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
        
        <!-- МОДАЛЬНОЕ ОКНО QR-КОДА -->
        <div v-if="showQrModal" class="fixed inset-0 bg-black/60 z-[200] flex items-center justify-center p-4 backdrop-blur-sm">
            <div class="bg-white rounded-2xl max-w-sm w-full p-8 text-center shadow-2xl relative border border-emerald-200">
                <button @click="showQrModal = false" class="absolute top-4 right-4 text-gray-400 hover:text-gray-800 text-xl font-bold bg-transparent border-0 cursor-pointer">✕</button>
                <h3 class="text-lg font-bold text-emerald-900 mb-2">Доступ к трансляции</h3>
                <p class="text-xs text-gray-500 mb-6">Отсканируйте код камерой смартфона, чтобы открыть прямой эфир</p>
                
                <div class="bg-gray-50 p-4 rounded-xl border border-gray-100 inline-block mb-6 shadow-inner">
                    <img :src="`https://api.qrserver.com/v1/create-qr-code/?size=250x250&data=${encodeURIComponent(currentQrUrl)}`" alt="QR Code" class="w-48 h-48 mix-blend-multiply">
                </div>
                
                <p class="text-[10px] text-emerald-700 bg-emerald-50 px-3 py-2 rounded break-all border border-emerald-100 font-mono">{{ currentQrUrl }}</p>
            </div>
        </div>

    </template> <!-- Конец условия v-else для обычного интерфейса -->
</div>
</template>