(function () {
  "use strict";

  const API_TICKET = "/api/ticket";
  const API_SUPPORT = "/api/support";
  const API_REPORTING = "/api/reporting";

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  let selectedId = null;
  let inFlight = 0;
  let currentTab = "customer";
  let cachedAssignments = null;
  let assignmentsFetchError = false;

  function statusPillModifier(status) {
    const raw = String(status || "open")
      .toLowerCase()
      .replace(/\s+/g, "_");
    if (raw === "open" || raw === "in_progress" || raw === "resolved" || raw === "closed") {
      return raw;
    }
    return "open";
  }

  function detailStatusPillClass(status) {
    return `status-pill status-pill--${statusPillModifier(status)}`;
  }

  function assignedAgentNameFromRows(assignments) {
    if (!Array.isArray(assignments) || assignments.length === 0) {
      return null;
    }
    const last = assignments[assignments.length - 1];
    if (!last || last.agent_id == null) {
      return null;
    }
    const name = String(last.agent_id).trim();
    return name.length > 0 ? name : null;
  }

  function hideCustomerAssignNotice(box) {
    if (!box) return;
    box.textContent = "";
    box.setAttribute("hidden", "");
  }

  function updateCustomerAssignNotice() {
    const box = $("#customer-assign-notice");
    const customerLine = $("#assignee-line-customer");
    if (!customerLine) return;

    if (currentTab !== "customer") {
      customerLine.hidden = true;
      customerLine.textContent = "";
      hideCustomerAssignNotice(box);
      return;
    }

    if (cachedAssignments === null) {
      customerLine.hidden = false;
      customerLine.textContent = "Loading…";
      customerLine.classList.add("muted");
      hideCustomerAssignNotice(box);
      return;
    }

    if (assignmentsFetchError) {
      customerLine.hidden = false;
      customerLine.textContent = "Could not load assignment status.";
      customerLine.classList.add("muted");
      hideCustomerAssignNotice(box);
      return;
    }

    const agentName = assignedAgentNameFromRows(cachedAssignments);
    if (!agentName) {
      customerLine.hidden = false;
      customerLine.textContent = "No agent assigned yet.";
      customerLine.classList.add("muted");
      hideCustomerAssignNotice(box);
      return;
    }

    customerLine.hidden = true;
    customerLine.textContent = "";
    if (box) {
      box.textContent = `Your ticket is assigned to ${agentName} and is being worked on.`;
      box.removeAttribute("hidden");
    }
  }

  function applyTab(tab) {
    currentTab = tab;
    const app = $("#app");
    if (!app) return;
    app.classList.remove("portal--customer", "portal--support");
    app.classList.add(tab === "customer" ? "portal--customer" : "portal--support");

    const isCustomer = tab === "customer";
    const tabCustomer = $("#tab-customer");
    const tabSupport = $("#tab-support");
    if (tabCustomer) {
      tabCustomer.classList.toggle("tab--active", isCustomer);
      tabCustomer.setAttribute("aria-selected", String(isCustomer));
    }
    if (tabSupport) {
      tabSupport.classList.toggle("tab--active", !isCustomer);
      tabSupport.setAttribute("aria-selected", String(!isCustomer));
    }

    const listTitle = $("#list-panel-title");
    if (listTitle) {
      listTitle.textContent = isCustomer ? "Your tickets" : "All tickets";
    }

    const msgTitle = $("#messages-section-title");
    if (msgTitle) {
      msgTitle.textContent = isCustomer ? "Conversation" : "Messages";
    }

    const msgForm = $("#form-message");
    if (msgForm) {
      const nameInput = msgForm.querySelector('input[name="agent_id"]');
      const bodyInput = msgForm.querySelector('textarea[name="body"]');
      const submitBtn = msgForm.querySelector('button[type="submit"]');
      if (nameInput) {
        nameInput.placeholder = isCustomer ? "Your name" : "Agent id";
      }
      if (bodyInput) {
        bodyInput.placeholder = isCustomer ? "Your reply" : "Message to customer";
      }
      if (submitBtn) {
        submitBtn.textContent = isCustomer ? "Send reply" : "Send message";
      }
    }
    updateCustomerAssignNotice();
  }

  function setLoading(on) {
    inFlight += on ? 1 : -1;
    const bar = $("#loading-bar");
    bar.classList.toggle("loading-bar-hidden", inFlight <= 0);
  }

  function showBanner(message, isError = true) {
    const el = $("#banner");
    el.style.background = "";
    el.style.borderColor = "";
    el.style.color = "";
    if (!message) {
      el.classList.add("banner-hidden");
      el.textContent = "";
      return;
    }
    el.textContent = message;
    el.classList.remove("banner-hidden");
    if (!isError) {
      el.style.background = "rgba(78, 207, 138, 0.12)";
      el.style.borderColor = "rgba(78, 207, 138, 0.35)";
      el.style.color = "#a8ebc4";
    }
  }

  async function api(url, options = {}) {
    const opts = {
      headers: { Accept: "application/json", ...options.headers },
      ...options,
    };
    if (opts.body && typeof opts.body === "object" && !(opts.body instanceof FormData)) {
      opts.body = JSON.stringify(opts.body);
      opts.headers["Content-Type"] = "application/json";
    }
    setLoading(true);
    try {
      const res = await fetch(url, opts);
      const text = await res.text();
      let data = null;
      if (text) {
        try {
          data = JSON.parse(text);
        } catch {
          data = text;
        }
      }
      if (!res.ok) {
        const detail =
          data && typeof data === "object" && data.detail != null
            ? typeof data.detail === "string"
              ? data.detail
              : JSON.stringify(data.detail)
            : res.statusText;
        throw new Error(detail || `HTTP ${res.status}`);
      }
      return data;
    } finally {
      setLoading(false);
    }
  }

  async function loadSummary() {
    try {
      const row = await api(`${API_REPORTING}/reports/summary`);
      $("#sum-created").textContent = row.tickets_created ?? "—";
      $("#sum-updated").textContent = row.tickets_updated ?? "—";
      $("#sum-messages").textContent = row.support_messages ?? "—";
      $("#sum-resolved").textContent = row.support_resolved ?? "—";
      const meta = $("#summary-meta");
      meta.textContent = row.updated_at
        ? `Counters last updated: ${new Date(row.updated_at).toLocaleString()}`
        : "";
    } catch (e) {
      showBanner(`Summary: ${e.message}`);
    }
  }

  function formatDate(iso) {
    if (!iso) return "";
    try {
      return new Date(iso).toLocaleString();
    } catch {
      return iso;
    }
  }

  function renderTicketList(tickets) {
    const ul = $("#ticket-list");
    const empty = $("#ticket-list-empty");
    ul.innerHTML = "";
    if (!tickets.length) {
      empty.classList.remove("empty-hidden");
      return;
    }
    empty.classList.add("empty-hidden");
    for (const t of tickets) {
      const li = document.createElement("li");
      const btn = document.createElement("button");
      btn.type = "button";
      btn.dataset.id = String(t.id);
      if (selectedId === t.id) btn.classList.add("active");
      btn.innerHTML = `<span class="t-title"></span><span class="t-meta"></span>`;
      btn.querySelector(".t-title").textContent = t.title;
      const meta = btn.querySelector(".t-meta");
      meta.replaceChildren();
      const pre = document.createElement("span");
      pre.className = "t-meta-prefix";
      pre.textContent = `#${t.id} · `;
      const pill = document.createElement("span");
      pill.className = `status-pill status-pill--${statusPillModifier(t.status)}`;
      pill.textContent = t.status;
      meta.appendChild(pre);
      meta.appendChild(pill);
      btn.addEventListener("click", () => selectTicket(t.id));
      li.appendChild(btn);
      ul.appendChild(li);
    }
  }

  async function loadTickets() {
    try {
      const tickets = await api(`${API_TICKET}/tickets`);
      renderTicketList(tickets);
      if (selectedId != null && !tickets.some((t) => t.id === selectedId)) {
        selectedId = null;
        showDetailPlaceholder();
      }
    } catch (e) {
      showBanner(`Tickets: ${e.message}`);
    }
  }

  function showDetailPlaceholder() {
    $("#detail-panel").hidden = true;
    $("#detail-placeholder").hidden = false;
    hideCustomerAssignNotice($("#customer-assign-notice"));
    const customerLine = $("#assignee-line-customer");
    if (customerLine) {
      customerLine.hidden = true;
      customerLine.textContent = "";
    }
  }

  function renderAssigneeLine(assignments) {
    const el = $("#assignee-line");
    if (!el) return;
    el.textContent = "";
    if (!Array.isArray(assignments) || assignments.length === 0) {
      el.textContent = "No agent assigned yet.";
      el.classList.add("muted");
      return;
    }
    el.classList.remove("muted");
    const last = assignments[assignments.length - 1];
    if (!last || typeof last.agent_id !== "string") {
      el.textContent = "No agent assigned yet.";
      el.classList.add("muted");
      return;
    }
    el.appendChild(document.createTextNode("Assigned agent: "));
    const name = document.createElement("strong");
    name.className = "assignee-name";
    name.textContent = last.agent_id;
    el.appendChild(name);
  }

  async function loadAssignmentsForTicket(ticketId) {
    const el = $("#assignee-line");
    if (!el) return;
    assignmentsFetchError = false;
    cachedAssignments = null;
    updateCustomerAssignNotice();
    el.textContent = "Loading…";
    el.classList.add("muted");
    try {
      const rows = await api(`${API_SUPPORT}/tickets/${ticketId}/assignments`);
      if (!Array.isArray(rows)) {
        throw new Error("Assignments response was not a JSON array (hard refresh or rebuild web + support images).");
      }
      assignmentsFetchError = false;
      cachedAssignments = rows;
      renderAssigneeLine(rows);
      updateCustomerAssignNotice();
    } catch (e) {
      assignmentsFetchError = true;
      cachedAssignments = [];
      el.textContent = "Could not load assignee.";
      el.classList.add("muted");
      showBanner(`Assignee: ${e.message}`);
      updateCustomerAssignNotice();
    }
  }

  function setResolveEnabledForStatus(status) {
    const btn = $("#btn-resolve-ticket");
    const off = status === "resolved" || status === "closed";
    btn.disabled = off;
    btn.classList.toggle("btn-resolve-disabled", off);
    if (off) {
      btn.title = "This ticket is already resolved or closed.";
    } else {
      btn.removeAttribute("title");
    }
  }

  async function loadMessages(ticketId) {
    const list = $("#message-list");
    list.innerHTML = "";
    try {
      const messages = await api(`${API_SUPPORT}/tickets/${ticketId}/messages`);
      if (!messages.length) {
        const li = document.createElement("li");
        li.textContent = "No messages yet.";
        li.style.border = "none";
        li.style.background = "transparent";
        li.style.color = "var(--text-muted)";
        list.appendChild(li);
        return;
      }
      for (const m of messages) {
        const li = document.createElement("li");
        li.innerHTML = `<div class="msg-head"></div><div class="msg-body"></div>`;
        li.querySelector(".msg-head").textContent = `${m.agent_id} · ${formatDate(m.created_at)}`;
        li.querySelector(".msg-body").textContent = m.body;
        list.appendChild(li);
      }
    } catch (e) {
      showBanner(`Messages: ${e.message}`);
    }
  }

  async function selectTicket(id) {
    selectedId = id;
    $$(".ticket-list button").forEach((b) => {
      b.classList.toggle("active", Number(b.dataset.id) === id);
    });
    $("#detail-placeholder").hidden = true;
    $("#detail-panel").hidden = false;
    try {
      const t = await api(`${API_TICKET}/tickets/${id}`);
      $("#detail-id").textContent = String(t.id);
      $("#detail-status").textContent = t.status;
      $("#detail-status").className = detailStatusPillClass(t.status);
      $("#detail-title").textContent = t.title;
      $("#detail-description").textContent = t.description || "—";
      $("#detail-dates").textContent = `Created ${formatDate(t.created_at)} · Updated ${formatDate(t.updated_at)}`;
      setResolveEnabledForStatus(t.status);
      $("#form-assign").reset();
      $("#form-message").reset();
      await Promise.all([loadMessages(id), loadAssignmentsForTicket(id)]);
    } catch (e) {
      showBanner(`Ticket: ${e.message}`);
    }
  }

  function openDialog(id) {
    const d = document.getElementById(id);
    if (d && typeof d.showModal === "function") d.showModal();
  }

  function closeDialog(id) {
    const d = document.getElementById(id);
    if (d) d.close();
  }

  $("#tab-customer").addEventListener("click", () => {
    applyTab("customer");
  });

  $("#tab-support").addEventListener("click", () => {
    applyTab("support");
    loadSummary();
  });

  $("#btn-open-create").addEventListener("click", () => {
    showBanner("");
    $("#form-create").reset();
    openDialog("modal-create");
  });

  $("#form-create").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const fd = new FormData(ev.target);
    const title = (fd.get("title") || "").toString().trim();
    const description = (fd.get("description") || "").toString();
    if (!title) {
      showBanner("Title is required.");
      return;
    }
    try {
      const created = await api(`${API_TICKET}/tickets`, {
        method: "POST",
        body: { title, description },
      });
      closeDialog("modal-create");
      showBanner("Ticket created.", false);
      await loadTickets();
      await loadSummary();
      await selectTicket(created.id);
    } catch (e) {
      showBanner(e.message);
    }
  });

  $$("#modal-create .btn-secondary, #modal-edit .btn-secondary").forEach((btn) => {
    btn.addEventListener("click", () => {
      const dialog = btn.closest("dialog");
      if (dialog) dialog.close();
    });
  });

  $("#btn-edit-ticket").addEventListener("click", async () => {
    if (selectedId == null) return;
    showBanner("");
    try {
      const t = await api(`${API_TICKET}/tickets/${selectedId}`);
      const f = $("#form-edit");
      f.elements.title.value = t.title;
      f.elements.description.value = t.description || "";
      f.elements.status.value = "";
      openDialog("modal-edit");
    } catch (e) {
      showBanner(e.message);
    }
  });

  $("#form-edit").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    if (selectedId == null) return;
    const fd = new FormData(ev.target);
    const title = (fd.get("title") || "").toString().trim();
    const description = (fd.get("description") || "").toString();
    const status = (fd.get("status") || "").toString();
    const body = {};
    if (title) body.title = title;
    if (description !== undefined) body.description = description;
    if (status) body.status = status;
    if (Object.keys(body).length === 0) {
      showBanner("Change at least one field.");
      return;
    }
    try {
      await api(`${API_TICKET}/tickets/${selectedId}`, { method: "PATCH", body });
      closeDialog("modal-edit");
      showBanner("Ticket updated.", false);
      await loadTickets();
      await loadSummary();
      await selectTicket(selectedId);
    } catch (e) {
      showBanner(e.message);
    }
  });

  $("#form-assign").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    if (selectedId == null) return;
    const fd = new FormData(ev.target);
    const agent_id = (fd.get("agent_id") || "").toString().trim();
    if (!agent_id) return;
    try {
      await api(`${API_SUPPORT}/tickets/${selectedId}/assign`, {
        method: "POST",
        body: { agent_id },
      });
      ev.target.reset();
      showBanner("Assigned.", false);
      await loadAssignmentsForTicket(selectedId);
      await loadSummary();
    } catch (e) {
      showBanner(e.message);
    }
  });

  $("#form-message").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    if (selectedId == null) return;
    const fd = new FormData(ev.target);
    const agent_id = (fd.get("agent_id") || "").toString().trim();
    const body = (fd.get("body") || "").toString().trim();
    if (!agent_id || !body) return;
    try {
      await api(`${API_SUPPORT}/tickets/${selectedId}/messages`, {
        method: "POST",
        body: { agent_id, body },
      });
      ev.target.reset();
      showBanner("Message sent.", false);
      await loadMessages(selectedId);
      await loadSummary();
    } catch (e) {
      showBanner(e.message);
    }
  });

  $("#btn-resolve-ticket").addEventListener("click", async () => {
    if (selectedId == null) return;
    if ($("#btn-resolve-ticket").disabled) return;
    if (!window.confirm("Resolve this ticket? Status will be set to resolved.")) return;
    try {
      await api(`${API_SUPPORT}/tickets/${selectedId}/resolve`, { method: "POST" });
      showBanner("Ticket resolved.", false);
      await loadTickets();
      await loadSummary();
      await selectTicket(selectedId);
    } catch (e) {
      showBanner(e.message);
    }
  });

  $("#btn-refresh-list-customer").addEventListener("click", () => {
    showBanner("");
    loadTickets();
  });

  $("#btn-refresh-list-support").addEventListener("click", () => {
    showBanner("");
    loadTickets();
  });

  $("#btn-refresh-summary").addEventListener("click", () => {
    showBanner("");
    loadSummary();
  });

  applyTab("customer");
  loadSummary();
  loadTickets();
})();
