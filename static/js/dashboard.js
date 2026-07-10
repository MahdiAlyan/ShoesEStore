/* Dashboard: AJAX order status changes. */
(function () {
    "use strict";
    function csrf() { return window.CSRF_TOKEN || ""; }

    var STATUS_MSG = {
        ok: "Status updated.",
        fail: "Could not update status.",
    };

    function notify(message, type) {
        var el = document.getElementById("dash-alerts");
        if (!el) {
            el = document.createElement("div");
            el.id = "dash-alerts";
            el.style.cssText = "position:fixed;top:1rem;left:50%;transform:translateX(-50%);z-index:1080;max-width:520px;width:90%";
            document.body.appendChild(el);
        }
        var wrap = document.createElement("div");
        wrap.className = "alert alert-" + (type || "primary") + " alert-dismissible fade show shadow-sm";
        wrap.textContent = message;
        var b = document.createElement("button");
        b.type = "button"; b.className = "btn-close"; b.setAttribute("data-bs-dismiss", "alert");
        wrap.appendChild(b);
        el.appendChild(wrap);
        setTimeout(function () { wrap.remove(); }, 4000);
    }

    document.addEventListener("change", function (e) {
        var sel = e.target.closest && e.target.closest(".status-select");
        if (!sel) return;
        var id = sel.dataset.orderId;
        var newStatus = sel.value;
        var prev = sel.dataset.prev || sel.options[0].value;
        fetch("/api/admin/orders/" + id + "/status/", {
            method: "PATCH",
            headers: { "Content-Type": "application/json", "X-CSRFToken": csrf() },
            credentials: "same-origin",
            body: JSON.stringify({ status: newStatus }),
        }).then(function (r) {
            return r.json().then(function (data) { return { ok: r.ok, data: data }; });
        }).then(function (res) {
            if (res.ok) {
                sel.dataset.prev = newStatus;
                var badge = document.querySelector('[data-status-badge="' + id + '"]');
                if (badge) {
                    badge.className = "badge status-" + res.data.status;
                    badge.textContent = res.data.status_display;
                }
                notify(sel.dataset.okMsg || STATUS_MSG.ok, "success");
            } else {
                notify(res.data.detail || STATUS_MSG.fail, "danger");
                if (sel.dataset.prev) sel.value = sel.dataset.prev;  // revert on invalid transition
            }
        });
    });

    // Seed prev value for revert.
    document.querySelectorAll(".status-select").forEach(function (s) {
        s.dataset.prev = s.value;
    });
})();
