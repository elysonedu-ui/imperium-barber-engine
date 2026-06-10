document.addEventListener("DOMContentLoaded", async () => {
    const navLinks = document.querySelectorAll(".nav-link");
    const sections = document.querySelectorAll("section");

    if (sections.length > 0) {
        window.addEventListener("scroll", () => {
            let current = "";
            sections.forEach(section => {
                const sectionTop = section.offsetTop;
                if (pageYOffset >= (sectionTop - 150)) {
                    current = section.getAttribute("id");
                }
            });

            navLinks.forEach(link => {
                link.classList.remove("active");
                if (link.getAttribute("href").includes(current)) {
                    link.classList.add("active");
                }
            });
        });
    }

    // === Carregamento Dinâmico (SaaS) ===
    const barberContainer = document.getElementById("barber-container");
    const serviceSelect = document.getElementById("service-select");

    async function loadDynamicConfig() {
        try {
            if (barberContainer) {
                const res = await fetch("/api/barbeiros");
                const barbers = await res.json();
                barberContainer.innerHTML = "";
                barbers.forEach((barber, index) => {
                    const checked = index === 0 ? "checked" : "";
                    const imgName = barber.username === "john" ? "barber_john.png" : "barber_marcus.png";
                    barberContainer.innerHTML += `
                        <label class="barber-option">
                            <input type="radio" name="barber" value="${barber.display_name}" ${checked}>
                            <div class="barber-option-content">
                                <img src="/static/${imgName}" alt="${barber.display_name}" style="width: 32px; height: 32px; border-radius: 50%; object-fit: cover; border: 1px solid var(--gold);">
                                <span class="bo-name">${barber.display_name}</span>
                            </div>
                        </label>
                    `;
                });
                
                // Re-atachar os eventos nos radios
                document.querySelectorAll('input[name="barber"]').forEach(radio => {
                    radio.addEventListener('change', generateTimeSlots);
                });
            }

            if (serviceSelect) {
                const res = await fetch("/api/servicos");
                const services = await res.json();
                serviceSelect.innerHTML = "";
                services.forEach(s => {
                    serviceSelect.innerHTML += `
                        <option value="${s.nome}" data-price="${s.preco.toFixed(2)}">${s.nome} — R$ ${s.preco.toFixed(2).replace('.', ',')}</option>
                    `;
                });
            }
        } catch (e) {
            console.error("Erro ao carregar configurações dinâmicas.", e);
        }
    }
    
    await loadDynamicConfig();


    const datePickerGrid = document.getElementById("date-picker-grid");
    let selectedDate = "";

    const daysOfWeek = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"];
    const months = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"];

    function generateCalendar() {
        if (!datePickerGrid) return;
        const today = new Date();
        for (let i = 0; i < 7; i++) {
            const nextDate = new Date(today);
            nextDate.setDate(today.getDate() + i);

            const dayName = daysOfWeek[nextDate.getDay()];
            const dayNum = String(nextDate.getDate()).padStart(2, '0');
            const monthName = months[nextDate.getMonth()];
            
            const fullDateString = `${dayNum} de ${monthName}`;

            const dateBtn = document.createElement("div");
            dateBtn.classList.add("date-btn");
            if (i === 0) {
                dateBtn.classList.add("active");
                selectedDate = fullDateString;
            }

            dateBtn.innerHTML = `
                <span class="date-btn-day">${dayName}</span>
                <span class="date-btn-num">${dayNum}</span>
            `;

            dateBtn.addEventListener("click", () => {
                document.querySelectorAll(".date-btn").forEach(btn => btn.classList.remove("active"));
                dateBtn.classList.add("active");
                selectedDate = fullDateString;
                selectedTime = "";
                generateTimeSlots();
            });

            datePickerGrid.appendChild(dateBtn);
        }
    }
    generateCalendar();

    const timeSlotsGrid = document.getElementById("time-slots-grid");
    let standardTimes = [];
    if (window.SITE_CONFIG) {
        let currentH = parseInt(window.SITE_CONFIG.start_time.split(":")[0]);
        let currentM = parseInt(window.SITE_CONFIG.start_time.split(":")[1]);
        const endH = parseInt(window.SITE_CONFIG.end_time.split(":")[0]);
        const interval = window.SITE_CONFIG.interval_minutes;
        
        while (currentH < endH || (currentH === endH && currentM === 0)) {
            const hStr = currentH.toString().padStart(2, '0');
            const mStr = currentM.toString().padStart(2, '0');
            standardTimes.push(`${hStr}:${mStr}`);
            
            currentM += interval;
            if (currentM >= 60) {
                currentH += Math.floor(currentM / 60);
                currentM = currentM % 60;
            }
        }
    } else {
        standardTimes = ["09:00", "10:00", "11:00", "13:00", "14:00", "15:00", "16:00", "17:00", "18:00"];
    }
    let selectedTime = "";

    async function generateTimeSlots() {
        if (!timeSlotsGrid) return;
        timeSlotsGrid.innerHTML = "<div class='no-data' style='grid-column: 1/-1;'>Carregando horários...</div>";
        
        const selectedBarberRadio = document.querySelector('input[name="barber"]:checked');
        if (!selectedBarberRadio) return;
        const selectedBarberVal = selectedBarberRadio.value;

        try {
            const response = await fetch(`/api/busy-slots?barber=${encodeURIComponent(selectedBarberVal)}&date=${encodeURIComponent(selectedDate)}`);
            const busySlots = response.ok ? await response.json() : [];
            timeSlotsGrid.innerHTML = "";
            
            const today = new Date();
            const todayDayNum = String(today.getDate()).padStart(2, '0');
            const todayMonthName = months[today.getMonth()];
            const todayDateString = `${todayDayNum} de ${todayMonthName}`;
            const isToday = (selectedDate === todayDateString);
            
            standardTimes.forEach(time => {
                const timeBtn = document.createElement("div");
                timeBtn.classList.add("time-btn");
                timeBtn.textContent = time;

                let isPastTime = false;
                if (isToday) {
                    const [slotHour, slotMin] = time.split(":").map(Number);
                    const currentHour = today.getHours();
                    const currentMin = today.getMinutes();
                    if (slotHour < currentHour || (slotHour === currentHour && slotMin <= currentMin)) {
                        isPastTime = true;
                    }
                }

                const isBusy = busySlots.includes(time);
                if (isBusy) {
                    timeBtn.classList.add("busy");
                    timeBtn.title = "Horário já reservado por outro cliente";
                } else if (isPastTime) {
                    timeBtn.classList.add("busy");
                    timeBtn.style.opacity = "0.4";
                    timeBtn.style.cursor = "not-allowed";
                    timeBtn.title = "Horário já passou";
                } else {
                    timeBtn.addEventListener("click", () => {
                        document.querySelectorAll(".time-btn").forEach(btn => btn.classList.remove("active"));
                        timeBtn.classList.add("active");
                        selectedTime = time;
                    });
                }
                timeSlotsGrid.appendChild(timeBtn);
            });
        } catch (error) {
            console.error("Erro ao carregar agenda:", error);
            timeSlotsGrid.innerHTML = "<div class='no-data' style='grid-column: 1/-1; color: #ff3333;'>Erro ao carregar a agenda.</div>";
        }
    }
    generateTimeSlots();

    const barberRadios = document.querySelectorAll('input[name="barber"]');
    barberRadios.forEach(radio => {
        radio.addEventListener("change", () => {
            selectedTime = "";
            generateTimeSlots();
        });
    });

    const bookingForm = document.getElementById("booking-form");
    const receiptModal = document.getElementById("receipt-modal");
    
    const rClientName = document.getElementById("r-client-name");
    const rClientPhone = document.getElementById("r-client-phone");
    const rBarber = document.getElementById("r-barber");
    const rService = document.getElementById("r-service");
    const rDate = document.getElementById("r-date");
    const rTime = document.getElementById("r-time");
    const rPrice = document.getElementById("r-price");

    if (bookingForm) {
        bookingForm.addEventListener("submit", async (e) => {
            e.preventDefault();

            if (!selectedDate || !selectedTime) {
                alert("Selecione data e horário.");
                return;
            }

            const clientNameVal = document.getElementById("client-name").value.trim();
            const clientPhoneVal = document.getElementById("client-phone").value.trim();
            const clientEmailInput = document.getElementById("client-email");
            const clientEmailVal = clientEmailInput ? clientEmailInput.value.trim() : "";
            const selectedBarberVal = document.querySelector('input[name="barber"]:checked').value;
            
            const serviceSelect = document.getElementById("service-select");
            const selectedServiceVal = serviceSelect.value;
            const selectedOption = serviceSelect.options[serviceSelect.selectedIndex];
            const priceVal = parseFloat(selectedOption.getAttribute("data-price"));

            const payload = {
                barber: selectedBarberVal,
                service: selectedServiceVal,
                date: selectedDate,
                time: selectedTime,
                price: priceVal,
                client_name: clientNameVal,
                client_phone: clientPhoneVal,
                client_email: clientEmailVal
            };

            try {
                const response = await fetch("/api/book", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload)
                });

                if (!response.ok) {
                    const data = await response.json();
                    throw new Error(data.error || "Erro no servidor.");
                }

                rClientName.textContent = clientNameVal.toUpperCase();
                rClientPhone.textContent = clientPhoneVal;
                rBarber.textContent = selectedBarberVal.toUpperCase();
                rService.textContent = selectedServiceVal;
                rDate.textContent = selectedDate.toUpperCase();
                rTime.textContent = `${selectedTime} HORAS`;
                rPrice.textContent = `R$ ${priceVal.toFixed(2).replace('.', ',')}`;

                receiptModal.classList.add("open");
            } catch (error) {
                alert("Erro ao realizar agendamento: " + error.message);
            }
        });
    }

    const closeModalBtn = document.getElementById("close-modal-btn");
    if (closeModalBtn) {
        closeModalBtn.addEventListener("click", () => {
            receiptModal.classList.remove("open");
            bookingForm.reset();
            selectedTime = "";
            generateTimeSlots();
            window.location.reload();
        });
    }
});

    // Intersection Observer para animacoes de Scroll Reveal
    const revealElements = document.querySelectorAll('.hidden-reveal');
    const revealOptions = {
        threshold: 0.15,
        rootMargin: "0px 0px -50px 0px"
    };

    const revealObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('reveal-active');
                observer.unobserve(entry.target);
            }
        });
    }, revealOptions);

    revealElements.forEach(el => {
        revealObserver.observe(el);
    });
