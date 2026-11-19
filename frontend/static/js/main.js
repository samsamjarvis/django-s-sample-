/* Silver — landing JS */
(function () {
    "use strict";

    document.addEventListener("DOMContentLoaded", function () {

        // ─── دکمه بستن alertها ───
        document.addEventListener("click", function (e) {
            var closeBtn = e.target.closest(".alert-close");
            if (closeBtn) {
                var alert = closeBtn.closest(".alert");
                if (alert) {
                    alert.style.opacity = "0";
                    setTimeout(function () { alert.remove(); }, 200);
                }
            }
        });

        // ─── auto-dismiss messages بعد از ۵ ثانیه ───
        document.querySelectorAll(".messages-container .alert").forEach(function (a) {
            setTimeout(function () {
                if (a.parentElement) {
                    a.style.transition = "opacity 300ms";
                    a.style.opacity = "0";
                    setTimeout(function () { a.remove(); }, 300);
                }
            }, 5000);
        });

        // ─── Mobile menu (hamburger) ───
        var menuBtn = document.querySelector("[data-mobile-menu-toggle]");
        var mobileNav = document.querySelector("[data-mobile-menu]");

        if (menuBtn && mobileNav) {
            menuBtn.addEventListener("click", function (e) {
                e.preventDefault();
                var isOpen = mobileNav.classList.toggle("is-open");
                menuBtn.setAttribute("aria-expanded", isOpen ? "true" : "false");
            });

            // بستن با کلیک بیرون از منو
            document.addEventListener("click", function (e) {
                if (!mobileNav.classList.contains("is-open")) return;
                if (mobileNav.contains(e.target) || menuBtn.contains(e.target)) return;
                mobileNav.classList.remove("is-open");
                menuBtn.setAttribute("aria-expanded", "false");
            });

            // بستن با کلید Escape
            document.addEventListener("keydown", function (e) {
                if (e.key === "Escape" && mobileNav.classList.contains("is-open")) {
                    mobileNav.classList.remove("is-open");
                    menuBtn.setAttribute("aria-expanded", "false");
                }
            });

            // بستن هنگام کلیک روی لینک‌های منو
            mobileNav.querySelectorAll("a").forEach(function (link) {
                link.addEventListener("click", function () {
                    mobileNav.classList.remove("is-open");
                    menuBtn.setAttribute("aria-expanded", "false");
                });
            });
        } else {
            console.warn("[menu] .mobile-menu-btn or .mobile-nav not found in HTML");
        }

        // ─── Product gallery thumbs ───
        var galleryThumbs = document.querySelectorAll(".product-gallery__thumbs img");
        var galleryMain = document.querySelector(".product-gallery__main img");
        if (galleryMain && galleryThumbs.length) {
            galleryThumbs.forEach(function (thumb) {
                thumb.addEventListener("click", function () {
                    galleryMain.src = thumb.src;
                    galleryThumbs.forEach(function (t) { t.classList.remove("active"); });
                    thumb.classList.add("active");
                });
            });
        }

        // ─── Address radio click فعال‌سازی ───
        document.querySelectorAll(".address-radio").forEach(function (label) {
            label.addEventListener("click", function () {
                document.querySelectorAll(".address-radio").forEach(function (l) {
                    l.classList.remove("is-selected");
                });
                label.classList.add("is-selected");
                var input = label.querySelector("input[type=radio]");
                if (input) input.checked = true;
            });
        });

        // ─── Cart: submit خودکار فرم تغییر تعداد ───
        document.querySelectorAll("[data-cart-qty]").forEach(function (input) {
            input.addEventListener("change", function () {
                var form = input.closest("form");
                if (form) form.submit();
            });
        });

        // ─── Hero carousel navigation (placeholder — فاز ۶) ───
        var heroPrev = document.querySelector(".hero-nav.prev");
        var heroNext = document.querySelector(".hero-nav.next");
        if (heroPrev) heroPrev.addEventListener("click", function () {});
        if (heroNext) heroNext.addEventListener("click", function () {});

        // ─── Scroll lock برای anchor links ───
        document.addEventListener("click", function (e) {
            var a = e.target.closest('a[href^="#"]');
            if (!a) return;
            var id = a.getAttribute("href").slice(1);
            if (!id) return;
            var target = document.getElementById(id);
            if (!target) return;
            e.preventDefault();
            target.scrollIntoView({ behavior: "smooth", block: "start" });
        });

    });
})();