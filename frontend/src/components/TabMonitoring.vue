<script setup>
import { ref, onMounted, computed } from 'vue';

const props = defineProps({
    reports: Object
});

const selectedCity = ref('moscow');
const selectedScreenIndex = ref(0);

const currentItem = ref(null);
const mediaList = ref([]);
const currentIndex = ref(0);
const intervalTimer = ref(null);
const isVideoPlaying = ref(false);

const cityScreensMap = {
    global: ['Общая сеть (Global)'],
    moscow: ['Москва — Экран 1', 'Москва — Экран 2', 'Москва — Экран 3'],
    spb: ['СПб — Экран 1', 'СПб — Экран 2'],
    novocheboksarsk: ['Новочебоксарск — Экран 1'],
    yartsevo: ['Ярцево — Экран 1'],
    azov: ['Азов — Экран 1'],
    orenburg: ['Оренбург — Экран 1'],
    chernyakhovsk: ['Черняховск — Экран 1']
};

const currentScreensList = computed(() => {
    return cityScreensMap[selectedCity.value] || ['Экран 1'];
});

const fetchActiveSchedule = async () => {
    try {
        const response = await fetch(`/api/schedules/active?city=${selectedCity.value}&screen=${selectedScreenIndex.value}`);
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
};

onMounted(() => {
    fetchActiveSchedule();
    handleRefreshStatus();
});

const staticScreens = [
    { name: 'Москва-Экран-1', city: 'MOSCOW', status: 'В сети', last_ping: 'только что' },
    { name: 'Москва-Экран-2', city: 'MOSCOW', status: 'В сети', last_ping: 'только что' },
    { name: 'Москва-Экран-3', city: 'MOSCOW', status: 'В сети', last_ping: 'только что' },
    { name: 'СПб-Экран-1', city: 'SPB', status: 'Офлайн', last_ping: '2 мин назад' },
    { name: 'СПб-Экран-2', city: 'SPB', status: 'В сети', last_ping: 'только что' },
    { name: 'Новочебоксарск-Экран-1', city: 'NOVOCHEBOKSARSK', status: 'Офлайн', last_ping: '5 мин назад' },
    { name: 'Ярцево-Экран-1', city: 'YARTSEVO', status: 'В сети', last_ping: 'только что' },
    { name: 'Азов-Экран-1', city: 'AZOV', status: 'В сети', last_ping: 'только что' },
    { name: 'Оренбург-Экран-1', city: 'ORENBURG', status: 'В сети', last_ping: 'только что' },
    { name: 'Черняховск-Экран-1', city: 'CHERNYAKHOVSK', status: 'В сети', last_ping: 'только что' },
];

const getScreens = () => {
    const list = props.reports?.screensList?.value || props.reports?.screensList;
    if (Array.isArray(list) && list.length > 0) return list;
    return staticScreens;
};
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
                    <option value="moscow">Москва (3 экрана)</option>
                    <option value="spb">Санкт-Петербург (2 экрана)</option>
                    <option value="novocheboksarsk">Новочебоксарск (1 экран)</option>
                    <option value="yartsevo">Ярцево (1 экран)</option>
                    <option value="azov">Азов (1 экран)</option>
                    <option value="orenburg">Оренбург (1 экран)</option>
                    <option value="chernyakhovsk">Черняховск (1 экран)</option>
                </select>

                <select v-if="currentScreensList.length > 1" v-model="selectedScreenIndex" @change="fetchActiveSchedule()" class="bg-emerald-700 text-white text-xs px-3 py-2 rounded-lg font-medium outline-none focus:bg-emerald-800 shadow-sm cursor-pointer">
                    <option v-for="(screenName, index) in currentScreensList" :key="index" :value="index">
                        Экран {{ index + 1 }}
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
                <img v-else-if="!isVideoPlaying" :src="`/uploads/${currentItem.file || currentItem}`" class="w-full h-full object-contain">
                <video v-else :src="`/uploads/${currentItem.file || currentItem}`" autoplay muted playsinline @ended="handleVideoEnded" class="w-full h-full object-contain"></video>

                <div class="absolute bottom-3 left-3 bg-black/60 backdrop-blur-md text-white/80 text-[11px] px-2.5 py-1 rounded border border-white/10">
                    Эфир: <span class="text-emerald-400 font-bold uppercase">{{ currentScreensList[selectedScreenIndex] || selectedCity }}</span> | Слайд: {{ currentIndex + 1 }}/{{ mediaList.length }}
                </div>
            </div>
            <div v-else class="text-gray-400 text-xs animate-pulse">
                Загрузка трансляции...
            </div>
        </div>
    </div>

    <!-- СЕТКА МОНИТОРИНГА С КНОПКОЙ ОБНОВЛЕНИЯ -->
    <div class="flex justify-between items-center pt-2">
        <h2 class="text-xl font-bold text-emerald-900">Мониторинг сети экранов</h2>
        <button @click="handleRefreshStatus" class="bg-emerald-600 hover:bg-emerald-700 text-white text-xs px-4 py-2 rounded-lg transition font-medium shadow-sm cursor-pointer">Обновить статус</button>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <div v-for="screen in getScreens()" :key="screen.name" class="bg-emerald-50/60 border border-emerald-200 rounded-xl p-4 shadow-sm hover:shadow transition flex flex-col justify-between">
            <div class="flex justify-between items-start mb-3">
                <div>
                    <h4 class="font-semibold text-emerald-900 text-sm">{{ screen.name }}</h4>
                    <span class="text-[10px] text-emerald-600 uppercase tracking-wider font-semibold">{{ screen.city }}</span>
                </div>
                <span :class="screen.status === 'В сети' ? 'bg-emerald-100 text-emerald-800 border-emerald-300' : 'bg-red-100 text-red-800 border-red-300'" class="text-[10px] px-2 py-0.5 rounded-full border font-medium flex items-center gap-1">
                    <span :class="screen.status === 'В сети' ? 'bg-emerald-500' : 'bg-red-500'" class="w-1.5 h-1.5 rounded-full"></span>
                    {{ screen.status }}
                </span>
            </div>
            <div class="text-[11px] text-emerald-700/80 bg-white/60 p-2 rounded border border-emerald-100 flex justify-between items-center">
                <span>Последний пинг:</span>
                <span class="font-mono">{{ screen.last_ping || 'только что' }}</span>
            </div>
        </div>
    </div>

</div>
</template>