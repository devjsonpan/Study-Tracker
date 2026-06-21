// Study summary page: renders all Chart.js charts and the GitHub-style activity heatmap.
// All data arrays (dailyLabels, courseLabels, friendNames, heatmapAllData, etc.) are
// injected as inline JSON by the Flask /summary route — no additional API calls needed.

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
    const isDark = document.documentElement.classList.contains('dark-theme');
    const gridColor = isDark ? '#475569' : '#e2e8f0';
    const textColor = isDark ? '#f8fafc' : '#4a5568';
    
    Chart.defaults.font.family = 'Arial, sans-serif';
    Chart.defaults.color = textColor;

    // Friends daily grouped bar chart (only if in a group)
    const friendsDailyEl = document.getElementById('friendsDailyChart');
    if (friendsDailyEl) {
        const friendChartHeight = Math.max(220, friendNames.length * 38 + 60);
        document.getElementById('friendsDailyInner').style.height = friendChartHeight + 'px';
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
                maintainAspectRatio: false,
                plugins: { legend: { position: 'bottom' } },
                scales: {
                    x: { beginAtZero: true, grid: { color: gridColor }, border: { color: gridColor }, ticks: { callback: v => v + 'h' } },
                    y: { grid: { display: false }, border: { color: gridColor } }
                }
            }
        });
    }

    // Friends weekly grouped bar chart (only if in a group)
    const friendsWeeklyEl = document.getElementById('friendsWeeklyChart');
    if (friendsWeeklyEl) {
        const friendChartHeight = Math.max(220, friendNames.length * 38 + 60);
        document.getElementById('friendsWeeklyInner').style.height = friendChartHeight + 'px';
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
                maintainAspectRatio: false,
                plugins: { legend: { position: 'bottom' } },
                scales: {
                    x: { beginAtZero: true, grid: { color: gridColor }, border: { color: gridColor }, ticks: { callback: v => v + 'h' } },
                    y: { grid: { display: false }, border: { color: gridColor } }
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
                    borderWidth: 0,
                    borderColor: 'transparent',
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
                        borderWidth: 0,
                        borderColor: 'transparent',
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
                    x: { grid: { display: false }, border: { color: gridColor } },
                    y: { beginAtZero: true, grid: { color: gridColor }, border: { color: gridColor }, ticks: { callback: v => v + 'h' } }
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
                        x: { grid: { display: false }, border: { color: gridColor } },
                        y: { beginAtZero: true, grid: { color: gridColor }, border: { color: gridColor }, ticks: { callback: v => v + 'h' } }
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

    // Render Heatmap
    if (typeof heatmapAllData !== 'undefined' && heatmapAllData.length > 0) {
        const heatmapContainer = document.getElementById('heatmap-container');
        const yearSelect = document.getElementById('heatmap-year-select');
        
        if (heatmapContainer) {
            let tooltip = document.getElementById('heatmap-tooltip');
            if (!tooltip) {
                tooltip = document.createElement('div');
                tooltip.id = 'heatmap-tooltip';
                tooltip.className = 'heatmap-tooltip';
                document.body.appendChild(tooltip);
            }

            // Extract available years from data
            const years = new Set();
            heatmapAllData.forEach(day => {
                years.add(day.date.substring(0, 4));
            });
            const sortedYears = Array.from(years).sort((a, b) => b - a);
            
            if (yearSelect) {
                sortedYears.forEach(year => {
                    const opt = document.createElement('option');
                    opt.value = year;
                    opt.textContent = year;
                    yearSelect.appendChild(opt);
                });
            }

            // Calculate Streaks
            let currentStreak = 0;
            let longestStreak = 0;
            let tempStreak = 0;
            
            heatmapAllData.forEach(day => {
                if (day.hours > 0) {
                    tempStreak++;
                    if (tempStreak > longestStreak) {
                        longestStreak = tempStreak;
                    }
                } else {
                    tempStreak = 0;
                }
            });
            
            if (heatmapAllData.length > 0) {
                const todayData = heatmapAllData[heatmapAllData.length - 1];
                const yesterdayData = heatmapAllData.length > 1 ? heatmapAllData[heatmapAllData.length - 2] : null;
                
                if (todayData.hours > 0) {
                    currentStreak = tempStreak;
                } else if (yesterdayData && yesterdayData.hours > 0) {
                    let backTrackStreak = 0;
                    for (let i = heatmapAllData.length - 2; i >= 0; i--) {
                        if (heatmapAllData[i].hours > 0) {
                            backTrackStreak++;
                        } else {
                            break;
                        }
                    }
                    currentStreak = backTrackStreak;
                }
            }
            
            const currentStreakEl = document.getElementById('current-streak');
            const longestStreakEl = document.getElementById('longest-streak');
            if (currentStreakEl) currentStreakEl.textContent = currentStreak + (currentStreak === 1 ? ' day' : ' days');
            if (longestStreakEl) longestStreakEl.textContent = longestStreak + (longestStreak === 1 ? ' day' : ' days');

            function renderHeatmapView(viewType) {
                heatmapContainer.innerHTML = '';
                
                let viewData = [];
                if (viewType === 'last365') {
                    viewData = heatmapAllData.slice(-365);
                } else {
                    const dataMap = new Map();
                    heatmapAllData.forEach(d => dataMap.set(d.date, d));
                    
                    const yearStart = new Date(viewType, 0, 1);
                    const isLeap = new Date(viewType, 1, 29).getMonth() === 1;
                    const daysInYear = isLeap ? 366 : 365;
                    
                    for(let i=0; i<daysInYear; i++) {
                        const d = new Date(yearStart.getTime() + i*24*60*60*1000);
                        const y = d.getFullYear();
                        const m = String(d.getMonth()+1).padStart(2, '0');
                        const day = String(d.getDate()).padStart(2, '0');
                        const dateStr = `${y}-${m}-${day}`;
                        
                        viewData.push(dataMap.has(dateStr) ? dataMap.get(dateStr) : { date: dateStr, hours: 0 });
                    }
                }
                
                const weeks = [];
                let currentWeek = [];
                
                const firstDateStr = viewData[0].date;
                const parts = firstDateStr.split('-');
                const firstDateObj = new Date(parts[0], parts[1] - 1, parts[2]);
                const firstDayOfWeek = firstDateObj.getDay(); 
                
                for (let i = 0; i < firstDayOfWeek; i++) {
                    currentWeek.push(null);
                }
                
                viewData.forEach(day => {
                    currentWeek.push(day);
                    if (currentWeek.length === 7) {
                        weeks.push(currentWeek);
                        currentWeek = [];
                    }
                });
                if (currentWeek.length > 0) {
                    while(currentWeek.length < 7) currentWeek.push(null);
                    weeks.push(currentWeek);
                }
                
                weeks.forEach(week => {
                    const col = document.createElement('div');
                    col.className = 'heatmap-column';
                    week.forEach(day => {
                        const cell = document.createElement('div');
                        cell.className = 'heatmap-cell';
                        if (day) {
                            let level = 0;
                            if (day.hours > 0 && day.hours <= 1) level = 1;
                            else if (day.hours > 1 && day.hours <= 3) level = 2;
                            else if (day.hours > 3 && day.hours <= 5) level = 3;
                            else if (day.hours > 5) level = 4;
                            
                            cell.setAttribute('data-level', level);
                            
                            const dParts = day.date.split('-');
                            const dateObj = new Date(dParts[0], dParts[1]-1, dParts[2]);
                            const dateString = dateObj.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
                            const tooltipText = `${day.hours}h on ${dateString}`;
                            
                            cell.addEventListener('mouseenter', () => {
                                tooltip.innerHTML = tooltipText;
                                tooltip.style.opacity = '1';
                            });
                            
                            cell.addEventListener('mousemove', (e) => {
                                tooltip.style.left = e.pageX + 'px';
                                tooltip.style.top = e.pageY + 'px';
                            });
                            
                            cell.addEventListener('mouseleave', () => {
                                tooltip.style.opacity = '0';
                            });
                        } else {
                            cell.style.visibility = 'hidden';
                        }
                        col.appendChild(cell);
                    });
                    heatmapContainer.appendChild(col);
                });
                
                setTimeout(() => {
                    heatmapContainer.scrollLeft = heatmapContainer.scrollWidth;
                }, 50);
            }
            
            renderHeatmapView('last365');
            
            if (yearSelect) {
                yearSelect.addEventListener('change', (e) => {
                    renderHeatmapView(e.target.value);
                });
            }
        }
    }
});