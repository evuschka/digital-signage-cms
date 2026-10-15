<script setup>
import { ref, onMounted, computed } from 'vue';

const props = defineProps({
    reports: Object,
    auth: Object,
    schedules: Object, // передаем schedules composable, так как там лежат функции для экранов
    toast: Function,
    confirm: Function
});

const selectedCity = ref('moscow');
const selectedScreenIndex = ref(0);
const currentItem = ref(null);
const mediaList = ref([]);
const currentIndex = ref(0);
const intervalTimer = ref(null);
const isVideoPlaying = ref(false);

// Модальное окно для создания экрана
const showAddScreenModal = ref(false);
const newScreenForm = ref({ city_id: 'moscow', name: '' });

// Динамический список экранов для плеера на основе данных с сервера
const currentScreensList = computed(() => {
    if (!props.schedules || !props.schedules.allScreensMap.value) return ['Экран 1'];
    return props.schedules.allScreensMap.value[selectedCity.value] || ['Экран 1'];
});

// Полный список экранов с их статусами (запрашиваем с сервера)
const getScreens = () => {
    const list = props.reports?.monitoringData?.value || [];
    return list;
};

const handleAddScreen = async () => {
    if (!newScreenForm.value.name.trim()) {
        props.toast('Введите имя экрана', 'warning');
        return;
    }
    
    try {
        const res = await fetch('/screens/', {
            method: 'POST',
            headers: { 
                'Authorization': props.auth.authHeader.value,
                'Content-Type': 'application/json' 
            },
            body: JSON.stringify(newScreenForm.value)
        });
        
        if (res.ok) {
            props.toast('Экран успешно добавлен', 'success');
            showAddScreenModal.value = false;
            newScreenForm.value.name = '';
            // Обновляем данные
            if (props.schedules.fetchScreens) props.schedules.fetchScreens();
            if (props.reports.fetchMonitoring) props.reports.fetchMonitoring();
        } else {
            const data = await res.json();
            props.toast(data.detail || 'Ошибка создания экрана', 'error');
        }
    } catch (e) {
        props.toast('Ошибка сети', 'error');
    }
};

const deleteScreen = async (screenId) => {
    try {
        const res = await fetch(`/screens/${screenId}`, {
            method: 'DELETE',
            headers: { 'Authorization': props.auth.authHeader.value }
        });
        if (res.ok) {
            props.toast('Экран удален', 'success');
            if (props.schedules.fetchScreens) props.schedules.fetchScreens();
            if (props.reports.fetchMonitoring) props.reports.fetchMonitoring();
        } else {
            props.toast('Ошибка удаления', 'error');
        }
    } catch (e) {
        props.toast('Ошибка сети', 'error');
    }
};

const fetchActiveSchedule = async () => {
    try {
        const response = await fetch(`/public-broadcast/active?city=${selectedCity.value}&screen=${selectedScreenIndex.value}`);
        if (!response.ok) throw new Error('Ошибка загрузки');
        const data = await response.json();
        
        if (data && data.items && data.items.length > 0) {
            mediaList.value = data.items;
            if (!currentItem.value) {
                currentIndex.value = 0;
                loadCurrentMedia();
            }
        } else {
            currentItem.value = { type: 'text', text: `Нет активного расписания для: ${currentScreensList.value[selectedScreenIndex.value] || selectedCity.value}` };
        }
    } catch (e) {
        currentItem.value = { type: 'text', text: `Трансляция: ${currentScreensList.value[selectedScreenIndex.value] || selectedCity.value} (Ожидание данных)` };
    }
};

const loadCurrentMedia = () => {
    if (mediaList.value.length === 0) return;
    if (currentIndex.value >= mediaList.value.length) currentIndex.value = 0;

    const item = mediaList.value[currentIndex.value];
    currentItem.value = item;

    const filename = item.file || item;
    const isVid = typeof filename === 'string' && (filename.endsWith('.mp4') || filename.endsWith('.webm') || filename.endsWith('.mov'));

    if (isVid) {
        isVideoPlaying.value = true;
    } else {
        isVideoPlaying.value = false;
        const duration = (item.duration || 10) * 1000;
        if (intervalTimer.value) clearTimeout(intervalTimer.value);
        intervalTimer.value = setTimeout(() => {
            currentIndex.value++;
            loadCurrentMedia();
        }, duration);
    }
};

const handleVideoEnded = () => {
    currentIndex.value++;
    loadCurrentMedia();
};

const handleRefreshStatus = () => {
    if (props.reports && typeof props.reports.fetchMonitoring === 'function') {
        props.reports.fetchMonitoring();
    }
    if (props.schedules && typeof props.schedules.fetchScreens === 'function') {
        props.schedules.fetchScreens();
    }
};

onMounted(() => {
    fetchActiveSchedule();
    handleRefreshStatus();
});
</script>

<template>
<div class="space-y-6 pb-12">
    
    <!-- БЛОК ТРАНСЛЯЦИЙ -->
    <div class="bg-emerald-50 border border-emerald-200 rounded-xl p-5 shadow-sm">
        <div class="flex flex-col md:flex-row justify-between items-start md:items-center mb-4 gap-3">
            <div>
                <h3 class="text-base font-bold text-emerald-900 flex items-center gap-2">
                    <span>📺</span> Трансляции в реальном времени (Эмуляция экранов)
                </h3>
                <p class="text-xs text-emerald-700">Выберите филиал и конкретный экран для проверки эфира</p>
            </div>
            
            <div class="flex items-center gap-2">
                <select v-model="selectedCity" @change="selectedScreenIndex = 0; fetchActiveSchedule()" class="bg-white border border-emerald-300 text-emerald-900 text-xs px-3 py-2 rounded-lg font-medium outline-none focus:border-emerald-600 shadow-sm cursor-pointer">
                    <option value="global">Вся сеть (Global)</option>
                    <option value="moscow">Москва</option>
                    <option value="spb">Санкт-Петербург</option>
                    <option value="novocheboksarsk">Новочебоксарск</option>
                    <option value="yartsevo">Ярцево</option>
                    <option value="azov">Азов</option>
                    <option value="orenburg">Оренбург</option>
                    <option value="chernyakhovsk">Черняховск</option>
                </select>

                <select v-if="currentScreensList.length > 0" v-model="selectedScreenIndex" @change="fetchActiveSchedule()" class="bg-emerald-700 text-white text-xs px-3 py-2 rounded-lg font-medium outline-none focus:bg-emerald-800 shadow-sm cursor-pointer">
                    <option v-for="(screenName, index) in currentScreensList" :key="index" :value="index">
                        {{ screenName }}
                    </option>
                </select>
            </div>
        </div>

        <div class="w-full h-64 bg-black rounded-lg overflow-hidden relative flex items-center justify-center border border-emerald-900/20 shadow-inner">
            <div v-if="currentItem" class="w-full h-full flex items-center justify-center relative">
                <div v-if="currentItem.type === 'text'" class="text-white text-center p-4">
                    <div class="text-3xl mb-2">📡</div>
                    <p class="text-sm text-emerald-400 font-medium tracking-wide">{{ currentItem.text }}</p>
                </div>
                <img v-else-if="!isVideoPlaying" :src="`/media-file/${encodeURIComponent(currentItem.file || currentItem)}`" class="w-full h-full object-contain">
                <video v-else :src="`/media-file/${encodeURIComponent(currentItem.file || currentItem)}`" autoplay muted playsinline @ended="handleVideoEnded" class="w-full h-full object-contain"></video>

                <div class="absolute bottom-3 left-3 bg-black/60 backdrop-blur-md text-white/80 text-[11px] px-2.5 py-1 rounded border border-white/10">
                    Эфир: <span class="text-emerald-400 font-bold uppercase">{{ currentScreensList[selectedScreenIndex] || selectedCity }}</span> | Слайд: {{ currentIndex + 1 }}/{{ mediaList.length }}
                </div>
            </div>
            <div v-else class="text-gray-400 text-xs animate-pulse">
                Загрузка трансляции...
            </div>
        </div>
    </div>

    <!-- СЕТКА МОНИТОРИНГА -->
    <div class="flex flex-col sm:flex-row justify-between items-center pt-2 gap-3">
        <h2 class="text-xl font-bold text-emerald-900">Мониторинг сети экранов</h2>
        <div class="flex gap-2">
            <button @click="handleRefreshStatus" class="bg-emerald-200 text-emerald-900 hover:bg-emerald-300 text-xs px-4 py-2 rounded-lg transition font-medium shadow-sm">Обновить статус</button>
            <button v-if="props.auth.login.value === 'admin_main'" @click="showAddScreenModal = true" class="bg-emerald-600 hover:bg-emerald-700 text-white text-xs px-4 py-2 rounded-lg transition font-medium shadow-sm">+ Добавить экран</button>
        </div>
    </div>

    <!-- Модальное окно добавления экрана -->
    <div v-if="showAddScreenModal" class="bg-emerald-100/50 border border-emerald-200 rounded-xl p-6 shadow-md mb-4">
        <h3 class="text-lg font-medium mb-4 text-emerald-800">Регистрация нового экрана</h3>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
            <div>
                <label class="block text-xs text-emerald-700 mb-1 font-medium">Филиал (Город)</label>
                <select v-model="newScreenForm.city_id" class="w-full bg-white border border-emerald-300 rounded p-2 text-sm">
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
                <label class="block text-xs text-emerald-700 mb-1 font-medium">Системное имя экрана</label>
                <input v-model="newScreenForm.name" type="text" placeholder="Например: Новый Экран 1" class="w-full bg-white border border-emerald-300 rounded p-2 text-sm">
            </div>
        </div>
        <div class="flex justify-end gap-3 mt-4">
            <button @click="showAddScreenModal = false" class="bg-emerald-200 text-emerald-900 px-4 py-2 rounded text-sm">Отмена</button>
            <button @click="handleAddScreen" class="bg-emerald-600 text-white px-4 py-2 rounded text-sm">Добавить в систему</button>
        </div>
    </div>

    <!-- Карточки экранов -->
    <div v-if="getScreens().length === 0" class="text-center py-8 text-emerald-600 border border-dashed border-emerald-200 rounded-lg bg-emerald-50/50">
        Нет подключенных экранов
    </div>
    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <div v-for="screen in getScreens()" :key="screen.id" class="bg-emerald-50/60 border border-emerald-200 rounded-xl p-4 shadow-sm hover:shadow transition flex flex-col justify-between">
            <div class="flex justify-between items-start mb-3">
                <div>
                    <h4 class="font-semibold text-emerald-900 text-sm">{{ screen.name }}</h4>
                    <span class="text-[10px] text-emerald-600 uppercase tracking-wider font-semibold">{{ screen.city_id || screen.city }}</span>
                </div>
                <div class="flex flex-col items-end gap-2">
                    <span :class="screen.status === 'В сети' ? 'bg-emerald-100 text-emerald-800 border-emerald-300' : 'bg-red-100 text-red-800 border-red-300'" class="text-[10px] px-2 py-0.5 rounded-full border font-medium flex items-center gap-1">
                        <span :class="screen.status === 'В сети' ? 'bg-emerald-500' : 'bg-red-500'" class="w-1.5 h-1.5 rounded-full"></span>
                        {{ screen.status }}
                    </span>
                    <!-- Кнопка удаления для админа -->
                    <button v-if="props.auth.login.value === 'admin_main'" @click="props.confirm($event, `Точно удалить экран ${screen.name}?`, () => deleteScreen(screen.id))" class="text-[10px] text-red-500 hover:text-red-700 underline">Удалить</button>
                </div>
            </div>
            <div class="text-[11px] text-emerald-700/80 bg-white/60 p-2 rounded border border-emerald-100 flex justify-between items-center">
                <span>ID: {{ screen.id }}</span>
                <span class="font-mono">Подключен</span>
            </div>
        </div>
    </div>

</div>
</template>