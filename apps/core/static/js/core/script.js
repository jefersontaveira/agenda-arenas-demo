document.addEventListener('DOMContentLoaded', () => {

    // 1. Rolagem Suave para links internos
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();

            const targetId = this.getAttribute('href');
            const targetElement = document.querySelector(targetId);

            if (targetElement) {
                targetElement.scrollIntoView({
                    behavior: 'smooth'
                });
            }
        });
    });

    // 2. Manipulação do Formulário (Envia para o WhatsApp)
    const form = document.getElementById('contactForm');

    form.addEventListener('submit', (e) => {
        e.preventDefault();

        // Pega os valores dos campos pelos IDs que criamos
        const nome = document.getElementById('nome').value;
        const email = document.getElementById('email').value;
        const whatsapp = document.getElementById('whatsapp').value;
        const plano = document.getElementById('plano').value;

        // Número do dono do sistema (Coloque o seu aqui com código do país 55 + DDD)
        const phoneReceiver = "5585999999999";

        // Cria a mensagem formatada (usando quebra de linha %0a)
        const message = `*Olá! Tenho interesse no GestãoNexus.*%0a%0a` +
                        `👤 *Nome:* ${nome}%0a` +
                        `📧 *Email:* ${email}%0a` +
                        `📱 *Zap do Cliente:* ${whatsapp}%0a` +
                        `🏆 *Plano Escolhido:* ${plano}%0a%0a` +
                        `Podemos conversar?`;

        // Cria o link da API do WhatsApp
        const url = `https://wa.me/${phoneReceiver}?text=${message}`;

        // Abre em uma nova aba
        window.open(url, '_blank');

        // Feedback visual e limpa o formulário
        alert('Redirecionando para o WhatsApp do consultor...');
        form.reset();
    });

    // 3. Efeito simples na Navbar ao rolar
    const navbar = document.querySelector('.navbar');
    window.addEventListener('scroll', () => {
        if (window.scrollY > 50) {
            navbar.style.background = 'rgba(18, 18, 18, 1)';
            navbar.style.boxShadow = '0 2px 10px rgba(0,0,0,0.5)';
        } else {
            navbar.style.background = 'rgba(18, 18, 18, 0.95)';
            navbar.style.boxShadow = 'none';
        }
    });

    // 4. Animação dos Contadores (Versão Corrigida e Suave)
    const counters = document.querySelectorAll('.counter');
    const duration = 2000; // Tempo da animação em milissegundos (2 segundos)

    const runCounter = (el) => {
        const target = +el.getAttribute('data-target'); // Onde quer chegar (ex: 0 ou 100)
        const start = +el.innerText; // De onde sai (ex: 50 ou 0)
        const startTime = performance.now(); // Marca a hora que começou

        const updateCount = (currentTime) => {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1); // Calcula % completado (0 a 1)

            // Fórmula mágica: Pega o valor inicial e soma a diferença multiplicada pelo progresso
            // Math.floor garante números inteiros
            const current = Math.floor(progress * (target - start) + start);

            el.innerText = current;

            if (progress < 1) {
                requestAnimationFrame(updateCount); // Continua animando
            } else {
                el.innerText = target; // Garante que termine no número exato
            }
        };

        requestAnimationFrame(updateCount);
    };

    // Observer para disparar apenas quando aparecer na tela
    const sectionObserver = new IntersectionObserver((entries) => {
        if (entries[0].isIntersecting) {
            counters.forEach(counter => runCounter(counter));
            sectionObserver.disconnect(); // Desconecta para não rodar de novo
        }
    }, { threshold: 0.5 });

    const securitySection = document.querySelector('.security');
    if (securitySection) {
        sectionObserver.observe(securitySection);
    }

    // 5. Sistema de Tabs Interativas (Tour do Sistema)
    const tourBtns = document.querySelectorAll('.tour-btn');
    const featureTitle = document.getElementById('feature-title');
    const featureDesc = document.getElementById('feature-desc');
    const featureImg = document.getElementById('feature-img');
    const tourContent = document.querySelector('.tour-content');

    // --- Lógica das Bolinhas (Dots) ---
    const dotsContainer = document.getElementById('tour-dots');

    // 1. Cria as bolinhas dinamicamente
    systemData.forEach((_, index) => {
        const dot = document.createElement('div');
        dot.classList.add('dot');
        if (index === 0) dot.classList.add('active'); // A primeira começa ativa
        dot.setAttribute('data-id', index);

        // Permite clicar na bolinha para mudar
        dot.addEventListener('click', () => {
            tourBtns[index].click(); // Simula clique no botão original
        });

        dotsContainer.appendChild(dot);
    });

    // 2. Atualiza a função de clique existente para mudar a bolinha também
    const allDots = document.querySelectorAll('.dot');

    tourBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            // ... (seu código existente de trocar conteúdo) ...

            // ATUALIZAÇÃO: Muda a cor da bolinha
            const index = btn.getAttribute('data-id');

            allDots.forEach(dot => dot.classList.remove('active')); // Limpa todas
            if(allDots[index]) {
                allDots[index].classList.add('active'); // Ativa a certa
            }
        });
    });

    tourBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            // Remove classe active de todos
            tourBtns.forEach(b => b.classList.remove('active'));
            // Adiciona ao clicado
            btn.classList.add('active');

            // Pega o índice do botão clicado
            const index = btn.getAttribute('data-id');
            const data = systemData[index];

            // Animação de saída rápida
            tourContent.style.opacity = 0;

            setTimeout(() => {
                // Atualiza o conteúdo
                featureTitle.innerText = data.title;
                featureDesc.innerText = data.desc;
                featureImg.src = data.img;

                // Animação de entrada
                tourContent.style.opacity = 1;
                featureImg.classList.remove('fade-anim'); // Reseta animação
                void featureImg.offsetWidth; // Trigger reflow
                featureImg.classList.add('fade-anim');
            }, 200);
        });
    });

    // Para o tour responsivo
    // --- Lógica de Swipe (Arrastar) para Mobile ---
    let touchStartX = 0;
    let touchEndX = 0;

    const tourSection = document.querySelector('.tour-content');

    // Captura onde o dedo tocou
    tourSection.addEventListener('touchstart', e => {
        touchStartX = e.changedTouches[0].screenX;
    });

    // Captura onde o dedo soltou
    tourSection.addEventListener('touchend', e => {
        touchEndX = e.changedTouches[0].screenX;
        handleSwipe();
    });

    function handleSwipe() {
        // Descobre qual botão está ativo agora
        const currentBtn = document.querySelector('.tour-btn.active');
        const currentIndex = parseInt(currentBtn.getAttribute('data-id'));

        // Defina a sensibilidade (quanto precisa arrastar para contar)
        const threshold = 50;

        if (touchEndX < touchStartX - threshold) {
            // Arrastou para ESQUERDA (Próximo Item)
            const nextIndex = currentIndex + 1;
            if (nextIndex < tourBtns.length) {
                tourBtns[nextIndex].click(); // Simula o clique no próximo botão
                scrollMenuToButton(tourBtns[nextIndex]); // Função extra para centralizar o botão
            }
        }

        if (touchEndX > touchStartX + threshold) {
            // Arrastou para DIREITA (Item Anterior)
            const prevIndex = currentIndex - 1;
            if (prevIndex >= 0) {
                tourBtns[prevIndex].click();
                scrollMenuToButton(tourBtns[prevIndex]);
            }
        }
    }

    // Função Extra: Faz o menu rolar automaticamente para mostrar o botão ativo
    function scrollMenuToButton(button) {
        const menu = document.querySelector('.tour-menu');
        const scrollLeft = button.offsetLeft - (menu.offsetWidth / 2) + (button.offsetWidth / 2);
        menu.scrollTo({
            left: scrollLeft,
            behavior: 'smooth'
        });
    }

    // Atualize seu clique existente para usar a rolagem também
    tourBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            // ... (seu código existente de trocar conteúdo) ...

            // Adicione isso no final do evento click:
            if (window.innerWidth <= 768) {
                scrollMenuToButton(btn);
            }
        });
    });

    // 6. Menu Mobile (Toggle)
    const mobileMenu = document.getElementById('mobile-menu');
    const navLinks = document.querySelector('.nav-links');
    const navItems = document.querySelectorAll('.nav-links li a');

    // 1. Abrir/Fechar ao clicar no ícone
    mobileMenu.addEventListener('click', () => {
        mobileMenu.classList.toggle('is-active'); // Transforma em X
        navLinks.classList.toggle('active');      // Desliza o menu
    });

    // 2. Fechar automaticamente ao clicar em um link
    navItems.forEach(item => {
        item.addEventListener('click', () => {
            // Remove as classes ativas para fechar o menu
            mobileMenu.classList.remove('is-active');
            navLinks.classList.remove('active');
        });
    });


});