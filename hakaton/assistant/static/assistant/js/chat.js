/**
 * UI-каркас чата: ввод, подсказки, блокировка отправки.
 * Логика ассистента и API подключаются отдельно.
 */
(function () {
    const form = document.getElementById("chat-form");
    const input = document.getElementById("chat-input");
    const submit = document.getElementById("chat-submit");
    const suggestions = document.querySelectorAll("[data-suggestion]");

    if (!form || !input || !submit) {
        return;
    }

    function syncSubmitState() {
        submit.disabled = !input.value.trim();
    }

    function resizeInput() {
        input.style.height = "auto";
        input.style.height = Math.min(input.scrollHeight, 160) + "px";
    }

    input.addEventListener("input", function () {
        syncSubmitState();
        resizeInput();
    });

    suggestions.forEach(function (btn) {
        btn.addEventListener("click", function () {
            input.value = btn.textContent.trim();
            syncSubmitState();
            resizeInput();
            input.focus();
        });
    });

    form.addEventListener("submit", function (event) {
        event.preventDefault();
    });

    syncSubmitState();
})();
