document.addEventListener('DOMContentLoaded', function () {
    const menuButtons = document.querySelectorAll('.span-menu-center');
    const contentBlocks = document.querySelectorAll('.content-block');
    const bannerButton = document.querySelector('.banner-free-robux');
    const codeInputs = document.querySelectorAll('.code-input');
    const activateButtons = document.querySelectorAll('.activate-btn');
    const hamburgerMenu = document.getElementById('hamburgerMenu');
    const mobileMenu = document.getElementById('mobileMenu');
    const closeMenu = document.getElementById('closeMenu');
    const languageToggle = document.getElementById('languageToggle');
    const mobileLanguageToggle = document.getElementById('mobileLanguageToggle');
    const slider = document.getElementById('slider');
    const result = document.getElementById('result');

    function activateContent(targetId) {
        contentBlocks.forEach(block => {
            block.classList.remove('active');
            if (block.id === targetId) {
                block.classList.add('active');
                localStorage.setItem('activeTab', targetId);
            }
        });
        menuButtons.forEach(btn => {
            btn.classList.remove('active');
            if (btn.getAttribute('data-target') === targetId) {
                btn.classList.add('active');
            }
        });
        if (mobileMenu && mobileMenu.classList.contains('active')) {
            mobileMenu.classList.remove('active');
        }
    }

    menuButtons.forEach(button => {
        button.addEventListener('click', function (e) {
            e.preventDefault();
            const targetId = this.getAttribute('data-target');
            activateContent(targetId);
        });
    });

    if (bannerButton) {
        bannerButton.addEventListener('click', function (e) {
            e.preventDefault();
            const targetId = this.getAttribute('data-target');
            activateContent(targetId);
        });
    }

    const savedTab = localStorage.getItem('activeTab');
    if (savedTab) {
        activateContent(savedTab);
    }

    function updateSlider() {
        const slider = document.getElementById('slider');
        const result = document.getElementById('result');
        const priceInput = document.getElementById('price');
        const robuxSteps = parseInt(slider.value);
        const rValue = 20 + (robuxSteps * 20);
        const language = localStorage.getItem('language') || 'ru';
        let currencyValue, currencySymbol;
        if (language === 'en') {
            currencyValue = (window.currencyRates.usd * rValue).toFixed(2);
        } else {
            currencyValue = (window.currencyRates.rub * rValue).toFixed(2);
        }
        result.innerHTML = `${currencyValue} ${currencySymbol} <span style="color: grey;">=</span> ${rValue.toFixed(0)} R$`;
        priceInput.value = currencyValue; // Передаём цену в форму
        const progress = (slider.value / slider.max) * 100;
        slider.style.setProperty('--slider-progress', `${progress}%`);
    }

    if (slider && result) {
        slider.oninput = updateSlider;
        updateSlider();
    }

    codeInputs.forEach(input => {
        input.addEventListener('input', function () {
            const form = this.closest('form');
            const activateBtn = form.querySelector('.activate-btn');
            if (form.action.includes('buy/step2') || this.value.length >= 3) {
                activateBtn.classList.add('enabled');
                activateBtn.disabled = false;
            } else {
                activateBtn.classList.remove('enabled');
                activateBtn.disabled = true;
            }
        });
    });

    activateButtons.forEach(btn => {
        if (btn.closest('form[action="/activate_promo/"]')) {
            btn.addEventListener('click', function (e) {
                e.preventDefault();
                const form = this.closest('form');
                const formData = new FormData(form);
                fetch('/activate_promo/', {
                    method: 'POST',
                    body: formData,
                    headers: {
                        'X-CSRFToken': form.querySelector('[name=csrfmiddlewaretoken]').value
                    }
                })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            alert(data.success);
                        } else {
                            alert(data.error);
                        }
                    })
                    .catch(error => {
                        alert('Ошибка при активации промокода');
                    });
            });
        }
    });

    const faqItems = document.querySelectorAll('.faq-item');
    faqItems.forEach(item => {
        item.addEventListener('click', () => {
            const isActive = item.classList.contains('active');
            faqItems.forEach(i => {
                i.classList.remove('active');
                i.querySelector('p').style.maxHeight = '0';
                i.querySelector('p').style.padding = '0 20px';
            });
            if (!isActive) {
                item.classList.add('active');
                const answer = item.querySelector('p');
                answer.style.maxHeight = answer.scrollHeight + 'px';
                answer.style.padding = '15px 20px';
            }
        });
    });

    function updateLanguage(language) {
        document.querySelectorAll('.lang').forEach(element => {
            element.textContent = element.getAttribute(`data-${language}`);
        });
        document.documentElement.lang = language;
        localStorage.setItem('language', language);
        updateSlider();
    }

    if (localStorage.getItem('language') === 'en') {
        languageToggle.checked = true;
        mobileLanguageToggle.checked = true;
        updateLanguage('en');
    }

    [languageToggle, mobileLanguageToggle].forEach(toggle => {
        toggle.addEventListener('change', () => {
            const language = toggle.checked ? 'en' : 'ru';
            languageToggle.checked = toggle.checked;
            mobileLanguageToggle.checked = toggle.checked;
            updateLanguage(language);
        });
    });

    if (hamburgerMenu && mobileMenu && closeMenu) {
        hamburgerMenu.addEventListener('click', () => {
            mobileMenu.classList.add('active');
        });

        closeMenu.addEventListener('click', () => {
            mobileMenu.classList.remove('active');
        });
    }

    const placeOptions = document.querySelectorAll('.place-option');
    placeOptions.forEach(option => {
        option.addEventListener('click', function () {
            placeOptions.forEach(opt => opt.classList.remove('active'));
            this.classList.add('active');
            document.getElementById('selected-place-id').value = this.dataset.placeId;
            document.getElementById('selected-place-name').value = this.dataset.placeName;
        });
    });
});

function reset() {
    const slider = document.getElementById('slider');
    const result = document.getElementById('result');
    if (slider && result) {
        slider.value = 0;
        const language = localStorage.getItem('language') || 'ru';
        let currencyValue, currencySymbol;
        if (language === 'en') {
            currencyValue = (20 * window.currencyRates.usd).toFixed(2);
        } else {
            currencyValue = (20 * window.currencyRates.rub).toFixed(2);
        }
        result.innerHTML = `${currencyValue.toFixed(2)} ${currencySymbol} <span style="color: grey;">=</span> 20 R$`;
        slider.style.setProperty('--slider-progress', '0%');
    }
}

