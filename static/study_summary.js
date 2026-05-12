// Tab switching
function switchTab(name) {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
    document.querySelector(`[onclick="switchTab('${name}')"]`).classList.add('active');
    document.getElementById('tab-' + name).classList.add('active');
}

function generateColors(count) {
    const colors = [];
    for (let i = 0; i < count; i++) {
        const hue = (i * 137.5) % 360; // golden angle spread — keeps colors distinct
        colors.push(`hsl(${hue}, 65%, 60%)`);
    }
    return colors;
}

document.addEventListener("DOMContentLoaded", function () {
    Chart.defaults.font.family = 'Arial, sans-serif';
    Chart.defaults.color = '#4a5568';

    // Friends daily grouped bar chart (only if in a group)
    const friendsDailyEl = document.getElementById('friendsDailyChart');
    if (friendsDailyEl) {
        new Chart(friendsDailyEl, {
            type: 'bar',
            data: {
                labels: friendNames,
                datasets: [
                {
                    label: 'Study',
                    data: friendTodayStudy,
                    backgroundColor: '#667eea',
                    borderRadius: 6,
                    borderSkipped: false,
                },
                {
                    label: 'Break',
                    data: friendTodayBreak,
                    backgroundColor: '#f6ad55',
                    borderRadius: 6,
                    borderSkipped: false,
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                plugins: { legend: { position: 'bottom' } },
                scales: {
                    x: { beginAtZero: true, grid: { color: '#e2e8f0' }, ticks: { callback: v => v + 'h' } },
                    y: { grid: { display: false } }
                }
            }
        });
    }

    // Friends weekly grouped bar chart (only if in a group)
    const friendsWeeklyEl = document.getElementById('friendsWeeklyChart');
    if (friendsWeeklyEl) {
        new Chart(friendsWeeklyEl, {
            type: 'bar',
            data: {
                labels: friendNames,
                datasets: [
                {
                    label: 'Study',
                    data: friendStudy,
                    backgroundColor: '#667eea',
                    borderRadius: 6,
                    borderSkipped: false,
                },
                {
                    label: 'Break',
                    data: friendBreak,
                    backgroundColor: '#f6ad55',
                    borderRadius: 6,
                    borderSkipped: false,
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                plugins: { legend: { position: 'bottom' } },
                scales: {
                    x: { beginAtZero: true, grid: { color: '#e2e8f0' }, ticks: { callback: v => v + 'h' } },
                    y: { grid: { display: false } }
                }
            }
        });
    }

    // All-time course donut
    if (courseLabels.length > 0) {
        new Chart(document.getElementById('courseChart'), {
            type: 'doughnut',
            data: {
                labels: courseLabels,
                datasets: [{
                    data: courseHours,
                    backgroundColor: generateColors(courseLabels.length),
                    borderWidth: 2,
                    borderColor: '#fff',
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { position: 'bottom', labels: { padding: 15 } },
                    tooltip: { callbacks: { label: ctx => ` ${ctx.label}: ${ctx.raw}h` } }
                },
                cutout: '65%',
            }
        });

        // Today's course donut
        if (todayCourseLabels.length > 0) {
            new Chart(document.getElementById('todayCourseChart'), {
                type: 'doughnut',
                data: {
                    labels: todayCourseLabels,
                    datasets: [{
                        data: todayCourseHours,
                        backgroundColor: generateColors(todayCourseLabels.length),
                        borderWidth: 2,
                        borderColor: '#fff',
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: { position: 'bottom', labels: { padding: 15 } },
                        tooltip: { callbacks: { label: ctx => ` ${ctx.label}: ${ctx.raw}h` } }
                    },
                    cutout: '65%',
                }
            });
        } else {
            const canvas = document.getElementById('todayCourseChart');
            const ctx = canvas.getContext('2d');
            canvas.parentElement.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:100%;color:#a0aec0;font-size:15px;">No sessions logged today</div>';
        }

        // Today's bar chart
        new Chart(document.getElementById('todayBarChart'), {
            type: 'bar',
            data: {
                labels: ['Today'],
                datasets: [
                    {
                        label: 'Study',
                        data: [todayStudyHours],
                        backgroundColor: '#667eea',
                        borderRadius: 8,
                        borderSkipped: false,
                    },
                    {
                        label: 'Break',
                        data: [todayBreakHours],
                        backgroundColor: '#f6ad55',
                        borderRadius: 8,
                        borderSkipped: false,
                    }
                ]
            },
            options: {
                responsive: true,
                plugins: { legend: { position: 'bottom' } },
                scales: {
                    x: { grid: { display: false } },
                    y: { beginAtZero: true, grid: { color: '#e2e8f0' }, ticks: { callback: v => v + 'h' } }
                }
            }
        });

        // Trend line chart with pagination controls
        const trendCanvas = document.getElementById('trendChart');
        const trendPrevButton = document.getElementById('trendPrev');
        const trendNextButton = document.getElementById('trendNext');
        const trendStartText = document.getElementById('trendStart');
        const trendEndText = document.getElementById('trendEnd');
        const trendTotalText = document.getElementById('trendTotal');

        if (trendCanvas) {
            const trendWindowSize = 14;
            let trendStartIndex = Math.max(0, dailyLabels.length - trendWindowSize);
            const trendTotalDays = dailyLabels.length;
            const trendMaxStart = Math.max(0, trendTotalDays - trendWindowSize);

            function updateTrendControls(startIndex) {
                const endIndex = Math.min(startIndex + trendWindowSize, trendTotalDays);
                trendStartText.textContent = startIndex + 1;
                trendEndText.textContent = endIndex;
                trendTotalText.textContent = trendTotalDays;
                trendPrevButton.disabled = startIndex === 0;
                trendNextButton.disabled = startIndex >= trendMaxStart;
            }

            function getTrendSlice(startIndex) {
                const endIndex = Math.min(startIndex + trendWindowSize, trendTotalDays);
                return {
                    labels: dailyLabels.slice(startIndex, endIndex),
                    study: dailyStudy.slice(startIndex, endIndex),
                    break: dailyBreak.slice(startIndex, endIndex)
                };
            }

            const initialSlice = getTrendSlice(trendStartIndex);
            const trendChart = new Chart(trendCanvas, {
                type: 'line',
                data: {
                    labels: initialSlice.labels,
                    datasets: [
                        {
                            label: 'Study',
                            data: initialSlice.study,
                            borderColor: '#667eea',
                            backgroundColor: 'rgba(102, 126, 234, 0.1)',
                            borderWidth: 2,
                            pointBackgroundColor: '#667eea',
                            pointRadius: 4,
                            tension: 0.3,
                            fill: true,
                        },
                        {
                            label: 'Break',
                            data: initialSlice.break,
                            borderColor: '#f6ad55',
                            backgroundColor: 'rgba(246, 173, 85, 0.1)',
                            borderWidth: 2,
                            pointBackgroundColor: '#f6ad55',
                            pointRadius: 4,
                            tension: 0.3,
                            fill: true,
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { position: 'bottom' } },
                    scales: {
                        x: { grid: { display: false } },
                        y: { beginAtZero: true, grid: { color: '#e2e8f0' }, ticks: { callback: v => v + 'h' } }
                    }
                }
            });

            if (trendTotalDays > 0) {
                updateTrendControls(trendStartIndex);
            }

            if (trendPrevButton && trendNextButton) {
                trendPrevButton.addEventListener('click', function () {
                    trendStartIndex = Math.max(0, trendStartIndex - trendWindowSize);
                    const slice = getTrendSlice(trendStartIndex);
                    trendChart.data.labels = slice.labels;
                    trendChart.data.datasets[0].data = slice.study;
                    trendChart.data.datasets[1].data = slice.break;
                    trendChart.update();
                    updateTrendControls(trendStartIndex);
                });

                trendNextButton.addEventListener('click', function () {
                    trendStartIndex = Math.min(trendMaxStart, trendStartIndex + trendWindowSize);
                    const slice = getTrendSlice(trendStartIndex);
                    trendChart.data.labels = slice.labels;
                    trendChart.data.datasets[0].data = slice.study;
                    trendChart.data.datasets[1].data = slice.break;
                    trendChart.update();
                    updateTrendControls(trendStartIndex);
                });
            }
        }
    }
});