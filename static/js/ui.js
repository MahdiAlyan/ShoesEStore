/* ShoeStore UI layer — vanilla replacement for the old theme-bundled site.js.
 * No jQuery, no Bootstrap, no SweetAlert2. Classic script, one global
 * namespace (window.ShoeStore) because template inline scripts and cart.js
 * call it directly.
 *
 * Public API (signatures kept Swal-compatible so cart.js/dashboard.js work
 * unchanged until their own rewrite milestones):
 *   ShoeStore.toast(icon, title)
 *   ShoeStore.alert(icon, title, text)      -> Promise
 *   ShoeStore.confirm({icon,title,text,confirmText,cancelText})
 *                                           -> Promise<{isConfirmed}>
 *   ShoeStore.openDialog(el) / closeDialog(el)   (M3/M4 building block)
 * Also wires: [data-menu] dropdowns, .lang-switcher, store mobile nav,
 * dashboard sidebar, Django messages, and <form data-confirm> interception.
 */
(function () {
    "use strict";

    var ShoeStore = window.ShoeStore = window.ShoeStore || {};
    var CFG = window.SS || {};
    var I18N = CFG.i18n || {};

    // ---------- Toasts ----------

    var toastRegion = null;

    function ensureToastRegion() {
        if (!toastRegion) {
            toastRegion = document.createElement("div");
            toastRegion.className = "toast-region";
            toastRegion.setAttribute("role", "status");
            toastRegion.setAttribute("aria-live", "polite");
            document.body.appendChild(toastRegion);
        }
        return toastRegion;
    }

    function dismissToast(el) {
        if (!el.parentNode) { return; }
        el.classList.add("leaving");
        // Match --dur-fast; also covers reduced-motion (animationend still fires).
        el.addEventListener("animationend", function () { el.remove(); });
        setTimeout(function () { el.remove(); }, 400); // safety net
    }

    ShoeStore.toast = function (icon, title) {
        var kind = icon === "error" || icon === "danger" ? "error"
            : icon === "warning" ? "warning"
            : icon === "success" ? "success" : "info";
        var region = ensureToastRegion();
        var toast = document.createElement("div");
        toast.className = "toast toast-" + kind;
        var msg = document.createElement("div");
        msg.className = "toast-msg";
        msg.textContent = title || "";
        var close = document.createElement("button");
        close.type = "button";
        close.className = "toast-close";
        close.setAttribute("aria-label", I18N.close || "Close");
        close.textContent = "×";
        close.addEventListener("click", function () { dismissToast(toast); });
        toast.appendChild(msg);
        toast.appendChild(close);
        region.appendChild(toast);
        setTimeout(function () { dismissToast(toast); }, 3500);
    };

    // ---------- Dialogs (native <dialog>) ----------

    var supportsDialog = typeof HTMLDialogElement === "function";

    ShoeStore.openDialog = function (el) {
        if (supportsDialog && el.showModal) { el.showModal(); }
        else { el.setAttribute("open", ""); }
    };

    ShoeStore.closeDialog = function (el) {
        if (el.close) { el.close(); }
        else { el.removeAttribute("open"); }
    };

    var ICON_GLYPHS = { warning: "!", error: "×", success: "✓", info: "i" };

    /* Builds a one-shot <dialog class="dialog"> with title/text/buttons.
       All copy goes through textContent — never innerHTML — so server or
       API-provided strings cannot inject markup. */
    function showDialog(opts) {
        if (!supportsDialog) {
            // Ancient fallback: native prompts.
            var plain = (opts.title || "") + (opts.text ? "\n" + opts.text : "");
            if (opts.cancelText) {
                return Promise.resolve({ isConfirmed: window.confirm(plain) });
            }
            window.alert((opts.title || "") + (opts.text ? "\n" + opts.text : ""));
            return Promise.resolve({ isConfirmed: true });
        }
        return new Promise(function (resolve) {
            var dlg = document.createElement("dialog");
            dlg.className = "dialog";

            var body = document.createElement("div");
            body.className = "dialog-body";

            var icon = document.createElement("div");
            var kind = opts.icon in ICON_GLYPHS ? opts.icon : "info";
            icon.className = "dialog-icon dialog-icon-" + kind;
            icon.setAttribute("aria-hidden", "true");
            icon.textContent = ICON_GLYPHS[kind];
            body.appendChild(icon);

            var title = document.createElement("h2");
            title.className = "dialog-title";
            title.textContent = opts.title || "";
            body.appendChild(title);

            if (opts.text) {
                var text = document.createElement("p");
                text.className = "dialog-text";
                text.textContent = opts.text;
                body.appendChild(text);
            }
            dlg.appendChild(body);

            var actions = document.createElement("div");
            actions.className = "dialog-actions";

            var confirmed = false;

            if (opts.cancelText) {
                var cancelBtn = document.createElement("button");
                cancelBtn.type = "button";
                cancelBtn.className = "btn btn-light";
                cancelBtn.textContent = opts.cancelText;
                cancelBtn.addEventListener("click", function () { dlg.close(); });
                actions.appendChild(cancelBtn);
            }

            var okBtn = document.createElement("button");
            okBtn.type = "button";
            okBtn.className = opts.danger ? "btn btn-danger" : "btn btn-primary";
            okBtn.textContent = opts.confirmText || I18N.yes || "OK";
            okBtn.addEventListener("click", function () {
                confirmed = true;
                dlg.close();
            });
            actions.appendChild(okBtn);
            dlg.appendChild(actions);

            dlg.addEventListener("close", function () {
                dlg.remove();
                resolve({ isConfirmed: confirmed });
            });

            document.body.appendChild(dlg);
            dlg.showModal();
            okBtn.focus();
        });
    }

    ShoeStore.alert = function (icon, title, text) {
        return showDialog({ icon: icon || "info", title: title, text: text });
    };

    // Note: confirm() always renders its primary button in the danger style.
    // dashboard.js passes a legacy confirmColor for the status-change dialog;
    // it is ignored here and reconciled when dashboard.js is rewritten (M4).
    ShoeStore.confirm = function (opts) {
        opts = opts || {};
        return showDialog({
            icon: opts.icon || "warning",
            title: opts.title || I18N.confirm || "Are you sure?",
            text: opts.text || "",
            confirmText: opts.confirmText || I18N.yes || "OK",
            cancelText: opts.cancelText || I18N.cancel || "Cancel",
            danger: true,
        });
    };

    // ---------- Dropdown menus ----------
    // Markup: <div class="menu" data-menu><button data-menu-btn>…</button>
    //         <div class="menu-panel" hidden>…</div></div>

    function closeMenus(except) {
        document.querySelectorAll("[data-menu]").forEach(function (menu) {
            if (menu === except) { return; }
            var panel = menu.querySelector(".menu-panel");
            var btn = menu.querySelector("[data-menu-btn]");
            if (panel) { panel.hidden = true; }
            if (btn) { btn.setAttribute("aria-expanded", "false"); }
        });
    }

    document.addEventListener("click", function (e) {
        var btn = e.target.closest && e.target.closest("[data-menu-btn]");
        if (btn) {
            var menu = btn.closest("[data-menu]");
            var panel = menu && menu.querySelector(".menu-panel");
            if (panel) {
                var opening = panel.hidden;
                closeMenus(menu);
                panel.hidden = !opening;
                btn.setAttribute("aria-expanded", String(opening));
            }
            return;
        }
        // Clicks inside an open panel (e.g. the logout form) proceed normally;
        // any other click closes all menus.
        if (!e.target.closest || !e.target.closest(".menu-panel")) {
            closeMenus(null);
        }
    });

    document.addEventListener("keydown", function (e) {
        if (e.key === "Escape") { closeMenus(null); }
    });

    // ---------- Language switcher ----------
    // Vanilla replacement for the old jQuery/select2 binding: copy the
    // option's pre-translated URL into the hidden `next`, then POST.

    document.addEventListener("change", function (e) {
        var sel = e.target.closest && e.target.closest("select.lang-switcher");
        if (!sel) { return; }
        var opt = sel.options[sel.selectedIndex];
        var form = sel.form;
        if (opt && form && form.next) {
            form.next.value = opt.getAttribute("data-next") || form.next.value;
            form.submit();
        }
    });

    // ---------- Storefront mobile nav ----------

    function initMobileNav() {
        var toggle = document.getElementById("nav_toggle");
        var panel = document.getElementById("mobile_nav");
        if (!toggle || !panel) { return; }
        toggle.addEventListener("click", function () {
            var open = panel.hidden;
            panel.hidden = !open;
            toggle.setAttribute("aria-expanded", String(open));
        });
    }

    // ---------- Dashboard collapsible sidebar ----------
    // Desktop: icon rail persisted in localStorage. Mobile: off-canvas drawer.

    ShoeStore.initDashSidebar = function () {
        var layout = document.getElementById("dash_layout");
        var toggle = document.getElementById("dash_sidebar_toggle");
        if (!layout || !toggle) { return; }
        var backdrop = document.getElementById("dash_backdrop");
        var KEY = "ss_dash_collapsed";
        var DESKTOP = 992;

        function isDesktop() { return window.innerWidth >= DESKTOP; }

        function syncAria() {
            var expanded = isDesktop()
                ? !layout.classList.contains("dash-collapsed")
                : layout.classList.contains("dash-drawer-open");
            toggle.setAttribute("aria-expanded", String(expanded));
        }

        function closeDrawer() {
            layout.classList.remove("dash-drawer-open");
            syncAria();
        }

        try {
            if (localStorage.getItem(KEY) === "1") { layout.classList.add("dash-collapsed"); }
        } catch (e) { /* storage unavailable — default to expanded */ }
        syncAria();

        toggle.addEventListener("click", function () {
            if (isDesktop()) {
                var collapsed = layout.classList.toggle("dash-collapsed");
                try { localStorage.setItem(KEY, collapsed ? "1" : "0"); } catch (e) {}
            } else {
                layout.classList.toggle("dash-drawer-open");
            }
            syncAria();
        });

        if (backdrop) { backdrop.addEventListener("click", closeDrawer); }

        layout.querySelectorAll(".dash-nav-link").forEach(function (a) {
            a.addEventListener("click", function () {
                if (!isDesktop()) { closeDrawer(); }
            });
        });

        window.addEventListener("resize", function () {
            if (isDesktop()) { layout.classList.remove("dash-drawer-open"); }
            syncAria();
        });
    };

    // ---------- Django messages -> toasts ----------

    function showMessages() {
        (CFG.messages || []).forEach(function (m) {
            var tag = (m.level || "").toLowerCase();
            if (tag.indexOf("error") !== -1 || tag.indexOf("danger") !== -1) {
                ShoeStore.alert("error", I18N.error || "Error", m.text);
            } else if (tag.indexOf("warning") !== -1) {
                ShoeStore.toast("warning", m.text);
            } else if (tag.indexOf("success") !== -1) {
                ShoeStore.toast("success", m.text);
            } else {
                ShoeStore.toast("info", m.text);
            }
        });
    }

    // ---------- Confirm-before-submit ----------
    // Any <form data-confirm="Question?"> gets a dialog first (capture phase
    // so it wins over default submission; form.submit() bypasses it after).

    document.addEventListener("submit", function (e) {
        var form = e.target;
        if (!form || !form.getAttribute || form.getAttribute("data-confirm") === null) { return; }
        e.preventDefault();
        ShoeStore.confirm({
            title: form.getAttribute("data-confirm") || (I18N.confirm || "Are you sure?"),
            confirmText: form.getAttribute("data-confirm-text") || I18N.yes || "OK",
            cancelText: I18N.cancel || "Cancel",
        }).then(function (res) {
            if (res && res.isConfirmed) { form.submit(); }
        });
    }, true);

    // ---------- Catalog filter panel ----------
    // <details.filter-panel> is a collapsible sheet on mobile; on desktop the
    // sidebar is always expanded. Force it open at/above the desktop breakpoint.
    function initFilterPanels() {
        var panels = document.querySelectorAll(".filter-panel");
        if (!panels.length || !window.matchMedia) { return; }
        var mq = window.matchMedia("(min-width: 992px)");
        function sync() {
            if (mq.matches) {
                panels.forEach(function (p) { p.open = true; });
            }
        }
        sync();
        mq.addEventListener("change", sync);
    }

    // ---------- Boot ----------

    function ready(fn) {
        if (document.readyState !== "loading") { fn(); }
        else { document.addEventListener("DOMContentLoaded", fn); }
    }

    ready(function () {
        initMobileNav();
        initFilterPanels();
        ShoeStore.initDashSidebar();
        showMessages();
    });
})();
