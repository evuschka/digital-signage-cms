<script setup>
const props = defineProps(['media', 'helpers', 'requestConfirm', 'showToast']);
const { trashFiles, emptyTrash, restoreFile } = props.media;
const { formatDate, getRemainingDays } = props.helpers;
</script>

<template>
    <div class="bg-emerald-50 border border-emerald-200 rounded-xl p-6 shadow-sm">
        <div class="flex justify-between items-center mb-4">
            <h2 class="text-xl font-semibold text-emerald-900">Корзина (хранение до 30 дней)</h2>
            <button @click="trashFiles.length > 0 ? requestConfirm($event, 'Очистить корзину навсегда?', emptyTrash) : showToast('Корзина уже пуста!', 'info')" 
                    :class="trashFiles.length === 0 ? 'opacity-50 cursor-not-allowed' : 'hover:bg-red-200 cursor-pointer'" 
                    class="text-xs bg-red-100 text-red-800 px-4 py-2 rounded-md border border-red-200 font-bold transition">
                🗑️ Очистить всё
            </button>
        </div>
        <div v-if="trashFiles.length === 0" class="text-center py-12 text-emerald-600 border border-dashed border-emerald-200 rounded-lg bg-white">Корзина пуста.</div>
        <div v-else class="space-y-3">
            <div v-for="file in trashFiles" :key="file.name" class="bg-white border border-emerald-200 p-4 rounded-lg flex justify-between items-center shadow-sm">
                <div>
                    <p class="font-medium text-emerald-900 text-sm">{{ file.name }}</p>
                    <p class="text-[11px] text-emerald-600 mt-0.5">
                        Удалено: {{ formatDate(file.deleted_at) }} | 
                        <span class="font-semibold text-amber-700">{{ getRemainingDays(file.deleted_at) }}</span>
                    </p>
                </div>
                <button @click="restoreFile(file.name)" class="bg-emerald-600 hover:bg-emerald-700 text-white text-xs px-4 py-2 rounded-md shadow-sm">Восстановить</button>
            </div>
        </div>
    </div>
</template>