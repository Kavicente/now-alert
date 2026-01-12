// Shared JavaScript functions for analytics pages
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const mainContent = document.getElementById('mainContent');
    sidebar.classList.toggle('active');
    mainContent.classList.toggle('shifted');
}

function showSection(type) {
    const roadHeader = document.getElementById('letterR');
    const roadSection = document.getElementById('roadSection');
    const fireHeader = document.getElementById('letterF');
    const fireSection = document.getElementById('fireSection');

    if (type === 'road') {
        roadHeader.classList.remove('hidden');
        roadSection.classList.remove('hidden');
        fireHeader.classList.add('hidden');
        fireSection.classList.add('hidden');
    } else if (type === 'fire') {
        roadHeader.classList.add('hidden');
        roadSection.classList.add('hidden');
        fireHeader.classList.remove('hidden');
        fireSection.classList.remove('hidden');
    }

    // Trigger data refresh for the active time period
    const activeTab = document.querySelector('.tab.active');
    if (activeTab) {
        filterData(activeTab.textContent.toLowerCase());
    }
}

function setActiveTab(tabElement) {
    document.querySelectorAll('.tab').forEach(tab => tab.classList.remove('active'));
    tabElement.classList.add('active');
}

function updateCharts(data) {
    const role = window.location.pathname.includes('bfp') ? 'bfp' :
                 window.location.pathname.includes('cdrrmo') ? 'cdrrmo' :
                 window.location.pathname.includes('pnp') ? 'pnp' : 'barangay';
    if (window.charts) {
        Object.values(window.charts).forEach(chart => chart.destroy());
    }
    window.charts = {};

    // Ensure data fields exist, provide defaults if missing
    const defaultData = {
        trends: { labels: [], total: [], responded: [] },
        distribution: {},
        causes: { road: {}, fire: {} },
        types: {},
        road_conditions: {},
        weather: {},
        vehicle_types: {},
        driver_age: {},
        driver_gender: {},
        property_types: {}
    };
    data = { ...defaultData, ...data };

    if (role === 'barangay' || role === 'cdrrmo' || role === 'pnp') {
        renderLine('roadIncidentTrendsChart', data.trends.labels, [
            { label: 'Total Incidents', data: data.trends.total, borderColor: '#36A2EB', backgroundColor: 'rgba(54, 162, 235, 0.2)' },
            { label: 'Responded Incidents', data: data.trends.responded, borderColor: '#FF6384', backgroundColor: 'rgba(255, 99, 132, 0.2)' }
        ], 'Incident Trends');
        renderPie('roadAccidentDistributionChart', Object.keys(data.distribution).reduce((acc, k) => ({ ...acc, [k]: data.distribution[k].total }), {}), 'Accident Distribution');
        renderBar('roadRespondedAlertsChart', Object.keys(data.distribution), Object.values(data.distribution).map(d => d.responded || 0), 'Responded Alerts');
        renderBar('roadCauseAnalysisChart', data.causes.road, 'Accident Cause');
        renderBar('roadAccidentTypeChart', data.types, 'Accident Type');
        renderPie('roadConditionChart', data.road_conditions, 'Road Condition');
        renderPie('roadWeatherChart', data.weather, 'Weather Condition');
        renderPie('roadVehicleTypesChart', data.vehicle_types, 'Vehicle Types');
        renderBar('roadDriverAgeChart', data.driver_age, 'Driver\'s Age');
        renderPie('roadDriverGenderChart', data.driver_gender, 'Driver\'s Gender');
    }

    if (role === 'barangay' || role === 'bfp') {
        renderLine('fireIncidentTrendsChart', data.trends.labels, [
            { label: 'Total Incidents', data: data.trends.total, borderColor: '#36A2EB', backgroundColor: 'rgba(54, 162, 235, 0.2)' },
            { label: 'Responded Incidents', data: data.trends.responded, borderColor: '#FF6384', backgroundColor: 'rgba(255, 99, 132, 0.2)' }
        ], 'Incident Trends');
        renderPie('fireIncidentDistributionChart', Object.keys(data.distribution).reduce((acc, k) => ({ ...acc, [k]: data.distribution[k].total }), {}), 'Incident Distribution');
        renderBar('fireRespondedAlertsChart', Object.keys(data.distribution), Object.values(data.distribution).map(d => d.responded || 0), 'Responded Alerts');
        renderBar('fireCauseAnalysisChart', data.causes.fire, 'Fire Cause Analysis');
        renderPie('fireWeatherChart', data.weather, 'Weather Impact');
        renderPie('firePropertyTypeChart', data.property_types, 'Property Type');
        renderBar('fireCauseChart', data.causes.fire, 'Fire Cause');
    }

    if (role === 'pnp') {
        renderLine('crimeIncidentTrendsChart', data.trends.labels, [
            { label: 'Total Incidents', data: data.trends.total, borderColor: '#36A2EB', backgroundColor: 'rgba(54, 162, 235, 0.2)' },
            { label: 'Responded Incidents', data: data.trends.responded, borderColor: '#FF6384', backgroundColor: 'rgba(255, 99, 132, 0.2)' }
        ], 'Incident Trends');
        renderPie('crimeIncidentDistributionChart', Object.keys(data.distribution).reduce((acc, k) => ({ ...acc, [k]: data.distribution[k].total }), {}), 'Incident Distribution');
        renderBar('crimeRespondedAlertsChart', Object.keys(data.distribution), Object.values(data.distribution).map(d => d.responded || 0), 'Responded Alerts');
        renderBar('crimeTypeAnalysisChart', data.causes.road, 'Crime Type Analysis');
    }
}

function renderPie(canvasId, objData, title) {
    const ctx = document.getElementById(canvasId)?.getContext('2d');
    if (!ctx) return;
    if (window[canvasId]) window[canvasId].destroy();
    window[canvasId] = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: Object.keys(objData),
            datasets: [{ data: Object.values(objData), backgroundColor: generateColors(objData) }]
        },
        options: { 
            responsive: true, 
            plugins: { 
                title: { display: true, text: title },
                legend: { position: 'top' }
            }
        }
    });
}

function renderLine(canvasId, labels, datasets, title) {
    const ctx = document.getElementById(canvasId)?.getContext('2d');
    if (!ctx) return;
    if (window[canvasId]) window[canvasId].destroy();
    window[canvasId] = new Chart(ctx, {
        type: 'line',
        data: { 
            labels, 
            datasets: datasets.map(ds => ({
                label: ds.label,
                data: ds.data,
                borderColor: ds.borderColor,
                backgroundColor: ds.backgroundColor,
                fill: true
            }))
        },
        options: { 
            responsive: true,
            plugins: { 
                title: { display: true, text: title }
            },
            scales: {
                y: { beginAtZero: true }
            }
        }
    });
}

function renderBar(canvasId, objDataOrLabels, data, title) {
    const ctx = document.getElementById(canvasId)?.getContext('2d');
    if (!ctx) return;
    let labels = Array.isArray(objDataOrLabels) ? objDataOrLabels : Object.keys(objDataOrLabels);
    let dataset = Array.isArray(data) ? data : Object.values(objDataOrLabels);
    if (window[canvasId]) window[canvasId].destroy();
    window[canvasId] = new Chart(ctx, {
        type: 'bar',
        data: { 
            labels, 
            datasets: [{ 
                label: title, 
                data: dataset, 
                backgroundColor: '#36A2EB',
                borderColor: '#36A2EB',
                borderWidth: 1
            }] 
        },
        options: { 
            responsive: true,
            plugins: { 
                title: { display: true, text: title }
            },
            scales: {
                y: { beginAtZero: true }
            }
        }
    });
}

function generateColors(obj) {
    const palette = ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40', '#8A2BE2', '#00CED1', '#FF4500', '#2E8B57'];
    return Object.keys(obj).map((_, i) => palette[i % palette.length]);
}

// Initialize page
document.addEventListener('DOMContentLoaded', () => {
    const defaultTab = document.querySelector('.tab');
    if (defaultTab) {
        defaultTab.classList.add('active');
        filterData('today');
    }
});