<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';

const props = defineProps({
    schedules: Object,
    playlists: Object,
    media: Object,
    auth: Object,
    requestConfirm: Function
});

const isFormOpen = ref(true);

const fallbackScreens = {
    moscow: ['Москва-Экран-1', 'Москва-Экран-2', 'Москва-Экран-3'],
    spb: ['СПБ-Экран-1', 'СПБ-Экран-2'],
    novocheboksarsk: ['Новочебоксарск-Экран-1'],
    yartsevo: ['Ярцево-Экран-1'],
    azov: ['Азов-Экран-1'],
    orenburg: ['Оренбург-Экран-1'],
    chernyakhovsk: ['Черняховск-Экран-1']
};

const screensMap = computed(() => {
    const fromApi = props.schedules?.screens?.value ?? props.schedules?.screens ?? {};
    return Object.keys(fromApi).length > 0 ? fromApi : fallbackScreens;
});

const form = computed(() => {
    return props.schedules?.newSchedule?.value ?? props.schedules?.newSchedule ?? {};
});

const cityTimezones = {
    global: { name: 'МСК', offset: 3 },
    moscow: { name: 'МСК', offset: 3 },
    spb: { name: 'МСК', offset: 3 },
    novocheboksarsk: { name: 'МСК', offset: 3 },
    yartsevo: { name: 'МСК', offset: 3 },
    azov: { name: 'МСК', offset: 3 },
    orenburg: { name: 'ЕКБ (+2 МСК)', offset: 5 },
    chernyakhovsk: { name: 'КЛГ (-1 МСК)', offset: 2 }
};

const currentTimeString = ref('');
let timer = null;

const updateClock = () => {
    const city = form.value.city || 'moscow';
    const tz = cityTimezones[city] || { offset: 3 };
    const now = new Date();
    const utc = now.getTime() + (now.getTimezoneOffset() * 60000);
    const cityDate = new Date(utc + (3600000 * tz.offset));
    
    const h = String(cityDate.getHours()).padStart(2, '0');
    const m = String(cityDate.getMinutes()).padStart(2, '0');
    const s = String(cityDate.getSeconds()).padStart(2, '0');
    currentTimeString.value = `${h}:${m}:${s}`;
};

onMounted(() => {
    updateClock();
    timer = setInterval(updateClock, 1000);
    if (!form.value.type) form.value.type = 'file';
    if (!form.value.time_start) form.value.time_start = '2026-09-16 12:53';
    if (!form.value.time_end) form.value.time_end = '2026-09-16 12:57';
});

onUnmounted(() => {
    clearInterval(timer);
});

const currentScreens = computed(() => {
    const city = form.value.city;
    if (!city || city === 'global') return [];
    return screensMap.value[city] || [];
});

const onCityChange = () => {
    const city = form.value.city;
    if (city === 'global') {
        form.value.screens = [];
        return;
    }
    const screens = screensMap.value[city] || [];
    if (screens.length === 1) {
        form.value.screens = [screens[0]];
    } else {
        form.value.screens = [];
    }
    updateClock();
};

const toggleSelectAll = () => {
    if (!currentScreens.value.length) return;
    if (form.value.screens.length === currentScreens.value.length) {
        form.value.screens = [];
    } else {
        form.value.screens = [...currentScreens.value];
    }
};

// --- Всплывающие календари с вводом времени с клавиатуры ---
const activePicker = ref(null);
const calYear = ref(2026);
const calMonth = ref(8);
const selectedDay = ref(16);
const calHours = ref(12);
const calMinutes = ref(53);

const monthsNames = [
    'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
    'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'
];

const calendarDays = computed(() => {
    const days = [];
    const firstDayIndex = new Date(calYear.value, calMonth.value, 1).getDay();
    const startOffset = (firstDayIndex + 6) % 7;
    const daysInMonth = new Date(calYear.value, calMonth.value + 1, 0).getDate();
    const prevMonthDays = new Date(calYear.value, calMonth.value, 0).getDate();

    for (let i = startOffset - 1; i >= 0; i--) {
        days.push({ day: prevMonthDays - i, isCurrent: false });
    }
    for (let i = 1; i <= daysInMonth; i++) {
        days.push({ day: i, isCurrent: true });
    }
    const remaining = 42 - days.length;
    for (let i = 1; i <= remaining; i++) {
        days.push({ day: i, isCurrent: false });
    }
    return days;
});

const prevMonth = () => {
    if (calMonth.value === 0) {
        calMonth.value = 11;
        calYear.value--;
    } else {
        calMonth.value--;
    }
};

const nextMonth = () => {
    if (calMonth.value === 11) {
        calMonth.value = 0;
        calYear.value++;
    } else {
        calMonth.value++;
    }
};

const selectDay = (item) => {
    if (!item.isCurrent) return;
    selectedDay.value = item.day;
    applyCalendarTime();
};

const applyCalendarTime = () => {
    // Валидация ввода с клавиатуры
    if (calHours.value > 23) calHours.value = 23;
    if (calHours.value < 0 || isNaN(calHours.value)) calHours.value = 0;
    
    if (calMinutes.value > 59) calMinutes.value = 59;
    if (calMinutes.value < 0 || isNaN(calMinutes.value)) calMinutes.value = 0;

    const y = calYear.value;
    const m = String(calMonth.value + 1).padStart(2, '0');
    const d = String(selectedDay.value).padStart(2, '0');
    const h = String(calHours.value).padStart(2, '0');
    const min = String(calMinutes.value).padStart(2, '0');
    const formatted = `${y}-${m}-${d} ${h}:${min}`;

    if (activePicker.value === 'start') {
        form.value.time_start = formatted;
    } else if (activePicker.value === 'end') {
        form.value.time_end = formatted;
    }
};

const openPicker = (type) => {
    activePicker.value = activePicker.value === type ? null : type;
};

const scheduleList = computed(() => props.schedules?.schedules?.value ?? props.schedules?.schedules ?? []);
const playlistList = computed(() => props.playlists?.playlists?.value ?? props.playlists?.playlists ?? []);
const mediaList = computed(() => props.media?.files?.value ?? props.media?.files ?? []);

const submitSchedule = () => {
    props.schedules.createSchedule();
};
</script>

<template>
<div class="space-y-6 text-left font-sans">
    <div class="flex justify-between items-center">
        <div>
            <h2 class="text-xl font-bold text-emerald-900 m-0">График трансляций (Smart Planner)</h2>
        </div>
        <button 
            v-if="props.auth.login.value === 'admin_main'"
            @click="isFormOpen = !isFormOpen" 
            class="bg-emerald-600 hover:bg-emerald-700 text-white text-xs px-4 py-2 rounded-lg transition font-medium shadow-sm cursor-pointer border-0">
            + Запланировать
        </button>
    </div>

    <!-- Форма «Новый запуск (с проверкой конфликтов)» -->
    <div v-if="props.auth.login.value === 'admin_main' && isFormOpen" class="bg-emerald-50/40 border border-emerald-200/80 rounded-2xl p-6 shadow-sm space-y-5">
        <h3 class="text-sm font-bold text-emerald-950 m-0">Новый запуск (с проверкой конфликтов)</h3>

        <!-- Радио-кнопки переключения типа контента -->
        <div class="flex items-center gap-6 text-xs text-emerald-950 font-medium">
            <label class="flex items-center gap-2 cursor-pointer select-none">
                <input type="radio" value="file" v-model="form.type" class="accent-emerald-600">
                <span>Отдельный файл</span>
            </label>
            <label class="flex items-center gap-2 cursor-pointer select-none">
                <input type="radio" value="playlist" v-model="form.type" class="accent-emerald-600">
                <span>Плейлист (Ряд)</span>
            </label>
        </div>

        <div class="space-y-4 max-w-xl">
            <!-- Динамическое поле: Выберите файл ИЛИ Выберите плейлист -->
            <div>
                <template v-if="form.type === 'file'">
                    <label class="block text-xs font-semibold text-emerald-900 mb-1.5">Выберите файл</label>
                    <select v-model="form.file" class="w-full px-3.5 py-2.5 bg-white text-emerald-950 border border-emerald-300 rounded-xl text-xs focus:outline-none focus:border-emerald-500 shadow-sm">
                        <option value="">-- Выберите файл --</option>
                        <option v-for="f in mediaList" :key="f.name" :value="f.name">{{ f.name }}</option>
                    </select>
                </template>
                <template v-else>
                    <label class="block text-xs font-semibold text-emerald-900 mb-1.5">Выберите плейлист</label>
                    <select v-model="form.playlist_id" class="w-full px-3.5 py-2.5 bg-white text-emerald-950 border border-emerald-300 rounded-xl text-xs focus:outline-none focus:border-emerald-500 shadow-sm">
                        <option :value="null">-- Выберите плейлист --</option>
                        <option v-for="pl in playlistList" :key="pl.id" :value="pl.id">{{ pl.name }}</option>
                    </select>
                </template>
            </div>

            <!-- Филиал (Город) -->
            <div>
                <label class="block text-xs font-semibold text-emerald-900 mb-1.5">Филиал (Город)</label>
                <select v-model="form.city" @change="onCityChange" class="w-full px-3.5 py-2.5 bg-white text-emerald-950 border border-emerald-300 rounded-xl text-xs focus:outline-none focus:border-emerald-500 shadow-sm">
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

            <!-- Часовой пояс -->
            <div class="flex items-center gap-2 text-xs text-emerald-800 bg-emerald-100/50 border border-emerald-200 px-3.5 py-2.5 rounded-xl">
                <span class="w-2.5 h-2.5 rounded-full bg-emerald-500 shrink-0"></span>
                <span>Часовой пояс: <strong>{{ cityTimezones[form.city || 'moscow']?.name }}</strong>. Текущее время в филиале: <strong class="font-mono">{{ currentTimeString }}</strong></span>
            </div>

            <!-- Целевые экраны -->
            <div v-if="form.city && form.city !== 'global' && currentScreens.length > 0">
                <div class="flex justify-between items-center mb-1.5">
                    <label class="text-xs font-semibold text-emerald-900">Целевые экраны:</label>
                    <button type="button" @click="toggleSelectAll" class="text-[11px] text-emerald-700 hover:text-emerald-900 font-medium bg-transparent border-0 cursor-pointer">Выбрать все</button>
                </div>
                <div class="flex flex-wrap gap-2">
                    <label v-for="scr in currentScreens" :key="scr" class="flex items-center gap-2 text-xs bg-white text-emerald-950 px-3 py-2 rounded-xl border border-emerald-200 hover:border-emerald-400 cursor-pointer transition select-none shadow-sm">
                        <input type="checkbox" :value="scr" v-model="form.screens" class="accent-emerald-600 rounded">
                        <span>{{ scr }}</span>
                    </label>
                </div>
            </div>

            <!-- Поля времени начала и окончания со всплывающими календарями -->
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                
                <!-- Начало -->
                <div class="relative">
                    <label class="block text-xs font-semibold text-emerald-900 mb-1.5">Начало (местное время филиала)</label>
                    <input 
                        v-model="form.time_start" 
                        readonly
                        @click="openPicker('start')"
                        placeholder="2026-09-16 12:53"
                        class="w-full px-3.5 py-2.5 bg-white text-emerald-950 border border-emerald-300 rounded-xl text-xs focus:outline-none focus:border-emerald-500 shadow-sm font-mono cursor-pointer">

                    <!-- Всплывающий календарь для Начала -->
                    <div v-if="activePicker === 'start'" class="absolute bottom-full mb-2 left-0 w-72 bg-white border border-gray-200 rounded-xl shadow-xl p-4 z-50 text-left">
                        <div class="flex justify-between items-center text-xs font-semibold text-gray-800 mb-3 px-1">
                            <button type="button" @click="prevMonth" class="text-gray-400 hover:text-gray-700 bg-transparent border-0 cursor-pointer text-base leading-none">‹</button>
                            <div class="flex items-center gap-1 cursor-pointer">
                                <span>{{ monthsNames[calMonth] }}</span>
                                <span class="text-[10px]">⌄</span>
                                <span>{{ calYear }}</span>
                            </div>
                            <button type="button" @click="nextMonth" class="text-gray-400 hover:text-gray-700 bg-transparent border-0 cursor-pointer text-base leading-none">›</button>
                        </div>

                        <div class="grid grid-cols-7 text-center text-[11px] font-semibold text-gray-600 mb-1">
                            <div>Пн</div><div>Вт</div><div>Ср</div><div>Чт</div><div>Пт</div><div>Сб</div><div>Вс</div>
                        </div>

                        <div class="grid grid-cols-7 text-center text-xs gap-y-1">
                            <div 
                                v-for="(item, idx) in calendarDays" 
                                :key="idx"
                                @click="selectDay(item)"
                                class="py-1 rounded-full cursor-pointer transition select-none flex items-center justify-center mx-auto w-7 h-7 text-[12px]"
                                :class="{
                                    'text-gray-300 pointer-events-none': !item.isCurrent,
                                    'border border-gray-400 text-gray-900 font-medium': item.isCurrent && item.day === selectedDay,
                                    'text-gray-700 hover:bg-gray-100': item.isCurrent && item.day !== selectedDay
                                }">
                                {{ item.day }}
                            </div>
                        </div>

                        <!-- Инпуты ввода часов и минут с клавиатуры -->
                        <div class="flex items-center justify-center gap-2 pt-3 mt-3 border-t border-gray-100">
                            <input 
                                type="number" 
                                min="0" 
                                max="23" 
                                v-model.number="calHours" 
                                @input="applyCalendarTime"
                                class="w-12 text-center font-bold text-sm bg-gray-50 border border-gray-200 rounded-lg py-1 focus:outline-none focus:border-emerald-600">

                            <span class="font-bold text-sm text-gray-900">:</span>

                            <input 
                                type="number" 
                                min="0" 
                                max="59" 
                                v-model.number="calMinutes" 
                                @input="applyCalendarTime"
                                class="w-12 text-center font-bold text-sm bg-gray-50 border border-gray-200 rounded-lg py-1 focus:outline-none focus:border-emerald-600">
                        </div>

                        <div class="text-right mt-2">
                            <button type="button" @click="activePicker = null" class="text-[11px] text-emerald-700 font-semibold bg-transparent border-0 cursor-pointer hover:underline">Готово</button>
                        </div>
                    </div>
                </div>

                <!-- Окончание -->
                <div class="relative">
                    <label class="block text-xs font-semibold text-emerald-900 mb-1.5">Окончание (местное время филиала)</label>
                    <input 
                        v-model="form.time_end" 
                        readonly
                        @click="openPicker('end')"
                        placeholder="2026-09-16 12:57"
                        class="w-full px-3.5 py-2.5 bg-white text-emerald-950 border border-emerald-300 rounded-xl text-xs focus:outline-none focus:border-emerald-500 shadow-sm font-mono cursor-pointer">

                    <!-- Всплывающий календарь для Окончания -->
                    <div v-if="activePicker === 'end'" class="absolute bottom-full mb-2 left-0 w-72 bg-white border border-gray-200 rounded-xl shadow-xl p-4 z-50 text-left">
                        <div class="flex justify-between items-center text-xs font-semibold text-gray-800 mb-3 px-1">
                            <button type="button" @click="prevMonth" class="text-gray-400 hover:text-gray-700 bg-transparent border-0 cursor-pointer text-base leading-none">‹</button>
                            <div class="flex items-center gap-1 cursor-pointer">
                                <span>{{ monthsNames[calMonth] }}</span>
                                <span class="text-[10px]">⌄</span>
                                <span>{{ calYear }}</span>
                            </div>
                            <button type="button" @click="nextMonth" class="text-gray-400 hover:text-gray-700 bg-transparent border-0 cursor-pointer text-base leading-none">›</button>
                        </div>

                        <div class="grid grid-cols-7 text-center text-[11px] font-semibold text-gray-600 mb-1">
                            <div>Пн</div><div>Вт</div><div>Ср</div><div>Чт</div><div>Пт</div><div>Сб</div><div>Вс</div>
                        </div>

                        <div class="grid grid-cols-7 text-center text-xs gap-y-1">
                            <div 
                                v-for="(item, idx) in calendarDays" 
                                :key="idx"
                                @click="selectDay(item)"
                                class="py-1 rounded-full cursor-pointer transition select-none flex items-center justify-center mx-auto w-7 h-7 text-[12px]"
                                :class="{
                                    'text-gray-300 pointer-events-none': !item.isCurrent,
                                    'border border-gray-400 text-gray-900 font-medium': item.isCurrent && item.day === selectedDay,
                                    'text-gray-700 hover:bg-gray-100': item.isCurrent && item.day !== selectedDay
                                }">
                                {{ item.day }}
                            </div>
                        </div>

                        <!-- Инпуты ввода часов и минут с клавиатуры -->
                        <div class="flex items-center justify-center gap-2 pt-3 mt-3 border-t border-gray-100">
                            <input 
                                type="number" 
                                min="0" 
                                max="23" 
                                v-model.number="calHours" 
                                @input="applyCalendarTime"
                                class="w-12 text-center font-bold text-sm bg-gray-50 border border-gray-200 rounded-lg py-1 focus:outline-none focus:border-emerald-600">

                            <span class="font-bold text-sm text-gray-900">:</span>

                            <input 
                                type="number" 
                                min="0" 
                                max="59" 
                                v-model.number="calMinutes" 
                                @input="applyCalendarTime"
                                class="w-12 text-center font-bold text-sm bg-gray-50 border border-gray-200 rounded-lg py-1 focus:outline-none focus:border-emerald-600">
                        </div>

                        <div class="text-right mt-2">
                            <button type="button" @click="activePicker = null" class="text-[11px] text-emerald-700 font-semibold bg-transparent border-0 cursor-pointer hover:underline">Готово</button>
                        </div>
                    </div>
                </div>

            </div>
        </div>

        <!-- Кнопки управления -->
        <div class="flex justify-end items-center gap-3 pt-4 border-t border-emerald-200/60">
            <button 
                type="button" 
                @click="isFormOpen = false" 
                class="px-5 py-2 border border-emerald-200 text-emerald-900 hover:bg-emerald-100/50 rounded-xl text-xs font-semibold bg-white cursor-pointer transition">
                Отмена
            </button>
            <button 
                type="button" 
                @click="submitSchedule" 
                class="px-6 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-semibold shadow-sm transition border-0 cursor-pointer">
                Сохранить
            </button>
        </div>
    </div>

    <!-- Таблица расписаний -->
    <div class="bg-white border border-emerald-200 rounded-xl overflow-hidden shadow-sm">
        <table class="w-full text-left text-xs border-collapse">
            <thead class="bg-emerald-50/70 border-b border-emerald-200 text-emerald-900">
                <tr>
                    <th class="p-3.5">Контент</th>
                    <th class="p-3.5">Город</th>
                    <th class="p-3.5">Экраны</th>
                    <th class="p-3.5">Интервал</th>
                    <th class="p-3.5">Статус</th>
                    <th v-if="props.auth.login.value === 'admin_main'" class="p-3.5 text-right">Действие</th>
                </tr>
            </thead>
            <tbody class="divide-y divide-emerald-100">
                <tr v-if="scheduleList.length === 0">
                    <td colspan="6" class="p-6 text-center text-gray-500">Расписания пока не созданы</td>
                </tr>
                <tr v-for="s in scheduleList" :key="s.id" class="hover:bg-emerald-50/30 transition">
                    <td class="p-3.5 font-semibold text-emerald-950">{{ s.file || `Плейлист ID ${s.playlist_id}` }}</td>
                    <td class="p-3.5">{{ s.city === 'global' ? 'Вся сеть' : s.city }}</td>
                    <td class="p-3.5">{{ s.screens && s.screens.length ? s.screens.join(', ') : 'Все экраны' }}</td>
                    <td class="p-3.5 font-mono text-[11px]">{{ s.time_start.replace('T', ' ') }} — {{ s.time_end.replace('T', ' ') }}</td>
                    <td class="p-3.5">
                        <span class="px-2.5 py-1 rounded-full text-[10px] font-semibold"
                            :class="{
                                'bg-emerald-100 text-emerald-800': s.status === 'Активен',
                                'bg-amber-100 text-amber-800': s.status === 'Ожидание',
                                'bg-gray-100 text-gray-700': s.status === 'Завершен'
                            }">
                            {{ s.status }}
                        </span>
                    </td>
                    <td v-if="props.auth.login.value === 'admin_main'" class="p-3.5 text-right">
                        <button @click="props.requestConfirm($event, 'Удалить это расписание?', () => props.schedules.deleteSchedule(s.id))" class="text-red-600 hover:text-red-800 font-medium cursor-pointer border-0 bg-transparent">Удалить</button>
                    </td>
                </tr>
            </tbody>
        </table>
    </div>
</div>
</template>