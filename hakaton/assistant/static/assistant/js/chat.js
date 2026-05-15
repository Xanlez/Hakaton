/**
 * Чат: POST на URL из data-chat-api (совпадает с логикой python chat.py / gigachat_advisor).
 */
(function () {
    const form = document.getElementById("chat-form");
    const input = document.getElementById("chat-input");
    const submit = document.getElementById("chat-submit");
    const messagesRoot = document.getElementById("chat-messages");
    const suggestions = document.querySelectorAll("[data-suggestion]");

    if (!form || !input || !submit || !messagesRoot) {
        return;
    }

    const apiUrl = form.dataset.chatApi;
    const chatId = (form.dataset.chatId || "").trim();
    if (!apiUrl || !chatId) {
        return;
    }

    function syncSubmitState() {
        submit.disabled = !input.value.trim();
    }

    function resizeInput() {
        input.style.height = "auto";
        input.style.height = Math.min(input.scrollHeight, 160) + "px";
    }

    function formatTime(date) {
        return date.toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" });
    }

    function csrfToken() {
        const el = form.querySelector("[name=csrfmiddlewaretoken]");
        return el ? el.value : "";
    }

    function ensureThread() {
        let thread = messagesRoot.querySelector(".chat-messages__thread");
        if (!thread) {
            const empty = document.getElementById("chat-empty");
            if (empty) {
                empty.remove();
            }
            thread = document.createElement("div");
            thread.className = "chat-messages__thread";
            messagesRoot.appendChild(thread);
        }
        return thread;
    }

    function appendMessage(role, text, timeStr, options) {
        const opts = options || {};
        const thread = ensureThread();
        const article = document.createElement("article");
        article.className = "chat-msg chat-msg--" + role;

        const meta = document.createElement("div");
        meta.className = "chat-msg__meta";

        const author = document.createElement("span");
        author.className = "chat-msg__author text-additional";
        author.textContent = role === "user" ? "Вы" : "Помощник";

        const timeEl = document.createElement("time");
        timeEl.className = "chat-msg__time text-additional";
        timeEl.dateTime = new Date().toISOString();
        timeEl.textContent = timeStr;

        meta.appendChild(author);
        meta.appendChild(timeEl);

        const bubble = document.createElement("div");
        let bubbleClass =
            "chat-msg__bubble" + (role === "user" ? " bg-secondary" : " bg-surface");
        if (opts.richHtml && role !== "user") {
            bubbleClass += " chat-msg__bubble--rich";
        }
        bubble.className = bubbleClass;
        if (opts.richHtml && role !== "user") {
            bubble.innerHTML = opts.richHtml;
        } else {
            bubble.textContent = text;
        }

        article.appendChild(meta);
        article.appendChild(bubble);
        thread.appendChild(article);

        messagesRoot.scrollTop = messagesRoot.scrollHeight;
        return bubble;
    }

    function sendChat() {
        const text = input.value.trim();
        if (!text || submit.disabled) {
            return;
        }

        const token = csrfToken();
        const nowStr = formatTime(new Date());

        appendMessage("user", text, nowStr);
        input.value = "";
        syncSubmitState();
        resizeInput();

        const loadingBubble = appendMessage("assistant", "…", nowStr);

        submit.disabled = true;

        fetch(apiUrl, {
            method: "POST",
            credentials: "same-origin",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": token,
            },
            body: JSON.stringify({ message: text, chat_id: chatId }),
        })
            .then(function (res) {
                return res.json().then(function (body) {
                    return { ok: res.ok, body: body };
                });
            })
            .then(function (r) {
                if (r.ok && r.body.reply !== undefined) {
                    if (r.body.reply_html) {
                        loadingBubble.classList.add("chat-msg__bubble--rich");
                        loadingBubble.innerHTML = r.body.reply_html;
                    } else {
                        loadingBubble.textContent = r.body.reply;
                    }
                } else {
                    const errText =
                        r.body.error || "Не удалось получить ответ.";
                    if (r.body.reply_html) {
                        loadingBubble.classList.add("chat-msg__bubble--rich");
                        loadingBubble.innerHTML = r.body.reply_html;
                    } else {
                        loadingBubble.textContent = errText;
                    }
                }
            })
            .catch(function () {
                loadingBubble.textContent = "Ошибка сети. Проверьте соединение.";
            })
            .finally(function () {
                submit.disabled = !input.value.trim();
                messagesRoot.scrollTop = messagesRoot.scrollHeight;
            });
    }

    input.addEventListener("input", function () {
        syncSubmitState();
        resizeInput();
    });

    input.addEventListener("keydown", function (event) {
        if (event.key !== "Enter") {
            return;
        }
        if (event.shiftKey || event.ctrlKey || event.metaKey || event.altKey) {
            return;
        }
        if (event.isComposing) {
            return;
        }
        event.preventDefault();
        sendChat();
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
        sendChat();
    });

    syncSubmitState();
})();
