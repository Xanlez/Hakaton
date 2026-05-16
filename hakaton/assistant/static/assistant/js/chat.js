/**
 * Чат: POST на api/chat — ответ всегда NDJSON-поток (delta / done / error), кроме ранней ошибки (JSON).
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

    function consumeNdjsonResponse(res, loadingBubble) {
        loadingBubble.textContent = "";
        loadingBubble.classList.remove("chat-msg__bubble--rich");

        function applyLine(rawLine) {
            const line = rawLine.replace(/\r$/, "").trim();
            if (!line) {
                return;
            }
            let obj;
            try {
                obj = JSON.parse(line);
            } catch (ignore) {
                return;
            }
            if (obj.type === "delta" && obj.text) {
                loadingBubble.textContent += obj.text;
            } else if (obj.type === "done") {
                if (obj.reply_html) {
                    loadingBubble.classList.add("chat-msg__bubble--rich");
                    loadingBubble.innerHTML = obj.reply_html;
                } else {
                    loadingBubble.textContent = obj.reply || "";
                }
            } else if (obj.type === "error") {
                if (obj.reply_html) {
                    loadingBubble.classList.add("chat-msg__bubble--rich");
                    loadingBubble.innerHTML = obj.reply_html;
                } else {
                    loadingBubble.textContent =
                        obj.message || "Не удалось получить ответ.";
                }
            }
            messagesRoot.scrollTop = messagesRoot.scrollHeight;
        }

        function parseAllFromText(full) {
            full.split(/\n/).forEach(function (segment) {
                applyLine(segment);
            });
        }

        let cloned = null;
        try {
            cloned = typeof res.clone === "function" ? res.clone() : null;
        } catch (ignore) {
            cloned = null;
        }

        const reader =
            res.body && typeof res.body.getReader === "function"
                ? res.body.getReader()
                : null;

        if (!reader) {
            return res.text().then(parseAllFromText);
        }

        const decoder = new TextDecoder("utf-8");
        let buf = "";

        function pump() {
            return reader
                .read()
                .then(function (chunk) {
                    if (chunk.done) {
                        if (buf.replace(/\s/g, "").length) {
                            parseAllFromText(buf);
                            buf = "";
                        }
                        return undefined;
                    }
                    try {
                        buf += decoder.decode(chunk.value, { stream: true });
                    } catch (ignore) {
                        if (cloned) {
                            return cloned.text().then(parseAllFromText);
                        }
                        throw new Error("Ошибка разбора ответа (UTF-8).");
                    }
                    let nl;
                    while ((nl = buf.indexOf("\n")) >= 0) {
                        const line = buf.slice(0, nl);
                        buf = buf.slice(nl + 1);
                        applyLine(line);
                    }
                    return pump();
                })
                .catch(function () {
                    if (cloned) {
                        return cloned.text().then(parseAllFromText);
                    }
                    return res.text().then(parseAllFromText);
                });
        }

        return pump();
    }

    function showHttpErrorBubble(loadingBubble, res, rawBody) {
        let body = null;
        try {
            body = rawBody ? JSON.parse(rawBody) : null;
        } catch (ignore) {
            body = null;
        }
        let errText = "Не удалось получить ответ.";
        if (body && (body.error || body.message)) {
            errText = body.error || body.message;
            if (body.reply_html) {
                loadingBubble.classList.add("chat-msg__bubble--rich");
                loadingBubble.innerHTML = body.reply_html;
                return;
            }
        } else if (rawBody && rawBody.trim()) {
            errText =
                "Ошибка " +
                res.status +
                ": " +
                rawBody.trim().substring(0, 280);
        } else {
            errText =
                "Ошибка " + res.status + " " + (res.statusText || "").trim();
        }
        loadingBubble.textContent = errText || "Не удалось получить ответ.";
        messagesRoot.scrollTop = messagesRoot.scrollHeight;
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
                Accept: "application/x-ndjson, application/json",
            },
            body: JSON.stringify({ message: text, chat_id: chatId }),
        })
            .then(function (res) {
                if (res.ok) {
                    return consumeNdjsonResponse(res, loadingBubble);
                }
                return res.text().then(function (raw) {
                    showHttpErrorBubble(loadingBubble, res, raw);
                });
            })
            .catch(function (err) {
                let msg = "";
                if (err && typeof err.message === "string") {
                    msg = err.message.trim();
                }
                if (!msg && err != null && err !== undefined) {
                    msg = String(err).trim();
                }
                loadingBubble.textContent =
                    msg ||
                    "Не удалось прочитать ответ сервера. Проверьте соединение.";
                messagesRoot.scrollTop = messagesRoot.scrollHeight;
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
