// Injects the shared footer.html into the current page
// function injectSharedFooter() {
    // Use relative path for compatibility
//     fetch('footer.html')
//         .then(response => {
//             if (!response.ok) throw new Error('Not found');
//             return response.text();
//         })
//         .then(html => {
//             document.querySelectorAll('footer.site-footer').forEach(el => el.remove());
//             const footerContainer = document.createElement('div');
//             footerContainer.innerHTML = html;
//             document.body.appendChild(footerContainer);
//         });
// }
// window.addEventListener('DOMContentLoaded', injectSharedFooter);

// Injects the shared footer.html into the current page
function injectSharedFooter() {
    fetch('/footer.html')  // use absolute path (root-based)
        .then(response => {
            if (!response.ok) throw new Error('Footer not found');
            return response.text();
        })
        .then(html => {
            // Remove any existing injected footer
            document.querySelectorAll('footer.site-footer').forEach(el => el.remove());
            // Insert at the end of body
            document.body.insertAdjacentHTML('beforeend', html);
        })
        .catch(err => console.error('Footer injection failed:', err));
}

window.addEventListener('DOMContentLoaded', injectSharedFooter);
