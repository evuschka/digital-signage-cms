<script setup>
const props = defineProps(['reports', 'helpers']);
const { analyticsData, activityHistory, storageHistory, chartStatusRef, chartCityRef, fetchHistory, fetchStorageHistory } = props.reports;
const { formatDate, formatSize } = props.helpers;
</script>

<template>
    <div class="space-y-6">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div class="bg-emerald-50 border border-emerald-200 rounded-xl p-6 shadow-sm flex flex-col justify-center items-center">
                <h3 class="text-emerald-700 text-sm font-semibold uppercase tracking-wide">Запланировано показов</h3>
                <p class="text-5xl font-bold text-emerald-900 mt-2">{{ analyticsData.total_shows }}</p>
            </div>
            <div class="bg-emerald-50 border border-emerald-200 rounded-xl p-6 shadow-sm flex flex-col justify-center items-center">
                <h3 class="text-emerald-700 text-sm font-semibold uppercase tracking-wide">Суммарное время (часы)</h3>
                <p class="text-5xl font-bold text-emerald-900 mt-2">{{ analyticsData.total_hours }}</p>
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

        <div class="bg-white border border-emerald-200 rounded-xl p-6 shadow-sm">
            <div class="flex justify-between items-center mb-4">
                <div>
                    <h3 class="text-emerald-900 font-semibold">Системный журнал событий</h3>
                    <p class="text-xs text-emerald-600 mt-0.5">Фиксация действий пользователей, системы и операций с файлами</p>
                </div>
                <button @click="fetchHistory" class="text-xs bg-emerald-100 hover:bg-emerald-200 text-emerald-800 px-3 py-1.5 rounded-md font-medium">Обновить журнал</button>
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
                        <tr v-if="activityHistory.length === 0">
                            <td colspan="4" class="px-4 py-8 text-center text-emerald-600">Журнал событий пуст</td>
                        </tr>
                        <tr v-for="log in activityHistory" :key="log.id" class="border-b border-emerald-50 hover:bg-emerald-50/50 text-xs">
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

        <div class="bg-white border border-emerald-200 rounded-xl p-6 shadow-sm mt-6">
            <div class="flex justify-between items-center mb-4">
                <h3 class="text-emerald-900 font-semibold">История содержимого в хранилище</h3>
                <button @click="fetchStorageHistory" class="text-xs bg-emerald-100 hover:bg-emerald-200 text-emerald-800 px-3 py-1.5 rounded-md font-medium">Обновить</button>
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
                        <tr v-if="storageHistory.length === 0">
                            <td colspan="5" class="px-4 py-8 text-center text-emerald-600">История хранилища пуста</td>
                        </tr>
                        <tr v-for="item in storageHistory" :key="item.id" class="border-b border-emerald-50 hover:bg-emerald-50/50 text-xs">
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
</template>