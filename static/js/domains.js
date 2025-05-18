document.addEventListener('DOMContentLoaded', function() {
    // Domain form validation
    const addDomainForm = document.getElementById('addDomainForm');
    if (addDomainForm) {
        addDomainForm.addEventListener('submit', function(e) {
            const domainName = document.getElementById('domain_name').value;
            const isSubdomain = document.getElementById('is_subdomain').checked;
            const parentDomain = document.getElementById('parent_domain').value;
            
            // Basic validation
            if (!domainName) {
                e.preventDefault();
                showAlert('Domain name is required', 'danger');
                return;
            }
            
            // Validate domain name format
            const domainRegex = /^[a-zA-Z0-9][a-zA-Z0-9-]{0,61}[a-zA-Z0-9](?:\.[a-zA-Z]{2,})+$/;
            const subdomainRegex = /^[a-zA-Z0-9][a-zA-Z0-9-]{0,61}[a-zA-Z0-9]$/;
            
            if (isSubdomain) {
                if (!parentDomain) {
                    e.preventDefault();
                    showAlert('Parent domain is required for subdomains', 'danger');
                    return;
                }
                
                if (!subdomainRegex.test(domainName)) {
                    e.preventDefault();
                    showAlert('Invalid subdomain format', 'danger');
                    return;
                }
            } else {
                if (!domainRegex.test(domainName)) {
                    e.preventDefault();
                    showAlert('Invalid domain format', 'danger');
                    return;
                }
            }
        });
    }
    
    // Toggle subdomain options
    const isSubdomainCheckbox = document.getElementById('is_subdomain');
    const parentDomainGroup = document.getElementById('parent_domain_group');
    
    if (isSubdomainCheckbox && parentDomainGroup) {
        isSubdomainCheckbox.addEventListener('change', function() {
            if (this.checked) {
                parentDomainGroup.classList.remove('d-none');
                document.getElementById('parent_domain').setAttribute('required', 'required');
            } else {
                parentDomainGroup.classList.add('d-none');
                document.getElementById('parent_domain').removeAttribute('required');
            }
        });
        
        // Initialize on page load
        if (isSubdomainCheckbox.checked) {
            parentDomainGroup.classList.remove('d-none');
            document.getElementById('parent_domain').setAttribute('required', 'required');
        } else {
            parentDomainGroup.classList.add('d-none');
            document.getElementById('parent_domain').removeAttribute('required');
        }
    }
    
    // Domain availability check
    const domainInput = document.getElementById('domain_name');
    const domainAvailabilityFeedback = document.getElementById('domain-availability');
    
    if (domainInput && domainAvailabilityFeedback) {
        let debounceTimer;
        
        domainInput.addEventListener('input', function() {
            clearTimeout(debounceTimer);
            
            const domain = this.value.trim();
            if (!domain) {
                domainAvailabilityFeedback.innerHTML = '';
                return;
            }
            
            debounceTimer = setTimeout(async function() {
                try {
                    const response = await fetch(`/domains/api/check/${domain}`);
                    const data = await response.json();
                    
                    if (!data.valid) {
                        domainAvailabilityFeedback.innerHTML = '<div class="text-danger">Invalid domain format</div>';
                    } else if (!data.available) {
                        domainAvailabilityFeedback.innerHTML = '<div class="text-danger">Domain already exists</div>';
                    } else {
                        domainAvailabilityFeedback.innerHTML = '<div class="text-success">Domain is available</div>';
                    }
                } catch (error) {
                    console.error('Error checking domain:', error);
                    domainAvailabilityFeedback.innerHTML = '';
                }
            }, 500);
        });
    }
    
    // Handle domain deletion confirmation
    document.querySelectorAll('.delete-domain-btn').forEach(function(button) {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            
            const domainName = this.getAttribute('data-domain-name');
            const form = this.closest('form');
            
            if (confirm(`Are you sure you want to delete the domain "${domainName}"? This action cannot be undone.`)) {
                form.submit();
            }
        });
    });
    
    // Load domains for parent domain select
    const parentDomainSelect = document.getElementById('parent_domain');
    if (parentDomainSelect) {
        fetch('/domains/api/list')
            .then(response => response.json())
            .then(domains => {
                // Filter out subdomains
                const parentDomains = domains.filter(d => !d.is_subdomain);
                
                // Clear existing options except the default one
                while (parentDomainSelect.options.length > 1) {
                    parentDomainSelect.remove(1);
                }
                
                // Add domain options
                parentDomains.forEach(domain => {
                    const option = document.createElement('option');
                    option.value = domain.name;
                    option.textContent = domain.name;
                    parentDomainSelect.appendChild(option);
                });
            })
            .catch(error => console.error('Error loading domains:', error));
    }
});
