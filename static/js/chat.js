/* =========================================================================
   AI Interview Copilot — front-end logic
   Shared across index.html, upload.html and chat.html. Every block checks
   for the DOM elements it needs before wiring up, so this single file can
   safely be included on every page.
   ========================================================================= */

(function () {
  "use strict";

  // -----------------------------------------------------------------------
  // Dark mode toggle (all pages)
  // -----------------------------------------------------------------------
  function initThemeToggle() {
    var btn = document.getElementById("themeToggleBtn");
    if (!btn) return;

    function applyIcon() {
      var theme = document.documentElement.getAttribute("data-bs-theme") || "light";
      btn.innerHTML = theme === "dark"
        ? '<i class="bi bi-sun-fill"></i>'
        : '<i class="bi bi-moon-stars-fill"></i>';
    }

    applyIcon();

    btn.addEventListener("click", function () {
      var current = document.documentElement.getAttribute("data-bs-theme") || "light";
      var next = current === "dark" ? "light" : "dark";
      document.documentElement.setAttribute("data-bs-theme", next);
      localStorage.setItem("ic-theme", next);
      applyIcon();
    });
  }

  // -----------------------------------------------------------------------
  // Toast helper (upload.html + chat.html)
  // -----------------------------------------------------------------------
  function showToast(message, variant) {
    var container = document.getElementById("toastContainer");
    if (!container) {
      // Fall back gracefully if no toast container is present on this page.
      console.warn(message);
      return;
    }
    variant = variant || "primary";
    var wrapper = document.createElement("div");
    wrapper.className = "toast align-items-center text-bg-" + variant + " border-0";
    wrapper.setAttribute("role", "alert");
    wrapper.innerHTML =
      '<div class="d-flex">' +
      '<div class="toast-body"></div>' +
      '<button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>' +
      "</div>";
    wrapper.querySelector(".toast-body").textContent = message;
    container.appendChild(wrapper);
    var toast = new bootstrap.Toast(wrapper, { delay: 5000 });
    toast.show();
    wrapper.addEventListener("hidden.bs.toast", function () {
      wrapper.remove();
    });
  }

  // -----------------------------------------------------------------------
  // Help & Support modal (all pages)
  // -----------------------------------------------------------------------
  function initSupportModal() {
    var modalEl = document.getElementById("supportModal");
    var accordion = document.getElementById("faqAccordion");
    if (!modalEl || !accordion) return;

    function renderFaqs(faqs) {
      accordion.innerHTML = "";
      if (!faqs.length) {
        accordion.innerHTML = '<p class="ic-section-subtitle small mb-0">No FAQs yet — be the first to add one below.</p>';
        return;
      }
      faqs.forEach(function (faq) {
        var itemId = "faqItem" + faq.id;
        var item = document.createElement("div");
        item.className = "accordion-item";
        item.innerHTML =
          '<h2 class="accordion-header">' +
          '<button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#' + itemId + '"></button>' +
          "</h2>" +
          '<div id="' + itemId + '" class="accordion-collapse collapse" data-bs-parent="#faqAccordion">' +
          '<div class="accordion-body"></div></div>';
        item.querySelector(".accordion-button").textContent = faq.question;
        item.querySelector(".accordion-body").textContent = faq.answer;
        accordion.appendChild(item);
      });
    }

    function loadFaqs() {
      accordion.innerHTML = '<div class="text-center py-3"><div class="spinner-border spinner-border-sm text-primary" role="status"></div></div>';
      fetch("/api/faqs")
        .then(function (r) { return r.json(); })
        .then(function (data) { renderFaqs(data.faqs || []); })
        .catch(function () {
          accordion.innerHTML = '<p class="ic-section-subtitle small mb-0">Could not load FAQs — is the server running?</p>';
        });
    }

    modalEl.addEventListener("show.bs.modal", loadFaqs);

    var submitBtn = document.getElementById("submitFaqBtn");
    var questionInput = document.getElementById("faqQuestionInput");
    var answerInput = document.getElementById("faqAnswerInput");
    submitBtn.addEventListener("click", function () {
      var question = questionInput.value.trim();
      var answer = answerInput.value.trim();
      if (!question || !answer) {
        showToast("Please fill in both the question and the answer.", "warning");
        return;
      }
      submitBtn.disabled = true;
      fetch("/api/faqs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: question, answer: answer }),
      })
        .then(function (r) { return r.json().then(function (data) { return { ok: r.ok, data: data }; }); })
        .then(function (result) {
          submitBtn.disabled = false;
          if (!result.ok || !result.data.success) {
            showToast(result.data.error || "Could not add the question.", "danger");
            return;
          }
          questionInput.value = "";
          answerInput.value = "";
          showToast("Added to the FAQ list. Thank you!", "success");
          loadFaqs();
        })
        .catch(function () {
          submitBtn.disabled = false;
          showToast("Network error while adding the FAQ.", "danger");
        });
    });
  }

  // -----------------------------------------------------------------------
  // Add Company modal (all pages)
  // -----------------------------------------------------------------------
  var COMPANY_ICON_CHOICES = [
    "bi-building", "bi-briefcase-fill", "bi-globe2", "bi-rocket-takeoff-fill",
    "bi-bank", "bi-cloud-fill", "bi-cpu-fill", "bi-gem", "bi-lightning-charge-fill", "bi-shop-window",
  ];

  function initAddCompanyModal() {
    var modalEl = document.getElementById("addCompanyModal");
    var picker = document.getElementById("companyIconPicker");
    if (!modalEl || !picker) return;

    var selectedIcon = COMPANY_ICON_CHOICES[0];

    function renderPicker() {
      picker.innerHTML = "";
      COMPANY_ICON_CHOICES.forEach(function (icon) {
        var btn = document.createElement("button");
        btn.type = "button";
        btn.className = "ic-icon-choice" + (icon === selectedIcon ? " active" : "");
        btn.innerHTML = '<i class="bi ' + icon + '"></i>';
        btn.addEventListener("click", function () {
          selectedIcon = icon;
          renderPicker();
        });
        picker.appendChild(btn);
      });
    }
    renderPicker();

    var nameInput = document.getElementById("newCompanyName");
    var createBtn = document.getElementById("createCompanyBtn");
    createBtn.addEventListener("click", function () {
      var name = nameInput.value.trim();
      if (!name) {
        showToast("Please enter a company name.", "warning");
        return;
      }
      createBtn.disabled = true;
      fetch("/api/companies", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: name, icon: selectedIcon }),
      })
        .then(function (r) { return r.json().then(function (data) { return { ok: r.ok, data: data }; }); })
        .then(function (result) {
          createBtn.disabled = false;
          if (!result.ok || !result.data.success) {
            showToast(result.data.error || "Could not create the company.", "danger");
            return;
          }
          showToast(result.data.company.name + " added.", "success");
          nameInput.value = "";
          var modalInstance = bootstrap.Modal.getInstance(modalEl);
          if (modalInstance) modalInstance.hide();
          setTimeout(function () { window.location.reload(); }, 700);
        })
        .catch(function () {
          createBtn.disabled = false;
          showToast("Network error while creating the company.", "danger");
        });
    });
  }

  // -----------------------------------------------------------------------
  // Upload page
  // -----------------------------------------------------------------------
  function initUploadPage() {
    var form = document.getElementById("uploadForm");
    if (!form) return;

    var companySelect = document.getElementById("companySelect");
    var customWrap = document.getElementById("customCompanyWrap");
    var customInput = document.getElementById("customCompanyInput");
    var dropzone = document.getElementById("dropzone");
    var fileInput = document.getElementById("fileInput");
    var fileChips = document.getElementById("fileChips");
    var spinnerOverlay = document.getElementById("spinnerOverlay");
    var spinnerMessage = document.getElementById("spinnerMessage");
    var submitBtn = document.getElementById("uploadSubmitBtn");

    var selectedFiles = [];

    function toggleCustomField() {
      var isCustom = companySelect.value === "Custom";
      customWrap.classList.toggle("d-none", !isCustom);
      customInput.required = isCustom;
    }
    companySelect.addEventListener("change", toggleCustomField);
    toggleCustomField();

    function renderChips() {
      fileChips.innerHTML = "";
      selectedFiles.forEach(function (file, index) {
        var chip = document.createElement("span");
        chip.className = "ic-file-chip";
        var icon = file.name.toLowerCase().endsWith(".pdf") ? "bi-file-earmark-pdf" : "bi-file-earmark-text";
        chip.innerHTML = '<i class="bi ' + icon + '"></i><span></span><i class="bi bi-x-circle remove-file"></i>';
        chip.querySelector("span").textContent = file.name + " (" + Math.ceil(file.size / 1024) + " KB)";
        chip.querySelector(".remove-file").addEventListener("click", function () {
          selectedFiles.splice(index, 1);
          renderChips();
        });
        fileChips.appendChild(chip);
      });
    }

    function addFiles(fileList) {
      Array.prototype.forEach.call(fileList, function (file) {
        var extension = file.name.split(".").pop().toLowerCase();
        if (extension !== "pdf" && extension !== "txt") {
          showToast("'" + file.name + "' skipped — only PDF and TXT files are supported.", "warning");
          return;
        }
        selectedFiles.push(file);
      });
      renderChips();
    }

    dropzone.addEventListener("click", function () {
      fileInput.click();
    });
    fileInput.addEventListener("change", function () {
      addFiles(fileInput.files);
      fileInput.value = "";
    });
    ["dragenter", "dragover"].forEach(function (evt) {
      dropzone.addEventListener(evt, function (e) {
        e.preventDefault();
        dropzone.classList.add("dragover");
      });
    });
    ["dragleave", "drop"].forEach(function (evt) {
      dropzone.addEventListener(evt, function (e) {
        e.preventDefault();
        dropzone.classList.remove("dragover");
      });
    });
    dropzone.addEventListener("drop", function (e) {
      if (e.dataTransfer && e.dataTransfer.files) {
        addFiles(e.dataTransfer.files);
      }
    });

    function setBusy(isBusy, message) {
      spinnerOverlay.classList.toggle("d-none", !isBusy);
      submitBtn.disabled = isBusy;
      if (message) spinnerMessage.textContent = message;
    }

    form.addEventListener("submit", function (e) {
      e.preventDefault();

      if (selectedFiles.length === 0) {
        showToast("Please add at least one PDF or TXT file.", "warning");
        return;
      }
      if (companySelect.value === "Custom" && !customInput.value.trim()) {
        showToast("Please enter a custom company name.", "warning");
        return;
      }

      var formData = new FormData();
      formData.append("company", companySelect.value);
      formData.append("custom_company", customInput.value.trim());
      selectedFiles.forEach(function (file) {
        formData.append("files", file);
      });

      setBusy(true, "Uploading and processing documents…");

      fetch("/upload", { method: "POST", body: formData })
        .then(function (response) {
          return response.json().then(function (data) {
            return { ok: response.ok, data: data };
          });
        })
        .then(function (result) {
          setBusy(false);
          if (!result.ok || !result.data.success) {
            showToast(result.data.error || "Upload failed.", "danger");
            return;
          }
          var stats = result.data.processing;
          showToast(
            "Processed " + result.data.saved_files.length + " file(s) for " + result.data.company +
            " (" + stats.chunks_added + " new chunks indexed).",
            "success"
          );
          selectedFiles = [];
          renderChips();
          setTimeout(function () {
            window.location.href = "/chat?company=" + encodeURIComponent(result.data.company);
          }, 1200);
        })
        .catch(function () {
          setBusy(false);
          showToast("Network error while uploading. Is the Flask server running?", "danger");
        });
    });

    document.querySelectorAll(".reprocess-btn").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var company = btn.getAttribute("data-company");
        setBusy(true, "Reprocessing " + company + "…");
        fetch("/process", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ company: company, force: true }),
        })
          .then(function (response) {
            return response.json();
          })
          .then(function (data) {
            setBusy(false);
            if (!data.success) {
              showToast(data.error || "Reprocessing failed.", "danger");
              return;
            }
            showToast(company + " reprocessed successfully.", "success");
            setTimeout(function () {
              window.location.reload();
            }, 900);
          })
          .catch(function () {
            setBusy(false);
            showToast("Network error while reprocessing.", "danger");
          });
      });
    });
  }

  // -----------------------------------------------------------------------
  // Chat page
  // -----------------------------------------------------------------------
  function initChatPage() {
    var messagesEl = document.getElementById("chatMessages");
    if (!messagesEl) return;

    var historyDataEl = document.getElementById("chatHistoryData");
    var configDataEl = document.getElementById("chatConfigData");
    var initialHistory = [];
    var config = { selectedCompany: "", selectedMode: "general", ollamaAvailable: true };
    try {
      initialHistory = JSON.parse(historyDataEl.textContent || "[]");
    } catch (e) {
      initialHistory = [];
    }
    try {
      config = JSON.parse(configDataEl.textContent || "{}");
    } catch (e) {
      // keep defaults
    }

    var emptyState = document.getElementById("chatEmptyState");
    var companySelect = document.getElementById("companySelect");
    var modeButtons = document.querySelectorAll(".ic-mode-pill");
    var suggestedWrap = document.getElementById("suggestedQuestions");
    var topicsWrap = document.getElementById("topicsPanel");
    var favoritesList = document.getElementById("favoritesList");
    var favoritesCount = document.getElementById("favoritesCount");
    var searchInput = document.getElementById("searchChat");
    var chatInput = document.getElementById("chatInput");
    var sendBtn = document.getElementById("sendBtn");
    var clearBtn = document.getElementById("clearChatBtn");
    var downloadBtn = document.getElementById("downloadChatBtn");

    var state = {
      company: companySelect.value || config.selectedCompany || "",
      mode: config.selectedMode || "general",
      messages: [],
      sending: false,
    };

    var MODE_LABELS = {};
    modeButtons.forEach(function (btn) {
      MODE_LABELS[btn.getAttribute("data-mode")] = btn.textContent.trim();
    });

    // ---- Favorites (localStorage) -----------------------------------
    function loadFavorites() {
      try {
        return JSON.parse(localStorage.getItem("ic-favorites") || "[]");
      } catch (e) {
        return [];
      }
    }
    function saveFavorites(favorites) {
      localStorage.setItem("ic-favorites", JSON.stringify(favorites));
    }
    function isFavorite(question, company) {
      return loadFavorites().some(function (f) { return f.question === question && f.company === company; });
    }
    function toggleFavorite(question, company, mode) {
      var favorites = loadFavorites();
      var index = favorites.findIndex(function (f) { return f.question === question && f.company === company; });
      if (index >= 0) {
        favorites.splice(index, 1);
      } else {
        favorites.unshift({ question: question, company: company, mode: mode });
      }
      saveFavorites(favorites);
      renderFavorites();
    }
    function renderFavorites() {
      var favorites = loadFavorites();
      favoritesCount.textContent = favorites.length;
      favoritesList.innerHTML = "";
      if (favorites.length === 0) {
        var empty = document.createElement("p");
        empty.className = "ic-section-subtitle small mb-0";
        empty.textContent = "Star a question to save it here.";
        favoritesList.appendChild(empty);
        return;
      }
      favorites.forEach(function (fav) {
        var chip = document.createElement("button");
        chip.type = "button";
        chip.className = "ic-suggested-chip text-start";
        chip.textContent = fav.question;
        chip.title = "Click to ask again (" + fav.company + ")";
        chip.addEventListener("click", function () {
          companySelect.value = fav.company;
          state.company = fav.company;
          setActiveMode(fav.mode || "general");
          chatInput.value = fav.question;
          chatInput.focus();
        });
        favoritesList.appendChild(chip);
      });
    }

    // ---- Rendering ------------------------------------------------------
    function scrollToBottom() {
      messagesEl.scrollTop = messagesEl.scrollHeight;
    }

    function confidenceBadgeClass(level) {
      return { high: "text-bg-success", medium: "text-bg-warning", low: "text-bg-danger", none: "text-bg-secondary" }[level] || "text-bg-secondary";
    }

    function renderMessage(msg) {
      emptyState.classList.add("d-none");

      var row = document.createElement("div");
      row.className = "ic-bubble-row " + (msg.role === "user" ? "user" : "assistant");
      row.setAttribute("data-role", msg.role);
      row.setAttribute("data-search-text", (msg.content || "").toLowerCase());

      var bubble = document.createElement("div");
      bubble.className = "ic-bubble " + (msg.role === "user" ? "user" : "assistant");

      var contentEl = document.createElement("div");
      contentEl.textContent = msg.content;
      bubble.appendChild(contentEl);

      if (msg.role === "assistant") {
        var metaRow = document.createElement("div");
        metaRow.className = "ic-bubble-meta d-flex align-items-center gap-2 flex-wrap";

        if (msg.confidence) {
          var badge = document.createElement("span");
          badge.className = "badge ic-confidence-badge " + confidenceBadgeClass(msg.confidence.level);
          badge.textContent = "Confidence: " + msg.confidence.label + (msg.confidence.score ? " (" + msg.confidence.score + "%)" : "");
          metaRow.appendChild(badge);
        }
        if (msg.mode && MODE_LABELS[msg.mode]) {
          var modeBadge = document.createElement("span");
          modeBadge.className = "badge text-bg-light border";
          modeBadge.textContent = MODE_LABELS[msg.mode];
          metaRow.appendChild(modeBadge);
        }
        bubble.appendChild(metaRow);

        if (msg.sources && msg.sources.length > 0) {
          var sourcesEl = document.createElement("div");
          sourcesEl.className = "ic-sources";
          var label = document.createElement("div");
          label.className = "fw-semibold mb-1";
          label.innerHTML = '<i class="bi bi-link-45deg"></i> Sources';
          sourcesEl.appendChild(label);
          msg.sources.forEach(function (source) {
            var chip = document.createElement("span");
            chip.className = "ic-source-chip";
            chip.innerHTML = '<i class="bi bi-file-earmark-text"></i>';
            var text = document.createElement("span");
            text.textContent = source.source + " · Chunk " + source.chunk_id;
            chip.appendChild(text);
            sourcesEl.appendChild(chip);
          });
          bubble.appendChild(sourcesEl);
        }
      } else {
        var star = document.createElement("i");
        var favActive = isFavorite(msg.content, msg.company || state.company);
        star.className = "bi favorite-star ms-2 " + (favActive ? "bi-star-fill active" : "bi-star");
        star.title = "Save as favorite question";
        star.addEventListener("click", function () {
          toggleFavorite(msg.content, msg.company || state.company, msg.mode || state.mode);
          star.classList.toggle("bi-star-fill");
          star.classList.toggle("bi-star");
          star.classList.toggle("active");
        });
        var starRow = document.createElement("div");
        starRow.className = "text-end";
        starRow.appendChild(star);
        bubble.appendChild(starRow);
      }

      row.appendChild(bubble);
      messagesEl.appendChild(row);
      scrollToBottom();
    }

    function renderAll() {
      messagesEl.querySelectorAll(".ic-bubble-row").forEach(function (el) { el.remove(); });
      if (state.messages.length === 0) {
        emptyState.classList.remove("d-none");
      } else {
        state.messages.forEach(renderMessage);
      }
    }

    function showTyping() {
      var row = document.createElement("div");
      row.className = "ic-bubble-row assistant";
      row.id = "typingIndicatorRow";
      var bubble = document.createElement("div");
      bubble.className = "ic-bubble assistant";
      bubble.innerHTML = '<div class="ic-typing"><span></span><span></span><span></span></div>';
      row.appendChild(bubble);
      messagesEl.appendChild(row);
      scrollToBottom();
    }
    function hideTyping() {
      var row = document.getElementById("typingIndicatorRow");
      if (row) row.remove();
    }

    // ---- Suggested questions & topics -----------------------------------
    function loadSuggestedQuestions() {
      suggestedWrap.innerHTML = '<div class="spinner-border spinner-border-sm text-primary" role="status"></div>';
      var params = new URLSearchParams({ mode: state.mode, company: state.company || "this company" });
      fetch("/api/suggested_questions?" + params.toString())
        .then(function (r) { return r.json(); })
        .then(function (data) {
          suggestedWrap.innerHTML = "";
          (data.questions || []).forEach(function (question) {
            var chip = document.createElement("button");
            chip.type = "button";
            chip.className = "ic-suggested-chip text-start";
            chip.textContent = question;
            chip.addEventListener("click", function () {
              sendMessage(question);
            });
            suggestedWrap.appendChild(chip);
          });
        })
        .catch(function () { suggestedWrap.innerHTML = ""; });
    }

    function loadTopics() {
      if (!state.company) {
        topicsWrap.innerHTML = '<p class="ic-section-subtitle small mb-0">Select a company to see trends.</p>';
        return;
      }
      topicsWrap.innerHTML = '<div class="spinner-border spinner-border-sm text-primary" role="status"></div>';
      fetch("/api/topics?company=" + encodeURIComponent(state.company))
        .then(function (r) { return r.json(); })
        .then(function (data) {
          topicsWrap.innerHTML = "";
          var topics = data.topics || [];
          if (topics.length === 0) {
            topicsWrap.innerHTML = '<p class="ic-section-subtitle small mb-0">No trends yet — ask a few questions first.</p>';
            return;
          }
          var maxCount = Math.max.apply(null, topics.map(function (t) { return t.count; }));
          topics.slice(0, 8).forEach(function (topic) {
            var wrap = document.createElement("div");
            var row = document.createElement("div");
            row.className = "d-flex justify-content-between small mb-1";
            row.innerHTML = "<span class=\"text-capitalize\"></span><span class=\"ic-section-subtitle\"></span>";
            row.children[0].textContent = topic.topic;
            row.children[1].textContent = topic.count;
            var bar = document.createElement("div");
            bar.className = "ic-topic-bar";
            var fill = document.createElement("div");
            fill.className = "ic-topic-bar-fill";
            fill.style.width = Math.max(8, Math.round((topic.count / maxCount) * 100)) + "%";
            bar.appendChild(fill);
            wrap.appendChild(row);
            wrap.appendChild(bar);
            wrap.className = "mb-2";
            topicsWrap.appendChild(wrap);
          });
        })
        .catch(function () { topicsWrap.innerHTML = ""; });
    }

    // ---- Company / mode selection ----------------------------------------
    function setActiveMode(mode) {
      state.mode = mode;
      modeButtons.forEach(function (btn) {
        btn.classList.toggle("active", btn.getAttribute("data-mode") === mode);
      });
      loadSuggestedQuestions();
    }

    companySelect.addEventListener("change", function () {
      state.company = companySelect.value;
      var url = new URL(window.location.href);
      url.searchParams.set("company", state.company);
      window.history.replaceState({}, "", url);
      loadSuggestedQuestions();
      loadTopics();
    });

    modeButtons.forEach(function (btn) {
      btn.addEventListener("click", function () {
        setActiveMode(btn.getAttribute("data-mode"));
      });
    });

    // ---- Sending messages -------------------------------------------------
    function autoResize() {
      chatInput.style.height = "auto";
      chatInput.style.height = Math.min(chatInput.scrollHeight, 160) + "px";
    }
    chatInput.addEventListener("input", autoResize);

    function sendMessage(overrideText) {
      var text = (overrideText !== undefined ? overrideText : chatInput.value).trim();
      if (!text || state.sending) return;

      if (!state.company) {
        showToast("Please select a company first.", "warning");
        return;
      }
      if (!config.ollamaAvailable) {
        showToast("Ollama is not reachable — start it before asking questions.", "warning");
      }

      var userMsg = { role: "user", content: text, company: state.company, mode: state.mode };
      state.messages.push(userMsg);
      renderMessage(userMsg);

      if (overrideText === undefined) {
        chatInput.value = "";
        autoResize();
      }

      state.sending = true;
      sendBtn.disabled = true;
      showTyping();

      fetch("/api/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ company: state.company, mode: state.mode, question: text }),
      })
        .then(function (response) {
          return response.json().then(function (data) {
            return { ok: response.ok, data: data };
          });
        })
        .then(function (result) {
          hideTyping();
          state.sending = false;
          sendBtn.disabled = false;

          if (!result.data.success) {
            showToast(result.data.error || "Something went wrong.", "danger");
            var errorMsg = {
              role: "assistant",
              content: result.data.error || "Something went wrong while answering your question.",
              sources: [],
              confidence: { score: 0, label: "Error", level: "none" },
              company: state.company,
              mode: state.mode,
            };
            state.messages.push(errorMsg);
            renderMessage(errorMsg);
            return;
          }

          var assistantMsg = {
            role: "assistant",
            content: result.data.answer,
            sources: result.data.sources,
            confidence: result.data.confidence,
            company: result.data.company,
            mode: result.data.mode,
          };
          state.messages.push(assistantMsg);
          renderMessage(assistantMsg);
          loadTopics();
        })
        .catch(function () {
          hideTyping();
          state.sending = false;
          sendBtn.disabled = false;
          showToast("Network error — is the Flask server running?", "danger");
        });
    }

    sendBtn.addEventListener("click", function () { sendMessage(); });
    chatInput.addEventListener("keydown", function (e) {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    });

    // ---- Clear chat ---------------------------------------------------
    clearBtn.addEventListener("click", function () {
      fetch("/clear_chat", { method: "POST" })
        .then(function () {
          state.messages = [];
          renderAll();
          showToast("Conversation cleared.", "success");
        })
        .catch(function () {
          showToast("Could not clear the conversation.", "danger");
        });
    });

    // ---- Download PDF ---------------------------------------------------
    downloadBtn.addEventListener("click", function () {
      if (state.messages.length === 0) {
        showToast("Nothing to export yet.", "warning");
        return;
      }
      fetch("/download_chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: state.messages, company: state.company, mode: state.mode }),
      })
        .then(function (response) {
          if (!response.ok) throw new Error("Export failed");
          return response.blob();
        })
        .then(function (blob) {
          var url = window.URL.createObjectURL(blob);
          var a = document.createElement("a");
          a.href = url;
          a.download = "interview_copilot_chat.pdf";
          document.body.appendChild(a);
          a.click();
          a.remove();
          window.URL.revokeObjectURL(url);
        })
        .catch(function () {
          showToast("Could not export the conversation.", "danger");
        });
    });

    // ---- Search previous conversation -----------------------------------
    searchInput.addEventListener("input", function () {
      var query = searchInput.value.trim().toLowerCase();
      messagesEl.querySelectorAll(".ic-bubble-row").forEach(function (row) {
        if (row.id === "typingIndicatorRow") return;
        var matches = !query || row.getAttribute("data-search-text").indexOf(query) !== -1;
        row.classList.toggle("d-none", !matches);
      });
    });

    // ---- Init ---------------------------------------------------------
    state.messages = initialHistory || [];
    renderAll();
    setActiveMode(state.mode);
    loadTopics();
    renderFavorites();
  }

  document.addEventListener("DOMContentLoaded", function () {
    initThemeToggle();
    initSupportModal();
    initAddCompanyModal();
    initUploadPage();
    initChatPage();
  });
})();
