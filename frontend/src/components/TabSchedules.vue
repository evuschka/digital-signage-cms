<script setup>
const props = defineProps(['schedules', 'playlists', 'media', 'auth', 'requestConfirm']);

// Вытаскиваем ВСЕ нужные переменные из composable
const { 
    schedules: schedulesList, 
    showAddModal, 
    scheduleType, 
    newSchedule, 
    availableScreens, 
    selectAllScreens, 
    onCityChange, 
    openScheduleModal, 
    addSchedule, 
    deleteSchedule 
} = props.schedules;

const { playlists: playlistsList } = props.playlists;
const { files } = props.media;
const { login } = props.auth;

const getPlaylistName = (id) => props.playlists.playlists.value.find(p => p.id === id)?.name || 'Неизвестный';
</script>

<template>
    <div class="space-y-6">
        <div class="flex justify-between items-center">
            <h2 class="text-xl font-semibold text-emerald-900">График трансляций (Smart Planner)</h2>
            <button v-if="login === 'admin_main'" @click="openScheduleModal" class="bg-emerald-600 text-white px-4 py-2 rounded-lg text-sm shadow-sm hover:bg-emerald-700 transition cursor-pointer border-0">+ Запланировать</button>
        </div>

        <!-- ФОРМА ДОБАВЛЕНИЯ -->
        <div v-show="showAddModal" class="bg-emerald-50 border border-emerald-200 rounded-xl p-6 shadow-md">
            <h3 class="text-lg font-medium mb-4 text-emerald-800">Новый запуск</h3>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
                
                <div class="sm:col-span-2 flex gap-4 bg-white p-3 rounded-lg border border-emerald-200">
                    <label class="flex items-center gap-2 text-xs font-medium cursor-pointer">
                        <input type="radio" value="file" v-model="scheduleType" @change="newSchedule.playlist_id = null" class="accent-emerald-600"> Отдельный файл
                    </label>
                    <label class="flex items-center gap-2 text-xs font-medium cursor-pointer">
                        <input type="radio" value="playlist" v-model="scheduleType" @change="newSchedule.file = ''" class="accent-emerald-600"> Плейлист
                    </label>
                </div>

                <div class="sm:col-span-2">
                    <label class="block text-xs text-emerald-700 mb-1 font-medium">{{ scheduleType === 'file' ? 'Выберите файл' : 'Выберите плейлист' }}</label>
                    <select v-if="scheduleType === 'file'" v-model="newSchedule.file" class="w-full bg-white border border-emerald-300 rounded p-2.5 text-sm focus:outline-none focus:border-emerald-600">
                        <option value="">-- Выберите файл --</option>
                        <option v-for="f in files" :key="f.name" :value="f.name">{{ f.name }}</option>
                    </select>
                    <select v-else v-model="newSchedule.playlist_id" class="w-full bg-white border border-emerald-300 rounded p-2.5 text-sm focus:outline-none focus:border-emerald-600">
                        <option :value="null">-- Выберите плейлист --</option>
                        <option v-for="pl in playlistsList" :key="pl.id" :value="pl.id">📑 {{ pl.name }}</option>
                    </select>
                </div>

                <div class="sm:col-span-2">
                    <label class="block text-xs text-emerald-700 mb-1 font-medium">Филиал (Город)</label>
                    <select v-model="newSchedule.city" @change="onCityChange" class="w-full bg-white border border-emerald-300 rounded p-2.5 text-sm focus:outline-none focus:border-emerald-600">
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

                <!-- БЛОК ЦЕЛЕВЫХ ЭКРАНОВ -->
                <div v-if="newSchedule.city !== 'global' && availableScreens.length > 0" class="sm:col-span-2 bg-white p-4 rounded-lg border border-emerald-200 shadow-sm">
                    <div class="flex justify-between items-center mb-2">
                        <label class="block text-xs font-semibold text-emerald-800">Целевые экраны:</label>
                        <button type="button" @click="selectAllScreens" class="text-xs text-emerald-600 hover:text-emerald-800 underline bg-transparent border-0 cursor-pointer font-medium">Выбрать все / Снять</button>
                    </div>
                    <div class="flex flex-wrap gap-2 mt-1">
                        <label v-for="scr in availableScreens" :key="scr" class="flex items-center gap-2 text-xs bg-emerald-50 px-3 py-1.5 rounded-md border border-emerald-200 cursor-pointer hover:border-emerald-400 select-none transition">
                            <input type="checkbox" :value="scr" v-model="newSchedule.screens" class="accent-emerald-600 w-3.5 h-3.5 rounded">
                            <span class="font-medium text-emerald-950">{{ scr }}</span>
                        </label>
                    </div>
                </div>
                
                <div>
                    <label class="block text-xs text-emerald-700 mb-1 font-medium">Время начала</label>
                    <input id="time_start_picker" type="text" placeholder="Выберите дату и время" class="w-full bg-white border border-emerald-300 rounded p-2 text-sm cursor-pointer focus:outline-none focus:border-emerald-600">
                </div>
                <div>
                    <label class="block text-xs text-emerald-700 mb-1 font-medium">Время окончания</label>
                    <input id="time_end_picker" type="text" placeholder="Выберите дату и время" class="w-full bg-white border border-emerald-300 rounded p-2 text-sm cursor-pointer focus:outline-none focus:border-emerald-600">
                </div>
            </div>
            
            <div class="flex justify-end gap-3">
                <button @click="showAddModal = false" class="bg-emerald-200 text-emerald-900 px-4 py-2 rounded text-sm hover:bg-emerald-300 transition cursor-pointer border-0">Отмена</button>
                <button @click="addSchedule($event)" class="bg-emerald-600 text-white px-4 py-2 rounded text-sm hover:bg-emerald-700 transition cursor-pointer border-0">Сохранить</button>
            </div>
        </div>
        
        <!-- ТАБЛИЦА РАСПИСАНИЙ -->
        <div class="bg-emerald-50 border border-emerald-200 rounded-xl p-6 shadow-sm overflow-x-auto">
            <table v-if="schedulesList.length > 0" class="w-full text-sm text-left text-emerald-900">
                <thead class="text-xs text-emerald-800 uppercase bg-emerald-100/70 border-b border-emerald-200">
                    <tr>
                        <th class="px-6 py-3">Контент</th>
                        <th class="px-6 py-3">Филиал / Экраны</th>
                        <th class="px-6 py-3">Время</th>
                        <th class="px-6 py-3">Статус</th>
                        <th v-if="login === 'admin_main'" class="px-6 py-3">Действия</th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="item in schedulesList" :key="item.id" class="border-b border-emerald-200 hover:bg-emerald-100/40 transition">
                        <td class="px-6 py-4 font-medium">
                            <span v-if="item.playlist_id" class="text-emerald-700 font-bold">📑 {{ getPlaylistName(item.playlist_id) }}</span>
                            <span v-else>📁 {{ item.file }}</span>
                        </td>
                        <td class="px-6 py-4 text-xs">
                            <span class="font-bold text-emerald-800 uppercase">{{ item.city }}</span><br>
                            <span class="text-slate-500">{{ !item.screens || item.screens.length === 0 ? 'Все экраны' : item.screens.join(', ') }}</span>
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
                        <td v-if="login === 'admin_main'" class="px-6 py-4">
                            <button @click="requestConfirm($event, 'Удалить из расписания?', () => deleteSchedule(item.id))" class="text-red-700 hover:text-red-900 font-medium text-xs cursor-pointer border-0 bg-transparent hover:underline">Удалить</button>
                        </td>
                    </tr>
                </tbody>
            </table>
            <div v-else class="text-center py-8 text-emerald-600 bg-white rounded-lg border border-dashed border-emerald-200">Расписание пока пусто.</div>
        </div>
    </div>
</template>