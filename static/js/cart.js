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

    function alertArea() {
        var el = document.getElementById("ss-alerts");
        if (!el) {
            el = document.createElement("div");
            el.id = "ss-alerts";
            el.style.cssText = "position:fixed;top:1rem;left:50%;transform:translateX(-50%);z-index:1080;max-width:520px;width:90%";
            document.body.appendChild(el);
        }
        return el;
    }

    function notify(message, type) {
        var wrap = document.createElement("div");
        wrap.className = "alert alert-" + (type || "primary") + " alert-dismissible fade show shadow-sm";
        wrap.setAttribute("role", "alert");
        wrap.textContent = message;
        var btn = document.createElement("button");
        btn.type = "button";
        btn.className = "btn-close";
        btn.setAttribute("data-bs-dismiss", "alert");
        wrap.appendChild(btn);
        alertArea().appendChild(wrap);
        setTimeout(function () { wrap.classList.remove("show"); setTimeout(function () { wrap.remove(); }, 300); }, 4000);
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

    document.addEventListener("change", function (e) {
        var input = e.target.closest && e.target.closest(".cart-qty");
        if (!input) return;
        var id = input.dataset.itemId;
        var q = parseInt(input.value || "1", 10);
        api("/api/cart/items/" + id + "/", "PATCH", { quantity: q }).then(function (r) {
            if (r.ok) { refreshCart(r.data); }
            else { notify(r.data.warning || r.data.detail || "Update failed.", "danger"); if (r.data.item_count !== undefined) refreshCart(r.data); }
        });
    });

    document.addEventListener("click", function (e) {
        var btn = e.target.closest && e.target.closest(".cart-remove");
        if (!btn) return;
        var id = btn.dataset.itemId;
        api("/api/cart/items/" + id + "/", "DELETE", null).then(function (r) {
            if (r.ok) {
                var row = document.querySelector('tr[data-row-id="' + id + '"]');
                if (row) row.remove();
                refreshCart(r.data);
            }
        });
    });
})();
