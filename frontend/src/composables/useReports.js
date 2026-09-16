import { ref, nextTick } from 'vue';

export function useReports(authHeader, showToast, safeJson) {
    const monitoringData = ref([]); 
    const analyticsData = ref({ total_shows: 0, total_hours: 0, status_counts: {}, city_counts: {} });
    const activityHistory = ref([]); 
    const storageHistory = ref([]); 
    
    const chartStatusRef = ref(null);
    const chartCityRef = ref(null);
    let chartStatusInstance = null; 
    let chartCityInstance = null;

    const fetchMonitoring = async () => {
        try {
            const res = await fetch('/monitoring/', { headers: { 'Authorization': authHeader.value } });
            if (res.ok) { 
                const data = await safeJson(res); 
                monitoringData.value = data.monitoring || []; 
            }
        } catch (e) {}
    };

    const fetchHistory = async () => {
        try {
            const res = await fetch('/history/', { headers: { 'Authorization': authHeader.value } });
            if (res.ok) { 
                const data = await safeJson(res); 
                activityHistory.value = data.history || []; 
            }
        } catch (e) { 
            showToast('Не удалось загрузить системный журнал', 'error'); 
        }
    };

    const fetchStorageHistory = async () => {
        try {
            const res = await fetch('/storage-history/', { headers: { 'Authorization': authHeader.value } });
            if (res.ok) { 
                const data = await safeJson(res); 
                storageHistory.value = data.storage_history || []; 
            }
        } catch (e) { 
            showToast('Не удалось загрузить историю хранилища', 'error'); 
        }
    };

    const fetchAnalytics = async () => {
        try {
            const res = await fetch('/analytics/', { headers: { 'Authorization': authHeader.value } });
            if (res.ok) { 
                analyticsData.value = await safeJson(res); 
            }
            
            nextTick(() => {
                if (chartStatusInstance) chartStatusInstance.destroy();
                if (chartCityInstance) chartCityInstance.destroy();
                
                if (chartStatusRef.value && window.Chart) {
                    chartStatusInstance = new window.Chart(chartStatusRef.value, { 
                        type: 'doughnut', 
                        data: { 
                            labels: Object.keys(analyticsData.value.status_counts), 
                            datasets: [{ data: Object.values(analyticsData.value.status_counts), backgroundColor: ['#fbbf24', '#34d399', '#cbd5e1'] }] 
                        }, 
                        options: { responsive: true, maintainAspectRatio: false } 
                    });
                }
                if (chartCityRef.value && window.Chart) {
                    chartCityInstance = new window.Chart(chartCityRef.value, { 
                        type: 'bar', 
                        data: { 
                            labels: Object.keys(analyticsData.value.city_counts), 
                            datasets: [{ label: 'Трансляции', data: Object.values(analyticsData.value.city_counts), backgroundColor: '#059669' }] 
                        }, 
                        options: { responsive: true, maintainAspectRatio: false, scales: { y: { beginAtZero: true } } } 
                    });
                }
            });
        } catch (e) {}
    };

    return { 
        monitoringData, analyticsData, activityHistory, storageHistory, 
        chartStatusRef, chartCityRef, fetchMonitoring, fetchHistory, fetchStorageHistory, fetchAnalytics 
    };
}