/* Dashboard: AJAX order status changes (M5: SweetAlert2 confirm + feedback). */
(function () {
    "use strict";
    function csrf() { return window.CSRF_TOKEN || ""; }

    function i18n(key, fallback) {
        return (window.SS && window.SS.i18n && window.SS.i18n[key]) || fallback;
    }
    function notify(message, type) {
        var kind = type === "danger" ? "error" : (type === "success" ? "success" : "info");
        if (window.ShoeStore) {
            if (kind === "error") { window.ShoeStore.alert("error", i18n("error", "Error"), message); }
            else { window.ShoeStore.toast(kind, message); }
        } else {
            window.alert(message);
        }
    }

    function applyStatus(sel) {
        var id = sel.dataset.orderId;
        var newStatus = sel.value;
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
                notify(sel.dataset.okMsg || i18n("success", "Status updated."), "success");
            } else {
                notify(res.data.detail || i18n("error", "Could not update status."), "danger");
                if (sel.dataset.prev) sel.value = sel.dataset.prev;  // revert on invalid transition
            }
        });
    }

    function onStatusChange(sel) {
        var prev = sel.dataset.prev || sel.options[0].value;
        if (sel.value === prev) return;
        function revert() {
            sel.value = prev;
            if (window.jQuery) { window.jQuery(sel).trigger("change.select2"); }  // sync select2 UI
        }
        // Confirm the change first (M5).
        if (window.ShoeStore && window.ShoeStore.confirm) {
            window.ShoeStore.confirm({
                icon: "question",
                title: i18n("statusChangeTitle", "Change order status?"),
                confirmText: i18n("statusChangeConfirm", "Yes, change it"),
                cancelText: i18n("cancel", "Cancel"),
                confirmColor: "#009ef7",
            }).then(function (res) {
                if (res && res.isConfirmed) { applyStatus(sel); }
                else { revert(); }
            });
        } else {
            applyStatus(sel);
        }
    }

    // Bind via jQuery so select2's change (jQuery-triggered) reaches us; fall back
    // to native delegation if jQuery is unavailable.
    if (window.jQuery) {
        window.jQuery(document).on("change", ".status-select", function () { onStatusChange(this); });
    } else {
        document.addEventListener("change", function (e) {
            var sel = e.target.closest && e.target.closest(".status-select");
            if (sel) onStatusChange(sel);
        });
    }

    // Seed prev value for revert.
    document.querySelectorAll(".status-select").forEach(function (s) {
        s.dataset.prev = s.value;
    });
})();
