import { ref, computed } from 'vue';

export function useMedia(authHeader, login, showToast, safeJson) {
    const files = ref([]); 
    const trashFiles = ref([]);
    const searchQuery = ref(''); 
    const filterCity = ref('all'); 
    const sortBy = ref('date_desc');
    const selectedFile = ref(null); 
    const selectedCity = ref('global');
    const uploading = ref(false); 
    const uploadError = ref(''); 
    const uploadProgress = ref(0);
    const importLogs = ref([]); 
    const storageStats = ref({ used: 0, max: 0, percent: 0 });

    const fetchFiles = async () => {
        try {
            const res = await fetch('/files/', { headers: { 'Authorization': authHeader.value } });
            const data = await safeJson(res); 
            files.value = data.files || [];
        } catch (e) {}
    };

    const fetchTrash = async () => {
        try {
            const res = await fetch('/trash/', { headers: { 'Authorization': authHeader.value } });
            const data = await safeJson(res); 
            trashFiles.value = data.trash || [];
        } catch (e) {}
    };

    const fetchStats = async () => {
        try {
            const res = await fetch('/storage-stats/', { headers: { 'Authorization': authHeader.value } });
            storageStats.value = await safeJson(res);
        } catch (e) {}
    };

    const handleFileSelect = (e) => {
        selectedFile.value = e.target.files[0];
    };

    const uploadFile = () => {
        if (!selectedFile.value) return showToast('Файл не выбран', 'warning');
        uploading.value = true; 
        uploadError.value = ''; 
        uploadProgress.value = 0;

        const formData = new FormData(); 
        formData.append('file', selectedFile.value); 
        formData.append('target_city', selectedCity.value);

        const xhr = new XMLHttpRequest(); 
        xhr.open('POST', '/upload/', true); 
        xhr.setRequestHeader('Authorization', authHeader.value);

        xhr.upload.onprogress = (event) => { 
            if (event.lengthComputable) {
                uploadProgress.value = Math.round((event.loaded / event.total) * 100); 
            }
        };

        xhr.onload = () => {
            uploading.value = false;
            try {
                const data = JSON.parse(xhr.responseText);
                if (xhr.status === 200) {
                    importLogs.value.unshift({ filename: selectedFile.value.name, success: true, text: data.message });
                    selectedFile.value = null; 
                    fetchFiles(); 
                    fetchStats(); 
                    showToast('Файл успешно загружен', 'success');
                } else {
                    uploadError.value = data.detail || 'Ошибка импорта';
                    importLogs.value.unshift({ filename: selectedFile.value.name, success: false, text: data.detail });
                    showToast(data.detail, 'error');
                }
            } catch (e) { 
                uploadError.value = 'Ошибка сервера'; 
                showToast('Ошибка сервера', 'error'); 
            }
        };

        xhr.onerror = () => { 
            uploading.value = false; 
            uploadError.value = 'Сервер недоступен'; 
            showToast('Сервер недоступен', 'error'); 
        };

        xhr.send(formData);
    };

    const deleteFile = async (fileName) => {
        await fetch(`/files/${encodeURIComponent(fileName)}`, { method: 'DELETE', headers: { 'Authorization': authHeader.value } });
        fetchFiles(); 
        fetchTrash(); 
        fetchStats(); 
        showToast('Перемещено в корзину', 'success');
    };

    const restoreFile = async (fileName) => {
        await fetch(`/trash/restore/${encodeURIComponent(fileName)}`, { method: 'POST', headers: { 'Authorization': authHeader.value } });
        fetchFiles(); 
        fetchTrash(); 
        fetchStats(); 
        showToast('Файл восстановлен', 'success');
    };

    const emptyTrash = async () => {
        await fetch('/trash/empty/', { method: 'DELETE', headers: { 'Authorization': authHeader.value } });
        fetchTrash(); 
        fetchStats(); 
        showToast('Корзина полностью очищена', 'success');
    };

    const filteredAndSortedFiles = computed(() => {
        let result = files.value;
        if (searchQuery.value) {
            result = result.filter(f => f.name.toLowerCase().includes(searchQuery.value.toLowerCase()));
        }
        if (login.value === 'admin_main' && filterCity.value !== 'all') { 
            result = result.filter(f => f.name.startsWith(filterCity.value + '/')); 
        }
        return result.slice().sort((a, b) => {
            if (sortBy.value === 'name_asc') return a.name.localeCompare(b.name);
            if (sortBy.value === 'name_desc') return b.name.localeCompare(a.name);
            if (sortBy.value === 'size_desc') return b.size - a.size;
            if (sortBy.value === 'size_asc') return a.size - b.size;
            const dateA = new Date(a.last_modified).getTime() || 0; 
            const dateB = new Date(b.last_modified).getTime() || 0;
            if (sortBy.value === 'date_desc') return dateB - dateA;
            if (sortBy.value === 'date_asc') return dateA - dateB;
            return 0;
        });
    });

    return { 
        files, trashFiles, searchQuery, filterCity, sortBy, selectedFile, selectedCity, 
        uploading, uploadError, uploadProgress, importLogs, storageStats, filteredAndSortedFiles, 
        handleFileSelect, fetchFiles, fetchTrash, fetchStats, uploadFile, deleteFile, restoreFile, emptyTrash 
    };
}