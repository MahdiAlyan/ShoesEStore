/* ShoeStore API helper — single fetch wrapper for all AJAX (cart, dashboard).
 * Classic script (no build step); everything hangs off window.ShoeStore.
 * API endpoints live under /api/ and are never locale-prefixed.
 */
(function () {
    "use strict";

    var ShoeStore = window.ShoeStore = window.ShoeStore || {};

    /**
     * ShoeStore.api(url, method, body) -> Promise<{ok, status, data}>
     * Sends/expects JSON, attaches CSRF, never rejects on HTTP errors —
     * callers branch on `ok` and read bilingual messages from `data`.
     */
    ShoeStore.api = function (url, method, body) {
        return fetch(url, {
            method: method || "GET",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": window.CSRF_TOKEN || "",
                "X-Requested-With": "XMLHttpRequest",
            },
            credentials: "same-origin",
            body: body ? JSON.stringify(body) : undefined,
        }).then(function (resp) {
            return resp.json().catch(function () { return {}; }).then(function (data) {
                return { ok: resp.ok, status: resp.status, data: data };
            });
        });
    };

    /** Translated UI string from the server-rendered window.SS bridge. */
    ShoeStore.i18n = function (key, fallback) {
        return (window.SS && window.SS.i18n && window.SS.i18n[key]) || fallback;
    };
})();
