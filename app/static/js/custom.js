// Custom JavaScript for API integration and dynamic features

document.addEventListener('DOMContentLoaded', function() {
    // Add fade-in animation to cards
    const cards = document.querySelectorAll('.card');
    cards.forEach(card => {
        card.classList.add('fade-in');
    });

    // Initialize tooltips if Bootstrap tooltips are used
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    const tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Function to fetch data from API
    function fetchFromAPI(endpoint, callback) {
        fetch(endpoint, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => callback(data))
        .catch(error => console.error('Error fetching data:', error));
    }

    // Load dashboard stats dynamically
    if (document.querySelector('#total-employees')) {
        fetchFromAPI('/api/dashboard/stats', function(data) {
            if (data.error) {
                console.error('Unauthorized');
                return;
            }
            document.querySelector('#total-employees').textContent = data.total_employees;
            document.querySelector('#total-revenue').textContent = '$' + data.total_revenue.toFixed(2);
            
            // Update sales chart
            if (document.getElementById('sales-chart')) {
                const ctx = document.getElementById('sales-chart').getContext('2d');
                new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: data.sales_labels,
                        datasets: [{
                            label: 'Sales ($)',
                            data: data.sales_values,
                            borderColor: '#007bff',
                            backgroundColor: 'rgba(0, 123, 255, 0.1)',
                            tension: 0.1,
                            fill: true
                        }]
                    },
                    options: {
                        responsive: true,
                        plugins: {
                            legend: {
                                position: 'top',
                            },
                            title: {
                                display: true,
                                text: 'Sales Over Last 30 Days'
                            }
                        }
                    }
                });
            }
        });
    }

    // Load businesses dynamically on dashboard
    if (document.querySelector('.business-grid')) {
        // Businesses are already rendered server-side, but we can add dynamic updates if needed
        // For now, they are static
    }

    // Add loading states
    function showLoading(element) {
        element.innerHTML = '<div class="text-center"><div class="spinner-border text-primary" role="status"><span class="visually-hidden">Loading...</span></div></div>';
    }

    function hideLoading(element, content) {
        element.innerHTML = content;
    }

    // Handle form submissions with AJAX if needed
    const forms = document.querySelectorAll('form[data-ajax="true"]');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            const formData = new FormData(form);
            fetch(form.action, {
                method: form.method,
                body: formData,
                headers: {
                    'Content-Type': 'application/json'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Handle success
                    location.reload();
                } else {
                    // Handle error
                    alert(data.message);
                }
            });
        });
    });

    // Auto-refresh notifications (placeholder)
    function refreshNotifications() {
        // Fetch notifications if endpoint exists
        // fetchFromAPI('/api/notifications', function(data) {
        //     const notificationBadge = document.querySelector('.notification-badge');
        //     if (notificationBadge) {
        //         notificationBadge.textContent = data.unread_count;
        //     }
        // });
    }

    // Refresh stats every 5 minutes
    if (document.querySelector('#total-employees')) {
        setInterval(() => {
            fetchFromAPI('/api/dashboard/stats', function(data) {
                if (!data.error) {
                    document.querySelector('#total-employees').textContent = data.total_employees;
                    document.querySelector('#total-revenue').textContent = '$' + data.total_revenue.toFixed(2);
                }
            });
        }, 300000); // 5 minutes
    }
});
