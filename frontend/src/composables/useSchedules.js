import { ref } from 'vue';

export function useSchedules(authHeader, showToast, requestConfirm, safeJson) {
    const schedules = ref([]); 
    const showAddModal = ref(false); 
    const scheduleType = ref('file');
    const newSchedule = ref({ file: '', playlist_id: null, city: 'global', screens: [], time_start: '', time_end: '' });
    
    // ЖЕЛЕЗОБЕТОННЫЙ ЗАПАС: вшиваем экраны сразу сюда, чтобы они всегда были доступны
    const allScreensMap = ref({
        moscow: ['Москва-Экран-1', 'Москва-Экран-2', 'Москва-Экран-3'],
        spb: ['СПБ-Экран-1', 'СПБ-Экран-2'],
        novocheboksarsk: ['Новочебоксарск-Экран-1'],
        yartsevo: ['Ярцево-Экран-1'],
        azov: ['Азов-Экран-1'],
        orenburg: ['Оренбург-Экран-1'],
        chernyakhovsk: ['Черняховск-Экран-1']
    }); 
    
    const availableScreens = ref([]);
    
    const cityTimezones = {
        global: { label: 'МСК', offset: 3 }, moscow: { label: 'МСК', offset: 3 }, spb: { label: 'МСК', offset: 3 }, novocheboksarsk: { label: 'МСК', offset: 3 },
        yartsevo: { label: 'МСК', offset: 3 }, azov: { label: 'МСК', offset: 3 }, orenburg: { label: 'МСК+2', offset: 5 }, chernyakhovsk: { label: 'МСК-1', offset: 2 }
    };

    const fetchScreens = async () => {
        try {
            const res = await fetch('/screens/', { headers: { 'Authorization': authHeader.value } });
            const data = await safeJson(res); 
            if (data.screens && Object.keys(data.screens).length > 0) {
                allScreensMap.value = data.screens;
            }
        } catch (e) {}
    };

    const fetchSchedules = async () => {
        try {
            const res = await fetch('/schedules/', { headers: { 'Authorization': authHeader.value } });
            const data = await safeJson(res); 
            schedules.value = data.schedules || [];
        } catch (e) {}
    };

    // Обновляем доступные экраны при смене города
    const onCityChange = () => {
        if (!newSchedule.value.city || newSchedule.value.city === 'global') {
            availableScreens.value = [];
            newSchedule.value.screens = [];
        } else {
            // Достаем из нашего гарантированного справочника
            availableScreens.value = allScreensMap.value[newSchedule.value.city] || [];
            newSchedule.value.screens = [...availableScreens.value]; // Сразу выделяем все чекбоксы
        }
    };

    const selectAllScreens = () => { 
        if (newSchedule.value.screens.length === availableScreens.value.length) {
            newSchedule.value.screens = []; // Снять все
        } else {
            newSchedule.value.screens = [...availableScreens.value]; // Выбрать все
        }
    };

    const openScheduleModal = () => {
        showAddModal.value = true;
        newSchedule.value.city = 'global'; // При открытии всегда сбрасываем на "Вся сеть"
        onCityChange();

        setTimeout(() => {
            if (window.flatpickr) {
                window.flatpickr("#time_start_picker", { 
                    enableTime: true, time_24hr: true, 
                    altInput: true, altFormat: "Y-m-d H:i", dateFormat: "Y-m-d\\TH:i:00", 
                    locale: "ru", defaultDate: newSchedule.value.time_start || null, 
                    onChange: (selectedDates, dateStr) => { newSchedule.value.time_start = dateStr; } 
                });
                window.flatpickr("#time_end_picker", { 
                    enableTime: true, time_24hr: true, 
                    altInput: true, altFormat: "Y-m-d H:i", dateFormat: "Y-m-d\\TH:i:00", 
                    locale: "ru", defaultDate: newSchedule.value.time_end || null, 
                    onChange: (selectedDates, dateStr) => { newSchedule.value.time_end = dateStr; } 
                });
            }
        }, 100);
    };

    const addSchedule = (e) => {
        if (scheduleType.value === 'file' && !newSchedule.value.file) return showToast('Выберите файл', 'warning');
        if (scheduleType.value === 'playlist' && !newSchedule.value.playlist_id) return showToast('Выберите плейлист', 'warning');
        if (!newSchedule.value.time_start || !newSchedule.value.time_end) return showToast('Заполните время', 'warning');

        const st = new Date(newSchedule.value.time_start);
        const en = new Date(newSchedule.value.time_end);
        const now = new Date(); 

        if (st < now) return showToast('Ошибка: нельзя запланировать трансляцию в прошлом!', 'error');
        if (en <= st) return showToast('Ошибка: время окончания должно быть позже времени начала', 'error');

        requestConfirm(e, 'Запланировать эту трансляцию?', async () => {
            const payload = { ...newSchedule.value, type: scheduleType.value };
            const res = await fetch('/schedules/', { 
                method: 'POST', 
                headers: { 'Authorization': authHeader.value, 'Content-Type': 'application/json' }, 
                body: JSON.stringify(payload) 
            });
            if (!res.ok) {
                const resData = await safeJson(res); 
                showToast(resData.detail || 'Ошибка сохранения', 'error');
            } else {
                newSchedule.value = { file: '', playlist_id: null, city: 'global', screens: [], time_start: '', time_end: '' };
                showAddModal.value = false; 
                fetchSchedules(); 
                showToast('Трансляция запланирована', 'success');
            }
        });
    };

    const deleteSchedule = async (id) => {
        await fetch(`/schedules/${id}`, { method: 'DELETE', headers: { 'Authorization': authHeader.value } });
        fetchSchedules(); 
        showToast('Трансляция удалена', 'info');
    };

    return { 
        schedules, showAddModal, scheduleType, newSchedule, allScreensMap, availableScreens, 
        cityTimezones, fetchScreens, fetchSchedules, onCityChange, 
        selectAllScreens, openScheduleModal, addSchedule, deleteSchedule 
    };
}