document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', (e) => {
        e.preventDefault();
        
        if (item.classList.contains('collapsible')) {
            const section = item.getAttribute('data-section');
            const subsection = document.getElementById(section + '-section');
            item.classList.toggle('expanded');
            subsection.classList.toggle('hidden');
            subsection.classList.toggle('expanded');
        } else {
            const page = item.getAttribute('data-page');
            switchPage(page);
            
            document.querySelectorAll('.nav-item').forEach(nav => nav.classList.remove('active'));
            item.classList.add('active');
        }
    });
});

document.querySelectorAll('.nav-subitem').forEach(item => {
    item.addEventListener('click', (e) => {
        e.preventDefault();
        const page = item.getAttribute('data-page');
        switchPage(page);
        
        document.querySelectorAll('.nav-item, .nav-subitem').forEach(nav => nav.classList.remove('active'));
        item.classList.add('active');
    });
});

function switchPage(page) {
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.getElementById('page-' + page).classList.add('active');
}

document.getElementById('uploadForm').addEventListener('submit', async (e) => {
    e.preventDefault();

    const formData = new FormData();
    const customerFile = document.getElementById('customerFile').files[0];
    const templateFile = document.getElementById('templateFile').files[0];

    if (!customerFile) {
        alert('Please select a customer file');
        return;
    }

    formData.append('customer_file', customerFile);
    if (templateFile) {
        formData.append('template_file', templateFile);
    }

    document.getElementById('progressSection').style.display = 'block';
    document.getElementById('resultsSection').style.display = 'none';

    try {
        const response = await fetch('/api/process', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (response.ok) {
            document.getElementById('progressSection').style.display = 'none';
            document.getElementById('resultsSection').style.display = 'block';

            document.getElementById('downloadBtn').onclick = () => {
                window.location.href = `/api/download/${data.output_file}`;
            };
        } else {
            alert(`Error: ${data.error}`);
            document.getElementById('progressSection').style.display = 'none';
        }

        displayLogs(data.logs);

    } catch (error) {
        alert(`Upload failed: ${error.message}`);
        document.getElementById('progressSection').style.display = 'none';
    }
});

function displayLogs(logs) {
    const logsContainer = document.getElementById('logsContainer');
    logsContainer.innerHTML = '';

    logs.forEach(log => {
        const logEntry = document.createElement('div');
        logEntry.className = `log-entry log-${log.level.toLowerCase()}`;
        logEntry.innerHTML = `<strong>[${log.time}]</strong> ${log.level}: ${log.message}`;
        logsContainer.appendChild(logEntry);
    });

    logsContainer.scrollTop = logsContainer.scrollHeight;
}

// Design Input Review Form Handler
document.getElementById('designFile').addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    // Check which columns are available in the Excel file
    const formData = new FormData();
    formData.append('input_file', file);

    try {
        const response = await fetch('/api/check-columns', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();
        
        // Update indicators based on available columns
        updateColumnIndicator('signalOriginIndicator', data.has_signal_origin, 'signal_origin');
        updateColumnIndicator('ioRedundancyIndicator', data.has_io_redundancy, 'IO_REDUNDANCY');
        updateColumnIndicator('isNonIsIndicator', data.has_is_non_is, 'IS_Non_IS');
        updateColumnIndicator('controllerModelIndicator', data.has_controller_model, 'Controller_Model');

    } catch (error) {
        console.error('Error checking columns:', error);
    }
});

function updateColumnIndicator(elementId, hasColumn, columnName) {
    const indicator = document.getElementById(elementId);
    if (hasColumn) {
        indicator.textContent = '✓ Column Available';
        indicator.className = 'column-indicator available';
    } else {
        indicator.textContent = '✗ Column Missing - Input Required';
        indicator.className = 'column-indicator missing';
    }
}

document.getElementById('designForm').addEventListener('submit', async (e) => {
    e.preventDefault();

    const formData = new FormData();
    const inputFile = document.getElementById('designFile').files[0];

    if (!inputFile) {
        alert('Please select an input file');
        return;
    }

    formData.append('input_file', inputFile);
    formData.append('system_type', document.getElementById('systemType').value);
    formData.append('controller_model', document.getElementById('controllerModel').value);
    formData.append('explosion_protection', document.getElementById('explosionProtection').value);
    formData.append('temperature_rating', document.getElementById('temperatureRating').value);
    
    // Get selected IO types
    const ioTypes = Array.from(document.querySelectorAll('input[name="io_types"]:checked'))
        .map(cb => cb.value);
    formData.append('io_types', JSON.stringify(ioTypes));
    
    // Get selected redundancy types
    const redundancyTypes = Array.from(document.querySelectorAll('input[name="redundancy_types"]:checked'))
        .map(cb => cb.value);
    formData.append('redundancy_types', JSON.stringify(redundancyTypes));
    
    // Get selected IS types
    const isTypes = Array.from(document.querySelectorAll('input[name="is_types"]:checked'))
        .map(cb => cb.value);
    formData.append('is_types', JSON.stringify(isTypes));
    
    // Get wired spares percentage
    const wiredSpares = document.getElementById('wiredSpares').value;
    if (wiredSpares) {
        formData.append('wired_spares', wiredSpares);
    }

    document.getElementById('designProgressSection').style.display = 'block';
    document.getElementById('designResultsSection').style.display = 'none';

    try {
        const response = await fetch('/api/design-input-review', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (response.ok) {
            document.getElementById('designProgressSection').style.display = 'none';
            document.getElementById('designResultsSection').style.display = 'block';

            document.getElementById('designDownloadBtn').onclick = () => {
                window.location.href = `/api/download/${data.output_file}`;
            };
        } else {
            alert(`Error: ${data.error}`);
            document.getElementById('designProgressSection').style.display = 'none';
        }

        displayDesignLogs(data.logs);

    } catch (error) {
        alert(`Upload failed: ${error.message}`);
        document.getElementById('designProgressSection').style.display = 'none';
    }
});

function displayDesignLogs(logs) {
    const logsContainer = document.getElementById('designLogsContainer');
    logsContainer.innerHTML = '';

    logs.forEach(log => {
        const logEntry = document.createElement('div');
        logEntry.className = `log-entry log-${log.level.toLowerCase()}`;
        logEntry.innerHTML = `<strong>[${log.time}]</strong> ${log.level}: ${log.message}`;
        logsContainer.appendChild(logEntry);
    });

    logsContainer.scrollTop = logsContainer.scrollHeight;
}

