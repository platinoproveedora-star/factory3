// MENÚ HAMBURGUESA
document.addEventListener('DOMContentLoaded', function() {
    const hamburger = document.querySelector('.hamburger');
    const navMenu = document.querySelector('.nav-menu');
    let menuOpen = false;

    if (hamburger && navMenu) {
        hamburger.addEventListener('click', function(e) {
            e.stopPropagation();
            menuOpen = !menuOpen;
            if (menuOpen) {
                navMenu.style.display = 'flex';
                navMenu.style.position = 'absolute';
                navMenu.style.top = '100%';
                navMenu.style.left = '0';
                navMenu.style.right = '0';
                navMenu.style.background = 'white';
                navMenu.style.flexDirection = 'column';
                navMenu.style.padding = '1.5rem';
                navMenu.style.gap = '1rem';
                navMenu.style.boxShadow = 'var(--shadow-md)';
                navMenu.style.zIndex = '999';
                navMenu.style.borderTop = '1px solid var(--gray-200)';
            } else {
                navMenu.style.display = 'none';
            }
        });

        // Cerrar menú al hacer click en un enlace
        navMenu.querySelectorAll('a').forEach(link => {
            link.addEventListener('click', function() {
                menuOpen = false;
                navMenu.style.display = 'none';
            });
        });

        // Cerrar menú al hacer click fuera
        document.addEventListener('click', function(e) {
            if (!e.target.closest('nav') && menuOpen) {
                menuOpen = false;
                navMenu.style.display = 'none';
            }
        });
    }

    // FILTRO PRODUCTOS
    window.filterProducts = function(categoria) {
        const productos = document.querySelectorAll('[data-categoria]');
        const tabs = document.querySelectorAll('.tab-btn');
        
        tabs.forEach(tab => tab.classList.remove('active'));
        event.target.classList.add('active');

        productos.forEach(prod => {
            if (categoria === 'all' || prod.dataset.categoria === categoria) {
                prod.style.display = 'block';
            } else {
                prod.style.display = 'none';
            }
        });
    };

    // FAQ TOGGLE
    window.toggleFAQ = function(element) {
        const answer = element.nextElementSibling;
        const toggle = element.querySelector('.faq-toggle');
        
        // Cerrar otros FAQs
        document.querySelectorAll('.faq-answer').forEach(ans => {
            if (ans !== answer) {
                ans.classList.remove('show');
                ans.previousElementSibling.classList.remove('active');
                ans.previousElementSibling.querySelector('.faq-toggle').classList.remove('active');
            }
        });

        // Toggle actual
        answer.classList.toggle('show');
        element.classList.toggle('active');
        toggle.classList.toggle('active');
    };

    // ANIMACIÓN TUBOS — service cards
    const serviceCards = document.querySelectorAll('.service-card');
    if (serviceCards.length) {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const all = document.querySelectorAll('.service-card');
                    all.forEach((card, i) => {
                        setTimeout(() => card.classList.add('visible'), i * 110);
                    });
                    observer.disconnect();
                }
            });
        }, { threshold: 0.15 });
        observer.observe(serviceCards[0]);
    }

    // FORMULARIO CONTACTO
    const contactForm = document.getElementById('contacto-form');
    if (contactForm) {
        contactForm.addEventListener('submit', function(e) {
            e.preventDefault();
            alert('¡Gracias! Tu solicitud ha sido recibida. Nos contactaremos pronto.');
            this.reset();
        });
    }
});
