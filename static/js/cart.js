/* ShoeStore cart client. Handles add-to-cart (product detail), cart page
   quantity/remove, navbar badge, and bilingual alerts. */
(function () {
    "use strict";

    function csrf() { return window.CSRF_TOKEN || ""; }

    function api(url, method, body) {
        return fetch(url, {
            method: method,
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": csrf(),
                "X-Requested-With": "XMLHttpRequest",
            },
            credentials: "same-origin",
            body: body ? JSON.stringify(body) : undefined,
        }).then(function (resp) {
            return resp.json().catch(function () { return {}; }).then(function (data) {
                return { ok: resp.ok, status: resp.status, data: data };
            });
        });
    }

    // Feedback goes through ShoeStore (defined in ui.js). Errors are a dialog,
    // everything else a corner toast. Falls back to a plain alert if absent.
    function i18n(key, fallback) {
        return (window.SS && window.SS.i18n && window.SS.i18n[key]) || fallback;
    }
    function notify(message, type) {
        var kind = type === "danger" ? "error"
            : type === "warning" ? "warning"
            : type === "success" ? "success" : "info";
        if (window.ShoeStore) {
            if (kind === "error") { window.ShoeStore.alert("error", i18n("error", "Error"), message); }
            else { window.ShoeStore.toast(kind, message); }
        } else {
            window.alert(message);
        }
    }

    function updateBadge(count) {
        var badge = document.getElementById("cart-badge");
        if (!badge) return;
        badge.textContent = count;
        badge.classList.toggle("d-none", !count);
    }

    // ---- Product detail: bind Add to cart ----
    window.ShoeStoreBindAddToCart = function (picker, addBtn) {
        var url = picker.getAttribute("data-add-url");
        addBtn.addEventListener("click", function () {
            var sel = picker.getSelection();
            if (!sel.variantId) { notify(addBtn.dataset.selectMsg || "Please select a color and size.", "warning"); return; }
            addBtn.disabled = true;
            api(url, "POST", { variant_id: sel.variantId, quantity: sel.quantity }).then(function (r) {
                addBtn.disabled = false;
                if (r.ok) {
                    updateBadge(r.data.item_count);
                    notify(addBtn.dataset.addedMsg || "Added to cart.", "success");
                } else {
                    notify(r.data.warning || r.data.detail || "Could not add to cart.", "danger");
                    if (typeof r.data.item_count === "number") updateBadge(r.data.item_count);
                }
            });
        });
    };

    // ---- Cart page: quantity + remove ----
    function money(v) { return "$" + Number(v).toFixed(2); }

    function refreshCart(data) {
        updateBadge(data.item_count);
        var sub = document.getElementById("cart-subtotal");
        if (sub) sub.textContent = money(data.subtotal);
        (data.items || []).forEach(function (it) {
            var cell = document.querySelector('.line-total[data-item-id="' + it.id + '"]');
            if (cell) cell.textContent = money(it.line_total);
            var qty = document.querySelector('.cart-qty[data-item-id="' + it.id + '"]');
            if (qty && String(it.quantity) !== qty.value) qty.value = it.quantity;
        });
        if (!data.item_count) { window.location.reload(); }
    }

    // ---- Cart page: -/+ quantity steppers (M4.5) ----
    // Clamp between 1 and available stock, then reuse the change-based PATCH.
    document.addEventListener("click", function (e) {
        var stepBtn = e.target.closest && e.target.closest(".qty-step");
        if (!stepBtn) return;
        var id = stepBtn.dataset.itemId;
        var input = document.querySelector('.cart-qty[data-item-id="' + id + '"]');
        if (!input) return;
        var step = parseInt(stepBtn.dataset.step, 10) || 0;
        var max = parseInt(input.getAttribute("max") || "0", 10);
        var val = (parseInt(input.value || "1", 10) || 1) + step;
        if (val < 1) val = 1;
        if (max && val > max) val = max;
        if (String(val) === input.value) return;
        input.value = val;
        input.dispatchEvent(new Event("change", { bubbles: true }));
    });

    document.addEventListener("change", function (e) {
        var input = e.target.closest && e.target.closest(".cart-qty");
        if (!input) return;
        var id = input.dataset.itemId;
        var q = parseInt(input.value || "1", 10);
        if (q < 1) q = 1;
        api("/api/cart/items/" + id + "/", "PATCH", { quantity: q }).then(function (r) {
            if (r.ok) { refreshCart(r.data); }
            else { notify(r.data.warning || r.data.detail || "Update failed.", "danger"); if (r.data.item_count !== undefined) refreshCart(r.data); }
        });
    });

    function doRemove(id) {
        api("/api/cart/items/" + id + "/", "DELETE", null).then(function (r) {
            if (r.ok) {
                var row = document.querySelector('tr[data-row-id="' + id + '"]');
                if (row) row.remove();
                refreshCart(r.data);
            } else {
                notify(r.data.detail || i18n("error", "Error"), "danger");
            }
        });
    }

    document.addEventListener("click", function (e) {
        var btn = e.target.closest && e.target.closest(".cart-remove");
        if (!btn) return;
        var id = btn.dataset.itemId;
        // Confirm removal via ShoeStore.confirm (ui.js).
        if (window.ShoeStore && window.ShoeStore.confirm) {
            window.ShoeStore.confirm({
                title: i18n("removeTitle", "Remove this item?"),
                text: i18n("removeText", ""),
                confirmText: i18n("removeConfirm", "Yes, remove"),
                cancelText: i18n("cancel", "Cancel"),
            }).then(function (res) { if (res && res.isConfirmed) doRemove(id); });
        } else {
            doRemove(id);
        }
    });
})();
