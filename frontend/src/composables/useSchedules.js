import { ref, onMounted, onUnmounted } from 'vue';

export function useSchedules(authHeader, showToast, requestConfirm, safeJson) {
    const schedules = ref([]); 
    const showAddModal = ref(false); 
    const scheduleType = ref('file');
    const newSchedule = ref({ file: '', playlist_id: null, city: 'global', screens: [], time_start: '', time_end: '' });
    const allScreensMap = ref({}); 
    const availableScreens = ref([]);
    
    // Оставляем часовые пояса для истории, но они больше не сбивают логику
    const cityTimezones = {
        global: { label: 'МСК', offset: 3 }, moscow: { label: 'МСК', offset: 3 }, spb: { label: 'МСК', offset: 3 }, novocheboksarsk: { label: 'МСК', offset: 3 },
        yartsevo: { label: 'МСК', offset: 3 }, azov: { label: 'МСК', offset: 3 }, orenburg: { label: 'МСК+2', offset: 5 }, chernyakhovsk: { label: 'МСК-1', offset: 2 }
    };

    const fetchScreens = async () => {
        try {
            const res = await fetch('/screens/', { headers: { 'Authorization': authHeader.value } });
            const data = await safeJson(res); 
            allScreensMap.value = data.screens || {};
        } catch (e) {}
    };

    const fetchSchedules = async () => {
        try {
            const res = await fetch('/schedules/', { headers: { 'Authorization': authHeader.value } });
            const data = await safeJson(res); 
            schedules.value = data.schedules || [];
        } catch (e) {}
    };

    const onCityChange = () => {
        availableScreens.value = newSchedule.value.city === 'global' ? [] : (allScreensMap.value[newSchedule.value.city] || []);
        newSchedule.value.screens = []; 
    };

    const selectAllScreens = () => { 
        newSchedule.value.screens = [...availableScreens.value]; 
    };

    const openScheduleModal = () => {
        showAddModal.value = true;
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
        
        // Текущее время на ПК администратора (Московское время)
        const now = new Date(); 

        // СТРОГОЕ ПРАВИЛО: нельзя ставить время меньше текущего по МСК
        if (st < now) return showToast('Ошибка: нельзя запланировать трансляцию в прошлом (относительно МСК)!', 'error');
        if (en <= st) return showToast('Ошибка: время окончания должно быть позже времени начала', 'error');

        requestConfirm(e, 'Запланировать эту трансляцию?', async () => {
            const res = await fetch('/schedules/', { 
                method: 'POST', 
                headers: { 'Authorization': authHeader.value, 'Content-Type': 'application/json' }, 
                body: JSON.stringify(newSchedule.value) 
            });
            if (!res.ok) {
                const resData = await safeJson(res); 
                showToast(resData.detail, 'error');
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