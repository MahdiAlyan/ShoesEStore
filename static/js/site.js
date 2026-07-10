/* ShoeStore site-wide UI layer (M5).
 *
 * - Initializes select2 on every <select> (storefront + dashboard), RTL-aware,
 *   so mobile browsers never render the native picker.
 * - Exposes ShoeStore.toast / .alert / .confirm on top of SweetAlert2.
 * - Converts server-rendered Django messages into SweetAlert2 feedback.
 *
 * All vendor libs (jQuery, select2, SweetAlert2) ship locally in Metronic's
 * plugins.bundle.js — no CDN, works offline / on PythonAnywhere.
 */
(function () {
    "use strict";

    var $ = window.jQuery;
    var Swal = window.Swal || window.Sweetalert2;
    var CFG = window.SS || {};
    var I18N = CFG.i18n || {};
    var RTL = !!CFG.rtl;

    // ---------- SweetAlert2 helpers ----------
    var ShoeStore = window.ShoeStore || {};

    ShoeStore.toast = function (icon, title) {
        if (!Swal) { return; }
        Swal.fire({
            toast: true,
            position: RTL ? "top-start" : "top-end",
            icon: icon || "success",
            title: title || "",
            showConfirmButton: false,
            timer: 3000,
            timerProgressBar: true,
        });
    };

    ShoeStore.alert = function (icon, title, text) {
        if (!Swal) { window.alert((title || "") + (text ? "\n" + text : "")); return Promise.resolve(); }
        return Swal.fire({ icon: icon || "info", title: title || "", text: text || "" });
    };

    ShoeStore.confirm = function (opts) {
        opts = opts || {};
        if (!Swal) {
            return Promise.resolve({ isConfirmed: window.confirm(opts.title || I18N.confirm || "Are you sure?") });
        }
        return Swal.fire({
            icon: opts.icon || "warning",
            title: opts.title || I18N.confirm || "Are you sure?",
            text: opts.text || "",
            showCancelButton: true,
            confirmButtonText: opts.confirmText || I18N.yes || "OK",
            cancelButtonText: opts.cancelText || I18N.cancel || "Cancel",
            confirmButtonColor: opts.confirmColor || "#d33",
            reverseButtons: RTL,
        });
    };

    window.ShoeStore = ShoeStore;

    // ---------- select2 on all selects ----------
    ShoeStore.initSelect2 = function (root) {
        if (!$ || !$.fn || !$.fn.select2) { return; }
        var scope = root ? $(root) : $(document);
        scope.find("select").each(function () {
            var $s = $(this);
            if ($s.data("no-select2") !== undefined || $s.attr("data-no-select2") !== undefined) { return; }
            if ($s.hasClass("select2-hidden-accessible")) { return; } // already initialized
            // 'resolve' sizes full-width form-selects to their column and small
            // w-auto selects (language, status) to their rendered width.
            var opts = {
                dir: RTL ? "rtl" : "ltr",
                width: "resolve",
                // Hide the search box for short lists (language, status, filters).
                minimumResultsForSearch: $s.data("search") === false ? Infinity : 8,
            };
            // Keep the dropdown inside its modal so it isn't clipped / mis-focused.
            var $modal = $s.closest(".modal");
            if ($modal.length) { opts.dropdownParent = $modal; }
            $s.select2(opts);
        });
    };

    // ---------- Language switcher ----------
    // select2 fires `change` through jQuery, so a native listener/inline onchange
    // would not run. Bind via jQuery so switching works with select2 active.
    if ($) {
        $(document).on("change", "select.lang-switcher", function () {
            var opt = this.options[this.selectedIndex];
            var form = this.form;
            if (opt && form && form.next) {
                form.next.value = opt.getAttribute("data-next") || form.next.value;
                form.submit();
            }
        });
    }

    // ---------- Dashboard collapsible sidebar ----------
    // Desktop: toggle an icon-only rail (state persisted in localStorage).
    // Mobile (<992px): toggle an off-canvas drawer with a backdrop.
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

        // Restore the persisted desktop collapsed state.
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

        // Tapping a nav link on mobile closes the drawer.
        layout.querySelectorAll(".dash-nav-link").forEach(function (a) {
            a.addEventListener("click", function () {
                if (!isDesktop()) { closeDrawer(); }
            });
        });

        // Crossing back to desktop clears any open drawer state.
        window.addEventListener("resize", function () {
            if (isDesktop()) { layout.classList.remove("dash-drawer-open"); }
            syncAria();
        });
    };

    // ---------- Django messages -> SweetAlert2 ----------
    function showMessages() {
        var msgs = CFG.messages || [];
        msgs.forEach(function (m) {
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

    function ready(fn) {
        if (document.readyState !== "loading") { fn(); }
        else { document.addEventListener("DOMContentLoaded", fn); }
    }

    // ---------- Generic confirm-before-submit (M5) ----------
    // Any <form data-confirm="Question?"> is confirmed via SweetAlert2 first.
    document.addEventListener("submit", function (e) {
        var form = e.target;
        if (!form || !form.getAttribute || form.getAttribute("data-confirm") === null) { return; }
        e.preventDefault();
        ShoeStore.confirm({
            title: form.getAttribute("data-confirm") || (I18N.confirm || "Are you sure?"),
            confirmText: form.getAttribute("data-confirm-text") || I18N.yes || "OK",
            cancelText: I18N.cancel || "Cancel",
        }).then(function (res) {
            if (res && res.isConfirmed) { form.submit(); }  // form.submit() skips this handler
        });
    }, true);

    ready(function () {
        ShoeStore.initSelect2(document);
        ShoeStore.initDashSidebar();
        showMessages();
    });
})();
