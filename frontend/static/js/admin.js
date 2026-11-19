/* Silver Admin JS */
(function () {
    "use strict";
    document.querySelectorAll(".alert-close").forEach(function (b) {
        b.addEventListener("click", function () {
            var a = b.closest(".alert");
            if (a) a.remove();
        });
    });
    document.querySelectorAll(".messages-container .alert").forEach(function (a) {
        setTimeout(function () { a.remove(); }, 6000);
    });
})();