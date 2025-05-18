document.addEventListener('DOMContentLoaded', function() {
    // File browser functionality
    const fileBrowser = document.getElementById('file-browser');
    if (fileBrowser) {
        // Handle file/directory clicks
        fileBrowser.addEventListener('click', function(e) {
            const target = e.target.closest('.file-item');
            if (!target) return;
            
            if (target.dataset.type === 'dir') {
                // Navigate to directory
                const path = target.dataset.path;
                const domainId = document.getElementById('current-domain-id').value;
                window.location.href = `/files/browse/${domainId}?path=${encodeURIComponent(path)}`;
            } else if (target.dataset.type === 'file') {
                // View file
                const path = target.dataset.path;
                const domainId = document.getElementById('current-domain-id').value;
                window.location.href = `/files/view/${domainId}?path=${encodeURIComponent(path)}`;
            }
        });
    }
    
    // File editor functionality
    const fileEditor = document.getElementById('file-editor');
    if (fileEditor) {
        // Set up CodeMirror editor if available
        if (typeof CodeMirror !== 'undefined') {
            const textarea = document.getElementById('file-content');
            if (textarea) {
                const editor = CodeMirror.fromTextArea(textarea, {
                    lineNumbers: true,
                    mode: 'application/x-httpd-php', // Default to PHP
                    theme: 'monokai',
                    indentUnit: 4,
                    indentWithTabs: false,
                    lineWrapping: true,
                    extraKeys: {
                        "Ctrl-S": function(cm) {
                            document.getElementById('save-file-form').submit();
                        }
                    }
                });
                
                // Set mode based on file extension
                const filePath = document.getElementById('file-path').value;
                const ext = filePath.split('.').pop().toLowerCase();
                
                const modeMap = {
                    'php': 'application/x-httpd-php',
                    'js': 'javascript',
                    'css': 'css',
                    'html': 'htmlmixed',
                    'htm': 'htmlmixed',
                    'xml': 'xml',
                    'json': 'application/json',
                    'md': 'markdown',
                    'txt': 'text/plain',
                    'ini': 'properties',
                    'htaccess': 'apache'
                };
                
                if (modeMap[ext]) {
                    editor.setOption('mode', modeMap[ext]);
                }
                
                // Adjust height
                editor.setSize(null, 500);
            }
        }
    }
    
    // File uploader validation
    const fileUploadForm = document.getElementById('uploadFileForm');
    if (fileUploadForm) {
        fileUploadForm.addEventListener('submit', function(e) {
            const fileInput = document.getElementById('file');
            
            if (!fileInput.files.length) {
                e.preventDefault();
                showAlert('Please select a file to upload', 'danger');
                return;
            }
            
            const file = fileInput.files[0];
            
            // Check file size (max 5MB)
            const maxSize = 5 * 1024 * 1024; // 5MB in bytes
            if (file.size > maxSize) {
                e.preventDefault();
                showAlert('File size must be less than 5MB', 'danger');
                return;
            }
            
            showAlert('File upload started...', 'info');
        });
    }
    
    // Display selected file name
    const fileInput = document.getElementById('file');
    const fileLabel = document.querySelector('label[for="file"]');
    
    if (fileInput && fileLabel) {
        fileInput.addEventListener('change', function() {
            if (this.files.length > 0) {
                const fileName = this.files[0].name;
                const fileSize = formatBytes(this.files[0].size);
                fileLabel.textContent = `${fileName} (${fileSize})`;
            } else {
                fileLabel.textContent = 'Choose file';
            }
        });
    }
    
    // Create directory validation
    const createDirForm = document.getElementById('createDirForm');
    if (createDirForm) {
        createDirForm.addEventListener('submit', function(e) {
            const dirName = document.getElementById('dir_name').value;
            
            if (!dirName) {
                e.preventDefault();
                showAlert('Directory name is required', 'danger');
                return;
            }
            
            // Validate directory name (no special characters except dash and underscore)
            const nameRegex = /^[a-zA-Z0-9_-]+$/;
            if (!nameRegex.test(dirName)) {
                e.preventDefault();
                showAlert('Directory name can only contain letters, numbers, dashes, and underscores', 'danger');
                return;
            }
        });
    }
    
    // Handle file/directory deletion confirmation
    document.querySelectorAll('.delete-file-btn').forEach(function(button) {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            
            const itemName = this.getAttribute('data-item-name');
            const itemType = this.getAttribute('data-item-type');
            const form = this.closest('form');
            
            if (confirm(`Are you sure you want to delete this ${itemType} "${itemName}"? This action cannot be undone.`)) {
                form.submit();
            }
        });
    });
    
    // Breadcrumb navigation
    document.querySelectorAll('.breadcrumb-item a').forEach(function(link) {
        link.addEventListener('click', function(e) {
            showAlert('Navigating...', 'info');
        });
    });
    
    // File action buttons
    document.querySelectorAll('.file-action-btn').forEach(function(button) {
        button.addEventListener('click', function() {
            const action = this.getAttribute('data-action');
            
            if (action === 'download') {
                showAlert('Preparing file for download...', 'info');
            } else if (action === 'edit') {
                showAlert('Opening file editor...', 'info');
            } else if (action === 'view') {
                showAlert('Opening file viewer...', 'info');
            }
        });
    });
});

// Helper: get current domain and path
function getDomainAndPath() {
    const domainId = document.getElementById('current-domain-id').value;
    const path = new URLSearchParams(window.location.search).get('path') || '';
    return { domainId, path };
}

// Rename
$(document).on('click', '.rename-file-btn', function() {
    const itemName = $(this).data('item-name');
    const itemType = $(this).data('item-type');
    $('#rename-old-name').val(itemName);
    $('#rename-item-type').val(itemType);
    $('#rename-new-name').val(itemName);
    $('#renameModal').modal('show');
});

$('#renameForm').on('submit', function(e) {
    e.preventDefault();
    const { domainId, path } = getDomainAndPath();
    const oldName = $('#rename-old-name').val();
    const newName = $('#rename-new-name').val();
    $.post(`/files/rename/${domainId}`, { path, old_name: oldName, new_name: newName }, function(resp) {
        if (resp.success) {
            location.reload();
        } else {
            alert(resp.message || 'Rename failed');
        }
    });
});

// Zip
$(document).on('click', '.zip-file-btn', function() {
    if (!confirm('Zip this item?')) return;
    const itemName = $(this).data('item-name');
    const { domainId, path } = getDomainAndPath();
    $.post(`/files/zip/${domainId}`, { path, item_name: itemName }, function(resp) {
        if (resp.success) {
            location.reload();
        } else {
            alert(resp.message || 'Zip failed');
        }
    });
});

// Unzip
$(document).on('click', '.unzip-file-btn', function() {
    if (!confirm('Unzip this archive?')) return;
    const itemName = $(this).data('item-name');
    const { domainId, path } = getDomainAndPath();
    $.post(`/files/unzip/${domainId}`, { path, item_name: itemName }, function(resp) {
        if (resp.success) {
            location.reload();
        } else {
            alert(resp.message || 'Unzip failed');
        }
    });
});

// View Image
$(document).on('click', '.dropdown-item', function(e) {
    const $a = $(this);
    if ($a.text().trim().startsWith('View')) {
        const href = $a.attr('href');
        if (href && /\.(jpg|jpeg|png|gif|svg|bmp|webp)$/i.test(href)) {
            e.preventDefault();
            $('#view-image').attr('src', href);
            $('#viewImageModal').modal('show');
        }
    }
});
