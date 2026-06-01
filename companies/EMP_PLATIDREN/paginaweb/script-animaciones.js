// SCRIPT MEJORADO CON ANIMACIONES PROFESIONALES
// Incluye Scroll Animations, Counters, Parallax, etc.

document.addEventListener('DOMContentLoaded', function() {
    
    // ===== MENÚ HAMBURGUESA =====
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
                navMenu.style.animation = 'slideDown 0.3s ease-out';
            } else {
                navMenu.style.display = 'none';
            }
        });

        navMenu.querySelectorAll('a').forEach(link => {
            link.addEventListener('click', function() {
                menuOpen = false;
                navMenu.style.display = 'none';
            });
        });

        document.addEventListener('click', function(e) {
            if (!e.target.closest('nav') && menuOpen) {
                menuOpen = false;
                navMenu.style.display = 'none';
            }
        });
    }

    // ===== ANIMACIONES AL SCROLL (Scroll Reveal) =====
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver(function(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('aos-animate');
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);

    // Aplica animaciones a elementos con data-aos
    document.querySelectorAll('[data-aos]').forEach(element => {
        observer.observe(element);
    });

    // ===== CONTADOR DE NÚMEROS (Number Counter) =====
    function animateCounter(element, target, duration = 2000) {
        let current = 0;
        const increment = target / (duration / 16);
        const timer = setInterval(() => {
            current += increment;
            if (current >= target) {
                element.textContent = target + (element.textContent.includes('+') ? '+' : '');
                clearInterval(timer);
            } else {
                element.textContent = Math.floor(current) + (element.textContent.includes('+') ? '+' : '');
            }
        }, 16);
    }

    // Anima números cuando son visibles
    const numberObserver = new IntersectionObserver(function(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting && !entry.target.classList.contains('animated')) {
                const number = parseInt(entry.target.textContent);
                if (!isNaN(number)) {
                    entry.target.classList.add('animated');
                    animateCounter(entry.target, number);
                }
            }
        });
    }, observerOptions);

    document.querySelectorAll('.stat-number').forEach(element => {
        numberObserver.observe(element);
    });

    // ===== FILTRO PRODUCTOS =====
    window.filterProducts = function(categoria) {
        const productos = document.querySelectorAll('.producto-card');
        const tabs = document.querySelectorAll('.tab-btn');
        
        tabs.forEach(tab => tab.classList.remove('active'));
        event.target.classList.add('active');

        productos.forEach((prod, index) => {
            if (categoria === 'all' || prod.dataset.categoria === categoria) {
                prod.style.display = 'block';
                prod.style.animation = `zoomInCard 0.6s cubic-bezier(0.34, 1.56, 0.64, 1) ${index * 0.05}s forwards`;
            } else {
                prod.style.display = 'none';
            }
        });
    };

    // ===== FAQ TOGGLE =====
    window.toggleFAQ = function(element) {
        const answer = element.nextElementSibling;
        const toggle = element.querySelector('.faq-toggle');
        
        document.querySelectorAll('.faq-answer').forEach(ans => {
            if (ans !== answer) {
                ans.classList.remove('show');
                ans.previousElementSibling.classList.remove('active');
                ans.previousElementSibling.querySelector('.faq-toggle').classList.remove('active');
            }
        });

        answer.classList.toggle('show');
        element.classList.toggle('active');
        toggle.classList.toggle('active');
    };

    // ===== FORMULARIO CONTACTO =====
    const contactForm = document.getElementById('contacto-form');
    if (contactForm) {
        contactForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            // Animación de éxito
            const submitBtn = this.querySelector('button[type="submit"]');
            const originalText = submitBtn.textContent;
            submitBtn.textContent = '✓ ¡Enviado!';
            submitBtn.style.background = 'linear-gradient(135deg, #2ecc71, #27ae60)';
            
            setTimeout(() => {
                alert('¡Gracias! Tu solicitud ha sido recibida. Nos contactaremos pronto.');
                this.reset();
                submitBtn.textContent = originalText;
                submitBtn.style.background = '';
            }, 1500);
        });
    }

    // ===== PARALLAX EFFECT =====
    const parallaxElements = document.querySelectorAll('.hero::before, .hero::after');
    window.addEventListener('scroll', () => {
        const scrollY = window.scrollY;
        parallaxElements.forEach(el => {
            el.style.transform = `translateY(${scrollY * 0.5}px)`;
        });
    });

    // ===== SMOOTH SCROLL =====
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            const href = this.getAttribute('href');
            if (href !== '#' && document.querySelector(href)) {
                e.preventDefault();
                const target = document.querySelector(href);
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });

    // ===== ANIMACIÓN DE SCROLL INDICATOR =====
    const scrollIndicator = document.createElement('style');
    scrollIndicator.innerHTML = `
        @keyframes slideDown {
            from {
                opacity: 0;
                transform: translateY(-10px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        @keyframes zoomInCard {
            from {
                opacity: 0;
                transform: scale(0.8);
            }
            to {
                opacity: 1;
                transform: scale(1);
            }
        }
    `;
    document.head.appendChild(scrollIndicator);

    // ===== LIGHT BOX / HOVER EFFECTS =====
    document.querySelectorAll('.service-card, .producto-card, .testimonio-card').forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-8px)';
            this.style.boxShadow = 'var(--shadow-lg)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
            this.style.boxShadow = 'var(--shadow-sm)';
        });
    });

    // ===== ANIMACIÓN DE LOADING =====
    const style = document.createElement('style');
    style.innerHTML = `
        @keyframes spin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
        }
        
        .loading {
            animation: spin 1s linear infinite;
        }
    `;
    document.head.appendChild(style);

    // ===== ANIMACIÓN AL CAMBIAR TABS =====
    window.addEventListener('click', function(e) {
        if (e.target.classList.contains('tab-btn')) {
            const allBtns = document.querySelectorAll('.tab-btn');
            allBtns.forEach(btn => btn.style.animation = 'none');
            setTimeout(() => {
                e.target.style.animation = 'tabActive 0.3s ease-out';
            }, 10);
        }
    });

    // ===== EFECTO RIPPLE EN BOTONES =====
    document.querySelectorAll('.btn').forEach(btn => {
        btn.addEventListener('click', function(e) {
            const ripple = document.createElement('span');
            const rect = this.getBoundingClientRect();
            const size = Math.max(rect.width, rect.height);
            const x = e.clientX - rect.left - size / 2;
            const y = e.clientY - rect.top - size / 2;
            
            ripple.style.position = 'absolute';
            ripple.style.width = ripple.style.height = size + 'px';
            ripple.style.left = x + 'px';
            ripple.style.top = y + 'px';
            ripple.style.borderRadius = '50%';
            ripple.style.background = 'rgba(255, 255, 255, 0.6)';
            ripple.style.pointerEvents = 'none';
            ripple.style.animation = 'ripple 0.6s ease-out';
            
            this.style.position = 'relative';
            this.style.overflow = 'hidden';
            this.appendChild(ripple);
            
            setTimeout(() => ripple.remove(), 600);
        });
    });

    // Agregar animación ripple al CSS
    const rippleStyle = document.createElement('style');
    rippleStyle.innerHTML = `
        @keyframes ripple {
            to {
                transform: scale(4);
                opacity: 0;
            }
        }
    `;
    document.head.appendChild(rippleStyle);

    // ===== ANIMACIÓN DE ENTRADA DE PÁGINA =====
    document.body.style.animation = 'fadeIn 0.6s ease-out';

    // ===== OBSERVAR CAMBIOS EN VIEWPORT =====
    const elementsToAnimate = document.querySelectorAll('.section-title, .section-subtitle');
    elementsToAnimate.forEach(element => {
        observer.observe(element);
    });
});

// ===== SCROLL LISTENER PARA EFECTOS ESPECIALES =====
window.addEventListener('scroll', () => {
    // Cambiar opacity del header en scroll
    const header = document.querySelector('header');
    if (window.scrollY > 0) {
        header.style.boxShadow = 'var(--shadow-md)';
    } else {
        header.style.boxShadow = 'var(--shadow-sm)';
    }
});
