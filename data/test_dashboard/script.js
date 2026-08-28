// Dashboard Testdashboard
document.addEventListener('DOMContentLoaded', () => {
    new Chart(document.getElementById('lineChart'), {
        type: 'line',
        data: {
            labels: ['Ene','Feb','Mar','Abr','May','Jun','Jul'],
            datasets: [{
                label: 'Ventas 2026',
                data: [12,19,15,22,28,35,30],
                borderColor: '#a78bfa',
                backgroundColor: 'rgba(167,139,250,0.1)',
                tension: 0.4,
                fill: true,
            }]
        },
        options: {
            responsive: true,
            plugins: { legend: { labels: { color: '#e0e0e0' } } },
            scales: { x: { ticks: { color: '#888' } }, y: { ticks: { color: '#888' } } }
        }
    });
    new Chart(document.getElementById('doughnutChart'), {
        type: 'doughnut',
        data: {
            labels: ['Desktop', 'Mobile', 'Tablet'],
            datasets: [{
                data: [55, 35, 10],
                backgroundColor: ['#a78bfa', '#60a5fa', '#f472b6'],
            }]
        },
        options: { plugins: { legend: { labels: { color: '#e0e0e0' } } } }
    });
});
