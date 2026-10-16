// --- apps/scheduler/static/scheduler/js/arena_home.js ---

// --- VARIÁVEIS GLOBAIS ---
let currentBasePrice = 0;
let currentTotal = 0;
let currentCourtsData = [];
let currentEquipmentsData = [];

// Chave para persistência local do atleta
const ATHLETE_STORAGE_KEY = 'arena_athlete_' + (typeof ARENA_SLUG !== 'undefined' ? ARENA_SLUG : 'default');

// --- UTILITÁRIOS DE ATLETA / LOCALSTORAGE ---
function getSavedPlayer() {
    try {
        const slug = (typeof ARENA_SLUG !== 'undefined') ? ARENA_SLUG : 'default';
        const keys = [
            'arena_athlete_' + slug,
            'athlete_session_' + slug,
            'athlete_profile',
            ATHLETE_STORAGE_KEY
        ];
        for (const key of keys) {
            const raw = localStorage.getItem(key);
            if (raw) {
                const parsed = JSON.parse(raw);
                if (parsed && (parsed.name || parsed.phone)) {
                    return parsed;
                }
            }
        }
    } catch (e) {
        console.error('Erro ao ler dados do atleta:', e);
    }
    return null;
}

function savePlayerLocally(data) {
    if (!data) return;
    try {
        const slug = (typeof ARENA_SLUG !== 'undefined') ? ARENA_SLUG : 'default';
        const current = getSavedPlayer() || {};
        const merged = { ...current, ...data };
        const json = JSON.stringify(merged);
        localStorage.setItem(ATHLETE_STORAGE_KEY, json);
        localStorage.setItem('arena_athlete_' + slug, json);
        localStorage.setItem('athlete_session_' + slug, json);
        localStorage.setItem('athlete_profile', json);

        // Salva cookie do telefone para compatibilidade
        if (merged.phone) {
            const phoneVal = encodeURIComponent(merged.phone);
            document.cookie = `last_customer_phone=${phoneVal}; path=/; max-age=2592000`;
        }
    } catch (e) {
        console.error('Erro ao salvar dados do atleta:', e);
    }
    updateNavbarUI();
    prefillBookingModalWithPlayerData();
}

function clearSavedPlayer() {
    try {
        const slug = (typeof ARENA_SLUG !== 'undefined') ? ARENA_SLUG : 'default';
        localStorage.removeItem(ATHLETE_STORAGE_KEY);
        localStorage.removeItem('arena_athlete_' + slug);
        localStorage.removeItem('athlete_session_' + slug);
        localStorage.removeItem('athlete_profile');
        document.cookie = 'last_customer_phone=; path=/; max-age=0';
    } catch (e) {
        console.error('Erro ao limpar atleta:', e);
    }
    updateNavbarUI();
}

function updateNavbarUI() {
    const player = getSavedPlayer();
    const guestNav = document.getElementById('playerGuestNav');
    const identifiedNav = document.getElementById('playerIdentifiedNav');
    const nameSpan = document.getElementById('navPlayerName');

    if (player && (player.name || player.phone)) {
        if (guestNav) guestNav.classList.add('d-none');
        if (identifiedNav) {
            identifiedNav.classList.remove('d-none');
            identifiedNav.classList.add('d-flex');
        }
        if (nameSpan) {
            const firstName = (player.name || '').trim().split(' ')[0] || 'Atleta';
            nameSpan.innerText = firstName;
        }
    } else {
        if (guestNav) guestNav.classList.remove('d-none');
        if (identifiedNav) {
            identifiedNav.classList.add('d-none');
            identifiedNav.classList.remove('d-flex');
        }
    }
}

// --- FORMATAÇÃO DE DADOS ---
function formatPhone(val) {
    if (!val) return '';
    const digits = val.replace(/\D/g, '');
    if (digits.length <= 10) {
        return digits.replace(/(\d{2})(\d{4})(\d{0,4})/, '($1) $2-$3').replace(/-$/, '');
    }
    return digits.replace(/(\d{2})(\d{5})(\d{0,4})/, '($1) $2-$3').replace(/-$/, '');
}

function formatCPF(val) {
    if (!val) return '';
    const digits = val.replace(/\D/g, '').substring(0, 11);
    return digits.replace(/(\d{3})(\d{3})?(\d{3})?(\d{0,2})?/, function(m, p1, p2, p3, p4) {
        let res = p1;
        if (p2) res += '.' + p2;
        if (p3) res += '.' + p3;
        if (p4) res += '-' + p4;
        return res;
    });
}

function isValidCPF(cpf) {
    cpf = cpf.replace(/\D/g, '');
    if (cpf.length !== 11 || /^(\d)\1{10}$/.test(cpf)) return false;
    let sum = 0, rest;
    for (let i = 1; i <= 9; i++) sum = sum + parseInt(cpf.substring(i-1, i)) * (11 - i);
    rest = (sum * 10) % 11;
    if ((rest == 10) || (rest == 11)) rest = 0;
    if (rest != parseInt(cpf.substring(9, 10))) return false;
    sum = 0;
    for (let i = 1; i <= 10; i++) sum = sum + parseInt(cpf.substring(i-1, i)) * (12 - i);
    rest = (sum * 10) % 11;
    if ((rest == 10) || (rest == 11)) rest = 0;
    if (rest != parseInt(cpf.substring(10, 11))) return false;
    return true;
}

// --- AJAX SLOTS FETCHING ---
async function fetchAndSwapSlots(url, silent = false) {
    const slotsContainer = document.getElementById('slots-container');
    const modalitiesContainer = document.getElementById('modalities-container');
    const dateText = document.getElementById('display-date-text');
    
    if (!slotsContainer) return;
    
    // Se o modal de reserva estiver aberto e a atualização for silenciosa, não interrompe o preenchimento
    const modalEl = document.getElementById('bookingModal');
    const isModalOpen = modalEl && modalEl.classList.contains('show');
    if (isModalOpen && silent) {
        return;
    }

    if (!silent) {
        slotsContainer.style.opacity = '0.5';
        if (modalitiesContainer) modalitiesContainer.style.opacity = '0.5';
    }
    
    try {
        const fetchUrl = new URL(url, window.location.href);
        fetchUrl.searchParams.set('_ts', Date.now().toString());

        const res = await fetch(fetchUrl.toString(), {
            cache: 'no-store',
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        });
        const html = await res.text();
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');
        
        const newSlots = doc.getElementById('slots-container');
        if (newSlots) {
            // Só altera o DOM se houver mudanças reais para evitar piscar na tela
            if (!silent || newSlots.innerHTML.trim() !== slotsContainer.innerHTML.trim()) {
                slotsContainer.innerHTML = newSlots.innerHTML;
            }
        }
        
        const newModalities = doc.getElementById('modalities-container');
        if (newModalities && modalitiesContainer) {
            if (!silent || newModalities.innerHTML.trim() !== modalitiesContainer.innerHTML.trim()) {
                modalitiesContainer.innerHTML = newModalities.innerHTML;
            }
        }

        const newDateText = doc.getElementById('display-date-text');
        if (newDateText && dateText) {
            dateText.innerText = newDateText.innerText;
        }
        
        // Atualiza os inputs do form de data para sincronia
        const newDateForm = doc.getElementById('dateForm');
        const oldDateForm = document.getElementById('dateForm');
        if (newDateForm && oldDateForm) {
            const newModality = newDateForm.querySelector('input[name="modality"]');
            const oldModality = oldDateForm.querySelector('input[name="modality"]');
            if (newModality && oldModality) oldModality.value = newModality.value;

            const newDate = newDateForm.querySelector('input[name="date"]');
            const oldDate = oldDateForm.querySelector('input[name="date"]');
            if (newDate && oldDate) {
                oldDate.value = newDate.value;
                if (oldDate._flatpickr) {
                    oldDate._flatpickr.setDate(newDate.value, false);
                }
            }
        }
        
        if (!silent) {
            window.history.pushState({}, '', url);
        }
    } catch (e) {
        console.error("Erro ao buscar slots:", e);
    } finally {
        if (!silent) {
            slotsContainer.style.opacity = '1';
            if (modalitiesContainer) modalitiesContainer.style.opacity = '1';
        }
    }
}

// --- INICIALIZAÇÃO DOM E CICLO DE VIDA ---
updateNavbarUI();

window.addEventListener('pageshow', function(e) {
    updateNavbarUI();
    prefillBookingModalWithPlayerData();
    // Ao voltar da tela de pagamento, sucesso ou pelo botão Voltar do navegador, atualiza os horários na hora
    fetchAndSwapSlots(window.location.href, true);
});

document.addEventListener('visibilitychange', function() {
    if (document.visibilityState === 'visible') {
        updateNavbarUI();
        prefillBookingModalWithPlayerData();
        // Quando o usuário volta à aba do navegador, atualiza horários silenciosamente
        fetchAndSwapSlots(window.location.href, true);
    }
});

// Atualização automática em segundo plano a cada 8 segundos (sincroniza novas reservas em tempo real)
setInterval(function() {
    if (document.visibilityState === 'visible') {
        const modalEl = document.getElementById('bookingModal');
        if (!modalEl || !modalEl.classList.contains('show')) {
            fetchAndSwapSlots(window.location.href, true);
        }
    }
}, 8000);

window.addEventListener('storage', function(e) {
    if (e.key && (e.key.includes('athlete') || e.key.includes('arena_athlete'))) {
        updateNavbarUI();
        prefillBookingModalWithPlayerData();
    }
});

document.addEventListener('DOMContentLoaded', function() {
    updateNavbarUI();

    // Inicializa o Flatpickr
    const cardElement = document.getElementById('date-card-trigger');
    if (cardElement) {
        const fp = flatpickr("#dateInput", {
            locale: "pt",
            minDate: "today",
            dateFormat: "Y-m-d",
            disableMobile: "true",
            positionElement: cardElement,
            onChange: function(selectedDates, dateStr, instance) {
                const dateForm = document.getElementById('dateForm');
                if (dateForm) {
                    const params = new URLSearchParams(new FormData(dateForm)).toString();
                    fetchAndSwapSlots('?' + params);
                }
            }
        });

        cardElement.addEventListener('click', function() {
            fp.open();
        });
    }

    // Salva dados do atleta ao submeter o formulário de reserva
    const bookingForm = document.querySelector('form[action*="booking_action"]');
    if (bookingForm) {
        bookingForm.addEventListener('submit', function(e) {
            const nameInput = bookingForm.querySelector('input[name="customer_name"]');
            const phoneInput = bookingForm.querySelector('input[name="customer_phone"]');
            const cpfInput = bookingForm.querySelector('input[name="customer_cpf"]');
            const emailInput = bookingForm.querySelector('input[name="customer_email"]');
            
            let isValid = true;
            
            // Valida Nome (Mínimo de 2 palavras)
            if (nameInput) {
                const nameVal = nameInput.value.trim();
                const errorName = document.getElementById('error-name');
                if (nameVal.split(' ').filter(v=>v).length < 2 || nameVal.length < 5) {
                    nameInput.classList.add('is-invalid');
                    if (errorName) {
                        errorName.style.display = 'block';
                        errorName.innerText = 'Digite seu nome completo (Nome e Sobrenome)';
                    }
                    isValid = false;
                } else {
                    nameInput.classList.remove('is-invalid');
                    nameInput.classList.add('is-valid');
                    if (errorName) errorName.style.display = 'none';
                }
            }

            // Valida Telefone
            if (phoneInput) {
                const phoneVal = phoneInput.value.replace(/\D/g, '');
                let errorPhone = document.getElementById('error-phone');
                if (!errorPhone) {
                    errorPhone = document.createElement('div');
                    errorPhone.id = 'error-phone';
                    errorPhone.className = 'text-danger small mt-1';
                    phoneInput.parentNode.appendChild(errorPhone);
                }
                
                if (phoneVal.length < 10 || phoneVal.length > 11) {
                    phoneInput.classList.add('is-invalid');
                    errorPhone.style.display = 'block';
                    errorPhone.innerText = 'Digite um celular válido (com DDD)';
                    isValid = false;
                } else {
                    phoneInput.classList.remove('is-invalid');
                    phoneInput.classList.add('is-valid');
                    errorPhone.style.display = 'none';
                }
            }

            // Valida CPF
            if (cpfInput) {
                const cpfVal = cpfInput.value.replace(/\D/g, '');
                const errorCpf = document.getElementById('error-cpf');
                if (!isValidCPF(cpfVal)) {
                    cpfInput.classList.add('is-invalid');
                    if (errorCpf) {
                        errorCpf.style.display = 'block';
                        errorCpf.innerText = 'CPF inválido ou incorreto';
                    }
                    isValid = false;
                } else {
                    cpfInput.classList.remove('is-invalid');
                    cpfInput.classList.add('is-valid');
                    if (errorCpf) errorCpf.style.display = 'none';
                }
            }

            if (!isValid) {
                e.preventDefault(); // Impede o envio se houver erros
                return;
            }

            // Modo Demonstração: impede geração de cobrança PIX real no site público
            const pType = document.getElementById('inputPaymentType') ? document.getElementById('inputPaymentType').value : 'total';
            if (pType !== 'venue' && pType !== 'local') {
                e.preventDefault();
                alert("🔒 Modo de Demonstração:\n\nOs pagamentos online via PIX real estão desativados neste ambiente de testes para evitar cobranças financeiras reais.\n\nPara testar a grade de agendamentos e o controle das quadras livremente, acesse o Painel do Gestor!");
                return;
            }

            // Salva dados locais se tudo estiver OK
            const name = nameInput ? nameInput.value.trim() : '';
            const phone = phoneInput ? phoneInput.value.replace(/\D/g, '') : '';
            const cpf = cpfInput ? cpfInput.value.replace(/\D/g, '') : '';
            const email = emailInput ? emailInput.value.trim() : '';

            if (phone) {
                savePlayerLocally({
                    name: name,
                    phone: phone,
                    cpf: cpf,
                    email: email
                });
            }
        });
    }

    // Interceptar clique nas modalidades
    document.addEventListener('click', function(e) {
        const modalityBtn = e.target.closest('.modality-btn');
        if (modalityBtn) {
            e.preventDefault();
            fetchAndSwapSlots(modalityBtn.getAttribute('href'));
        }
    });

    window.addEventListener('popstate', function() {
        fetchAndSwapSlots(window.location.href);
    });

    // --- MÁSCARAS E VALIDAÇÕES DE TELEFONE ---
    const phoneInputs = document.querySelectorAll('input[name="customer_phone"], #searchPhone, #playerLoginPhone, #profilePhone');
    phoneInputs.forEach(input => {
        input.addEventListener('input', function(e) {
            e.target.value = formatPhone(e.target.value);
        });

        input.addEventListener('blur', function() {
            const numOnly = this.value.replace(/\D/g, '');
            if (numOnly.length >= 10) {
                this.classList.remove('is-invalid');
                this.classList.add('is-valid');
            } else if (this.value.length > 0) {
                this.classList.remove('is-valid');
                this.classList.add('is-invalid');
            }
        });
    });

    // --- MÁSCARAS E VALIDAÇÕES DE CPF ---
    const cpfInputs = document.querySelectorAll('input[name="customer_cpf"], #profileCpf');
    cpfInputs.forEach(input => {
        input.addEventListener('input', function(e) {
            e.target.value = formatCPF(e.target.value);
        });

        input.addEventListener('blur', function() {
            const numOnly = this.value.replace(/\D/g, '');
            const errDiv = document.getElementById('error-cpf') || document.getElementById('profileCpfError');
            if (numOnly.length === 11) {
                this.classList.remove('is-invalid');
                this.classList.add('is-valid');
                if (errDiv) errDiv.style.display = 'none';
            } else if (numOnly.length > 0) {
                this.classList.remove('is-valid');
                this.classList.add('is-invalid');
                if (errDiv) errDiv.style.display = 'block';
            }
        });
    });

    // --- OBRIGAR MAIÚSCULAS NO NOME ---
    const nameInputs = document.querySelectorAll('input[name="customer_name"], #playerLoginName, #profileName');
    nameInputs.forEach(input => {
        input.addEventListener('input', function() {
            this.value = this.value.toUpperCase();
        });
    });

    // Enter no campo de login de atleta
    const loginPhoneInput = document.getElementById('playerLoginPhone');
    if (loginPhoneInput) {
        loginPhoneInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                loginPlayer();
            }
        });
    }
});

// --- 1. ABERTURA DO MODAL DE RESERVA E RECALCULO DE PREÇO POR QUADRA ---
function openBookingModal(time, date, courts, price, equipmentsData) {
    currentCourtsData = courts || [];
    currentEquipmentsData = equipmentsData || [];

    if (!currentCourtsData || currentCourtsData.length === 0) {
        alert("Ops! Todas as quadras para este horário já foram reservadas.");
        fetchAndSwapSlots(window.location.href, false);
        return;
    }

    // Atualiza visual (Data e Hora)
    document.getElementById('displayTime').innerText = time;
    document.getElementById('displayDate').innerText = date.split('-').reverse().join('/');
    document.getElementById('modalDate').value = date;
    document.getElementById('modalTime').value = time;

    // Popula o Select de Quadras com seus preços individuais
    const select = document.getElementById('modalCourtSelect');
    select.innerHTML = '';

    currentCourtsData.forEach((court, idx) => {
        const option = document.createElement('option');
        option.value = court.id;
        const courtPrice = court.price !== undefined ? parseFloat(court.price) : parseFloat(price);
        option.dataset.price = courtPrice;
        option.text = `${court.name} - R$ ${courtPrice.toFixed(2).replace('.', ',')}`;
        select.appendChild(option);
    });

    // Define preço base inicial baseado na quadra selecionada
    if (currentCourtsData.length > 0 && currentCourtsData[0].price !== undefined) {
        currentBasePrice = parseFloat(currentCourtsData[0].price);
    } else {
        currentBasePrice = parseFloat(price);
    }

    // Listener para troca de quadra -> atualiza preço base e equipamentos
    select.removeEventListener('change', onCourtSelectionChange);
    select.addEventListener('change', onCourtSelectionChange);

    // Preenche dados do atleta se já estiver identificado
    prefillBookingModalWithPlayerData();

    // Atualiza equipamentos e recalcula preços
    updateEquipmentsVisibility();
    calculatePrices();
    selectPayment('total');

    new bootstrap.Modal(document.getElementById('bookingModal')).show();
}

function onCourtSelectionChange() {
    const select = document.getElementById('modalCourtSelect');
    const selectedCourtId = parseInt(select.value);
    const selectedCourt = currentCourtsData.find(c => c.id === selectedCourtId);

    if (selectedCourt && selectedCourt.price !== undefined) {
        currentBasePrice = parseFloat(selectedCourt.price);
    }

    updateEquipmentsVisibility();
    calculatePrices();
}

function prefillBookingModalWithPlayerData() {
    const player = getSavedPlayer();
    const noticeEl = document.getElementById('bookingPlayerIdentifiedNotice');
    const noticeName = document.getElementById('bookingIdentifiedPlayerName');

    const nameInput = document.querySelector('input[name="customer_name"]');
    const phoneInput = document.querySelector('input[name="customer_phone"]');
    const cpfInput = document.querySelector('input[name="customer_cpf"]');
    const emailInput = document.querySelector('input[name="customer_email"]');

    if (player && (player.name || player.phone)) {
        if (noticeEl && noticeName) {
            noticeName.innerText = player.name || formatPhone(player.phone);
            noticeEl.style.display = 'flex';
        }

        if (nameInput && player.name) nameInput.value = player.name;
        if (phoneInput && player.phone) phoneInput.value = formatPhone(player.phone);
        if (cpfInput && player.cpf) cpfInput.value = formatCPF(player.cpf);
        if (emailInput && player.email) emailInput.value = player.email;
    } else {
        if (noticeEl) noticeEl.style.display = 'none';
    }
}

// --- 2. FILTRA E RENDERIZA EQUIPAMENTOS ---
function updateEquipmentsVisibility() {
    const select = document.getElementById('modalCourtSelect');
    if (!select) return;
    const selectedCourtId = parseInt(select.value);

    const selectedCourt = currentCourtsData.find(c => c.id === selectedCourtId);
    if (!selectedCourt) return;

    const filteredEquipments = currentEquipmentsData.filter(eq => {
        if (!eq.modality_ids || eq.modality_ids.length === 0) return true;
        if (!selectedCourt.modality_ids || selectedCourt.modality_ids.length === 0) return true;
        return eq.modality_ids.some(id => selectedCourt.modality_ids.includes(id));
    });

    renderEquipments(filteredEquipments);
    calculatePrices();
}

function renderEquipments(equipmentsList) {
    const container = document.getElementById('modalEquipmentList');
    if (!container) return;
    container.innerHTML = '';

    if (!equipmentsList || equipmentsList.length === 0) {
        container.innerHTML = '<div class="text-muted small ms-1 fst-italic">Nenhum equipamento adicional disponível.</div>';
        return;
    }

    equipmentsList.forEach(eq => {
        let iconHtml = '<i class="bi bi-box-seam"></i>';
        if (eq.is_ball) iconHtml = '<i class="bi bi-circle-fill text-warning"></i>';
        else if (eq.is_racket) iconHtml = '<i class="bi bi-gem text-danger"></i>';

        let html = '';
        if (eq.stock > 0) {
            html = `
            <div class="col-12 col-md-6">
                <label class="card h-100 border-0 bg-light p-3 cursor-pointer position-relative shadow-sm user-select-none" for="eq_${eq.id}" style="cursor: pointer;">
                    <div class="d-flex justify-content-between align-items-center">
                        <div class="d-flex align-items-center">
                            <div class="rounded-circle bg-white p-2 me-3 d-flex align-items-center justify-content-center shadow-sm" style="width:40px; height:40px;">
                                ${iconHtml}
                            </div>
                            <div class="lh-1">
                                <span class="fw-bold d-block text-dark mb-1">${eq.name}</span>
                                <small class="text-muted fw-bold" style="font-size: 0.85rem;">+ R$ ${eq.price.toFixed(2)}</small>
                                <span class="badge bg-white text-secondary border ms-1" style="font-size: 0.65rem;">Restam: ${eq.stock}</span>
                            </div>
                        </div>
                        <div class="form-check form-switch m-0">
                            <input type="checkbox"
                                   name="equipment_ids"
                                   value="${eq.id}"
                                   id="eq_${eq.id}"
                                   class="form-check-input fs-4 equipment-checkbox"
                                   data-price="${eq.price}"
                                   onchange="calculatePrices()">
                        </div>
                    </div>
                </label>
            </div>`;
        } else {
            html = `
            <div class="col-12 col-md-6">
                <div class="card h-100 border-0 bg-light p-3 opacity-50">
                    <div class="d-flex justify-content-between align-items-center">
                        <div class="d-flex align-items-center">
                            <div class="rounded-circle bg-secondary bg-opacity-10 p-2 me-3 d-flex align-items-center justify-content-center" style="width:40px; height:40px;">
                                <i class="bi bi-slash-circle"></i>
                            </div>
                            <div class="lh-1">
                                <span class="fw-bold d-block text-muted text-decoration-line-through mb-1">${eq.name}</span>
                                <small class="text-danger fw-bold" style="font-size: 0.75rem;">Esgotado</small>
                            </div>
                        </div>
                        <div class="form-check form-switch m-0">
                            <input type="checkbox" class="form-check-input fs-4" disabled>
                        </div>
                    </div>
                </div>
            </div>`;
        }
        container.insertAdjacentHTML('beforeend', html);
    });
}

// --- 3. CALCULA O PREÇO TOTAL ---
function calculatePrices() {
    let extra = 0;
    const checkboxes = document.querySelectorAll('.equipment-checkbox:checked');
    checkboxes.forEach(cb => {
        extra += parseFloat(cb.dataset.price || 0);
    });

    currentTotal = currentBasePrice + extra;
    let sinal = currentTotal / 2;

    const elTotal = document.getElementById('displayTotalPrice');
    const elPartial = document.getElementById('displayPartialPrice');

    if (elTotal) elTotal.innerText = currentTotal.toLocaleString('pt-BR', {style: 'currency', currency: 'BRL'});
    if (elPartial) elPartial.innerText = sinal.toLocaleString('pt-BR', {style: 'currency', currency: 'BRL'});
}

// --- 4. SELEÇÃO DE PAGAMENTO ---
function selectPayment(type) {
    const inputHidden = document.getElementById('inputPaymentType');
    if (inputHidden) inputHidden.value = type;

    const btnTotal = document.getElementById('btnTotal');
    const btnPartial = document.getElementById('btnPartial');
    const btnVenue = document.getElementById('btnVenue');

    const allButtons = [
        { id: 'total', el: btnTotal },
        { id: 'partial', el: btnPartial },
        { id: 'venue', el: btnVenue }
    ];

    const activeClass = ['btn-warning', 'shadow', 'border-warning', 'active'];
    const inactiveClass = ['btn-outline-light', 'text-dark', 'bg-white', 'shadow-sm', 'border-0'];

    allButtons.forEach(btnObj => {
        if (!btnObj.el) return;
        if (btnObj.id === type) {
            btnObj.el.classList.remove(...inactiveClass);
            btnObj.el.classList.add(...activeClass);
            toggleIcon(btnObj.el, true);
        } else {
            btnObj.el.classList.remove(...activeClass);
            btnObj.el.classList.add(...inactiveClass);
            toggleIcon(btnObj.el, false);
        }
    });
}

function toggleIcon(btn, isActive) {
    const icon = btn.querySelector('.check-icon');
    if (!icon) return;

    if (isActive) {
        icon.classList.replace('bi-circle', 'bi-check-circle-fill');
        icon.classList.remove('text-warning');
        icon.classList.add('text-dark');
    } else {
        icon.classList.replace('bi-check-circle-fill', 'bi-circle');
        icon.classList.add('text-warning');
        icon.classList.remove('text-dark');
    }
}

// --- 5. "MEUS AGENDAMENTOS" & IDENTIFICAÇÃO DO ATLETA ---

function openMyBookingsModal(mode = 'bookings') {
    window.location.href = `/app/${ARENA_SLUG}/meus-agendamentos/`;
}

function switchAthleteTab(tab) {
    const tabBookingsBtn = document.getElementById('tabBookingsBtn');
    const tabProfileBtn = document.getElementById('tabProfileBtn');
    const tabBookingsContent = document.getElementById('tabBookingsContent');
    const tabProfileContent = document.getElementById('tabProfileContent');

    if (tab === 'profile') {
        if (tabProfileBtn) tabProfileBtn.classList.add('active');
        if (tabBookingsBtn) tabBookingsBtn.classList.remove('active');
        if (tabProfileContent) tabProfileContent.style.display = 'block';
        if (tabBookingsContent) tabBookingsContent.style.display = 'none';

        // Popula formulário de perfil com dados salvos
        const player = getSavedPlayer() || {};
        const pName = document.getElementById('profileName');
        const pPhone = document.getElementById('profilePhone');
        const pCpf = document.getElementById('profileCpf');
        const pEmail = document.getElementById('profileEmail');

        if (pName) pName.value = player.name || '';
        if (pPhone) pPhone.value = formatPhone(player.phone || '');
        if (pCpf) pCpf.value = formatCPF(player.cpf || '');
        if (pEmail) pEmail.value = player.email || '';

        const feedback = document.getElementById('profileFeedback');
        if (feedback) feedback.style.display = 'none';

    } else {
        if (tabBookingsBtn) tabBookingsBtn.classList.add('active');
        if (tabProfileBtn) tabProfileBtn.classList.remove('active');
        if (tabBookingsContent) tabBookingsContent.style.display = 'block';
        if (tabProfileContent) tabProfileContent.style.display = 'none';

        fetchBookings();
    }
}

function loginPlayer() {
    const nameInput = document.getElementById('playerLoginName');
    const phoneInput = document.getElementById('playerLoginPhone');
    const btn = document.getElementById('btnLoginPlayer');
    const genErr = document.getElementById('loginGeneralError');
    const nameErr = document.getElementById('loginNameError');
    const phoneErr = document.getElementById('loginPhoneError');

    const name = (nameInput?.value || '').trim();
    const phone = (phoneInput?.value || '').trim();
    const phoneDigits = phone.replace(/\D/g, '');

    let hasError = false;
    if (name.length < 2) {
        if (nameErr) nameErr.style.display = 'block';
        hasError = true;
    } else {
        if (nameErr) nameErr.style.display = 'none';
    }

    if (phoneDigits.length < 10) {
        if (phoneErr) phoneErr.style.display = 'block';
        hasError = true;
    } else {
        if (phoneErr) phoneErr.style.display = 'none';
    }

    if (hasError) return;

    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span> Entrando...';
    }
    if (genErr) genErr.style.display = 'none';

    fetch(BOOKINGS_URL, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken()
        },
        body: JSON.stringify({
            name: name,
            phone: phoneDigits
        })
    })
    .then(res => res.json())
    .then(data => {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<span>Acessar Meus Agendamentos</span> <i class="bi bi-arrow-right"></i>';
        }

        if (data.success) {
            // Salva dados no storage local
            savePlayerLocally({
                name: data.customer?.name || name,
                phone: data.customer?.phone || phoneDigits,
                cpf: data.customer?.cpf || '',
                email: data.customer?.email || ''
            });

            // Transiciona para o Painel do Atleta
            const loginView = document.getElementById('playerLoginView');
            const dashboardView = document.getElementById('playerDashboardView');
            if (loginView) loginView.style.display = 'none';
            if (dashboardView) dashboardView.style.display = 'block';

            const dashName = document.getElementById('dashboardPlayerName');
            const dashPhone = document.getElementById('dashboardPlayerPhone');
            if (dashName) dashName.innerText = data.customer?.name || name;
            if (dashPhone) dashPhone.innerText = formatPhone(data.customer?.phone || phoneDigits);

            switchAthleteTab('bookings');
            renderBookingsList(data.bookings);

            // Preenche modal de reserva se estiver aberto
            prefillBookingModalWithPlayerData();
        } else {
            if (genErr) {
                genErr.innerText = data.error || 'Erro ao identificar atleta. Verifique os dados.';
                genErr.style.display = 'block';
            }
        }
    })
    .catch(err => {
        console.error('Erro no login:', err);
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<span>Acessar Meus Agendamentos</span> <i class="bi bi-arrow-right"></i>';
        }
        if (genErr) {
            genErr.innerText = 'Erro de comunicação com o servidor. Tente novamente.';
            genErr.style.display = 'block';
        }
    });
}

function savePlayerProfile() {
    const nameInput = document.getElementById('profileName');
    const phoneInput = document.getElementById('profilePhone');
    const cpfInput = document.getElementById('profileCpf');
    const emailInput = document.getElementById('profileEmail');
    const btn = document.getElementById('btnSaveProfile');
    const feedback = document.getElementById('profileFeedback');
    const cpfErr = document.getElementById('profileCpfError');

    const name = (nameInput?.value || '').trim();
    const phoneDigits = (phoneInput?.value || '').replace(/\D/g, '');
    const cpfDigits = (cpfInput?.value || '').replace(/\D/g, '');
    const email = (emailInput?.value || '').trim();

    if (name.length < 2) {
        alert('Por favor, informe seu nome completo.');
        return;
    }

    if (phoneDigits.length < 10) {
        alert('Por favor, informe um telefone válido com DDD.');
        return;
    }

    if (cpfDigits && cpfDigits.length !== 11) {
        if (cpfErr) cpfErr.style.display = 'block';
        return;
    } else {
        if (cpfErr) cpfErr.style.display = 'none';
    }

    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span> Salvando...';
    }

    fetch(SAVE_PROFILE_URL, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken()
        },
        body: JSON.stringify({
            name: name,
            phone: phoneDigits,
            cpf: cpfDigits,
            email: email
        })
    })
    .then(res => res.json())
    .then(data => {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<i class="bi bi-check-circle-fill"></i> <span>Salvar Meus Dados</span>';
        }

        if (data.success) {
            savePlayerLocally({
                name: data.customer?.name || name,
                phone: data.customer?.phone || phoneDigits,
                cpf: data.customer?.cpf || cpfDigits,
                email: data.customer?.email || email
            });

            const dashName = document.getElementById('dashboardPlayerName');
            const dashPhone = document.getElementById('dashboardPlayerPhone');
            if (dashName) dashName.innerText = data.customer?.name || name;
            if (dashPhone) dashPhone.innerText = formatPhone(data.customer?.phone || phoneDigits);

            if (feedback) {
                feedback.className = 'alert alert-success py-2 small mb-3';
                feedback.innerHTML = '<i class="bi bi-check-circle-fill me-1"></i> Dados salvos com sucesso! Suas próximas reservas serão preenchidas automaticamente.';
                feedback.style.display = 'block';
            }

            prefillBookingModalWithPlayerData();
        } else {
            if (feedback) {
                feedback.className = 'alert alert-danger py-2 small mb-3';
                feedback.innerText = data.error || 'Erro ao salvar dados.';
                feedback.style.display = 'block';
            }
        }
    })
    .catch(err => {
        console.error('Erro ao salvar perfil:', err);
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<i class="bi bi-check-circle-fill"></i> <span>Salvar Meus Dados</span>';
        }
        if (feedback) {
            feedback.className = 'alert alert-danger py-2 small mb-3';
            feedback.innerText = 'Erro ao conectar ao servidor.';
            feedback.style.display = 'block';
        }
    });
}

function logoutPlayer() {
    clearSavedPlayer();

    // Reset visual dos avisos de atleta
    const noticeEl = document.getElementById('bookingPlayerIdentifiedNotice');
    if (noticeEl) noticeEl.style.display = 'none';

    // Limpa campos do modal de reserva
    const nameInput = document.querySelector('input[name="customer_name"]');
    const phoneInput = document.querySelector('input[name="customer_phone"]');
    const cpfInput = document.querySelector('input[name="customer_cpf"]');
    const emailInput = document.querySelector('input[name="customer_email"]');
    if (nameInput) nameInput.value = '';
    if (phoneInput) phoneInput.value = '';
    if (cpfInput) cpfInput.value = '';
    if (emailInput) emailInput.value = '';

    // Se o modal de agendamentos estiver aberto, alterna para a tela de identificação
    const loginView = document.getElementById('playerLoginView');
    const dashboardView = document.getElementById('playerDashboardView');
    if (loginView) loginView.style.display = 'block';
    if (dashboardView) dashboardView.style.display = 'none';

    const loginNameInput = document.getElementById('playerLoginName');
    const loginPhoneInput = document.getElementById('playerLoginPhone');
    if (loginNameInput) loginNameInput.value = '';
    if (loginPhoneInput) loginPhoneInput.value = '';
}

function refreshBookings() {
    fetchBookings();
}

function fetchBookings() {
    const player = getSavedPlayer();
    const listDiv = document.getElementById('bookingsList');
    if (!listDiv) return;

    if (!player || !player.phone) {
        listDiv.innerHTML = '<div class="alert alert-warning py-2 small text-center">Nenhum atleta identificado.</div>';
        return;
    }

    listDiv.innerHTML = '<div class="text-center py-4"><div class="spinner-border text-warning" role="status"></div><div class="small text-muted mt-2">Buscando seus jogos...</div></div>';

    fetch(`${BOOKINGS_URL}?phone=${encodeURIComponent(player.phone)}&name=${encodeURIComponent(player.name || '')}`)
        .then(response => {
            if (!response.ok) throw new Error('Erro na rede');
            return response.json();
        })
        .then(data => {
            if (data.customer) {
                savePlayerLocally(data.customer);
            }
            renderBookingsList(data.bookings || []);
        })
        .catch(error => {
            console.error('Erro ao buscar reservas:', error);
            listDiv.innerHTML = '<div class="text-danger text-center small py-3">Erro ao buscar reservas. Tente novamente.</div>';
        });
}

function renderBookingsList(bookings) {
    const listDiv = document.getElementById('bookingsList');
    if (!listDiv) return;
    listDiv.innerHTML = '';

    if (!bookings || bookings.length === 0) {
        listDiv.innerHTML = `
            <div class="text-center py-4 bg-light rounded-4">
                <i class="bi bi-calendar-x fs-1 text-muted opacity-50"></i>
                <p class="mt-2 text-muted fw-bold small mb-1">Nenhum agendamento encontrado.</p>
                <small class="text-muted">Seus horários reservados aparecerão aqui.</small>
            </div>`;
        return;
    }

    bookings.forEach(b => {
        // Badges de pagamento
        let paymentBadgeHtml = '';
        if (b.status === 'CONFIRMED') {
            if (b.payment_status === 'PARTIAL') {
                paymentBadgeHtml = '<span class="badge bg-info bg-opacity-10 text-primary border border-info rounded-pill px-2 py-1 small">Sinal Pago (50%)</span>';
            } else if (b.payment_status === 'PAID') {
                paymentBadgeHtml = '<span class="badge bg-success bg-opacity-10 text-success border border-success rounded-pill px-2 py-1 small">100% Pago</span>';
            } else {
                paymentBadgeHtml = '<span class="badge bg-secondary bg-opacity-10 text-secondary border rounded-pill px-2 py-1 small">Pagar na Arena</span>';
            }
        } else if (b.status === 'PENDING') {
            paymentBadgeHtml = '<span class="badge bg-warning bg-opacity-25 text-dark border border-warning rounded-pill px-2 py-1 small">Aguardando Pagamento</span>';
        } else {
            paymentBadgeHtml = `<span class="badge bg-secondary rounded-pill px-2 py-1 small">${b.status_text}</span>`;
        }

        // Botões de ação
        let actionBtnHtml = '';
        if (b.checkout_url) {
            actionBtnHtml = `
                <a href="${b.checkout_url}" class="btn btn-warning w-100 btn-sm rounded-pill fw-bold shadow-sm d-flex align-items-center justify-content-center gap-1 mt-2">
                    <i class="bi bi-qr-code"></i> Pagar via PIX (15 min)
                </a>`;
        } else if (b.success_url) {
            actionBtnHtml = `
                <a href="${b.success_url}" class="btn btn-outline-success w-100 btn-sm rounded-pill fw-bold d-flex align-items-center justify-content-center gap-1 mt-2">
                    <i class="bi bi-ticket-perforated"></i> Ver Comprovante
                </a>`;
        } else if (b.is_expired) {
            actionBtnHtml = `
                <div class="text-danger small fst-italic text-center mt-2">
                    <i class="bi bi-clock-history me-1"></i> Tempo de pagamento expirado (horário liberado)
                </div>`;
        }

        const card = `
            <div class="card border rounded-4 shadow-sm bg-white overflow-hidden">
                <div class="card-body p-3">
                    <div class="d-flex justify-content-between align-items-start mb-2">
                        <div>
                            <div class="fw-bold text-dark fs-6">
                                <i class="bi bi-calendar2-event text-warning me-1"></i> ${b.date}
                            </div>
                            <div class="small text-muted fw-bold ms-4">${b.time}</div>
                        </div>
                        <div class="text-end">
                            <span class="badge bg-${b.color} rounded-pill px-2 py-1">
                                ${b.status_text}
                            </span>
                        </div>
                    </div>

                    <div class="bg-light rounded-3 p-2 small mb-2 border">
                        <div class="d-flex justify-content-between text-muted mb-1">
                            <span>Quadra:</span>
                            <strong class="text-dark">${b.court}</strong>
                        </div>
                        <div class="d-flex justify-content-between text-muted mb-1">
                            <span>Valor Total:</span>
                            <strong class="text-dark">R$ ${b.total_price.toFixed(2)}</strong>
                        </div>
                        <div class="d-flex justify-content-between text-muted mb-1">
                            <span>Valor Pago:</span>
                            <strong class="text-success">R$ ${b.amount_paid.toFixed(2)}</strong>
                        </div>
                        ${b.remaining_balance > 0 ? `
                        <div class="d-flex justify-content-between text-muted mb-1">
                            <span>Saldo Restante na Arena:</span>
                            <strong class="text-danger">R$ ${b.remaining_balance.toFixed(2)}</strong>
                        </div>` : ''}
                        <div class="d-flex justify-content-between align-items-center pt-1 border-top mt-1">
                            <span class="text-muted"><i class="bi bi-wallet2 me-1"></i> ${b.payment_method}</span>
                            ${paymentBadgeHtml}
                        </div>
                    </div>

                    ${actionBtnHtml}
                </div>
            </div>`;

        listDiv.insertAdjacentHTML('beforeend', card);
    });
}

function getCSRFToken() {
    const input = document.querySelector('[name=csrfmiddlewaretoken]');
    if (input) return input.value;

    const cookies = document.cookie.split(';');
    for (let c of cookies) {
        c = c.trim();
        if (c.startsWith('csrftoken=')) {
            return decodeURIComponent(c.substring('csrftoken='.length));
        }
    }
    return '';
}