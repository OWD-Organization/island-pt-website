/* =================================================================
   DISTINCT DESIGNS CONSTRUCTION: SITE INTERACTIONS
   Vanilla JS only. No dependencies.
   ================================================================= */

(function () {
  "use strict";

  var prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ---------------------------------------------------------------
     Footer year
     --------------------------------------------------------------- */
  var yearEl = document.getElementById("year");
  if (yearEl) yearEl.textContent = new Date().getFullYear();

  /* ---------------------------------------------------------------
     Sticky nav shadow/border on scroll
     --------------------------------------------------------------- */
  var siteNav = document.getElementById("site-nav");
  var stickyCta = document.getElementById("sticky-cta");
  var hero = document.querySelector(".hero");

  function handleScrollState() {
    var scrolled = window.scrollY > 12;
    if (siteNav) siteNav.classList.toggle("is-scrolled", scrolled);

    if (stickyCta && hero) {
      var heroBottom = hero.getBoundingClientRect().bottom;
      stickyCta.classList.toggle("is-visible", heroBottom < 0);
    }
  }

  window.addEventListener("scroll", handleScrollState, { passive: true });
  handleScrollState();

  /* ---------------------------------------------------------------
     Mobile nav toggle
     --------------------------------------------------------------- */
  var navToggle = document.getElementById("nav-toggle");
  var mobileNav = document.getElementById("site-nav__mobile");

    function setMobileDropdown(id, open) {
      var panel = document.getElementById(id);
      if (!panel) return;
      var root = panel.closest(".nav-dropdown");
      var button = root && root.querySelector(".nav-dropdown__toggle");
      if (!root || !button) return;
      button.setAttribute("aria-expanded", open ? "true" : "false");
      root.classList.toggle("is-open", open);
    }

    if (navToggle && mobileNav) {
      var toggleLabel = navToggle.querySelector(".site-nav__toggle-label");

      function setMenuOpen(open) {
        navToggle.setAttribute("aria-expanded", open ? "true" : "false");
        navToggle.setAttribute("aria-label", open ? "Close menu" : "Open menu");
        if (toggleLabel) toggleLabel.textContent = open ? "Close" : "Menu";
        mobileNav.classList.toggle("is-open", open);
      }

      navToggle.addEventListener("click", function () {
        var isOpen = navToggle.getAttribute("aria-expanded") === "true";
        setMenuOpen(!isOpen);
        if (!isOpen) {
          setMobileDropdown("homes-menu-mobile", true);
        }
      });

      mobileNav.querySelectorAll("a").forEach(function (link) {
        link.addEventListener("click", function () {
          setMenuOpen(false);
        });
      });
    }

  /* ---------------------------------------------------------------
     Header dropdowns (Services, Service Areas)
     Desktop: hover and keyboard focus open the menu. Mobile: the button
     toggles it. Each menu exists twice (header links + hamburger).
     The 1280px cutoff matches the CSS that reveals the desktop link row.
     --------------------------------------------------------------- */
  var servicesDesktop = window.matchMedia("(min-width: 1280px)");

  document.querySelectorAll(".nav-dropdown").forEach(function (root) {
    var button = root.querySelector(".nav-dropdown__toggle");
    var panel = root.querySelector(".nav-dropdown__panel");
    if (!button || !panel) return;

    function openMenu() {
      button.setAttribute("aria-expanded", "true");
      root.classList.add("is-open");
    }

    function closeMenu() {
      button.setAttribute("aria-expanded", "false");
      root.classList.remove("is-open");
    }

    root.addEventListener("mouseenter", function () {
      if (servicesDesktop.matches) openMenu();
    });
    root.addEventListener("mouseleave", function () {
      if (servicesDesktop.matches) closeMenu();
    });
    root.addEventListener("focusin", function () {
      if (servicesDesktop.matches) openMenu();
    });
    root.addEventListener("focusout", function (event) {
      if (!servicesDesktop.matches) return;
      if (!root.contains(event.relatedTarget)) closeMenu();
    });
    button.addEventListener("click", function () {
      if (servicesDesktop.matches) return;
      if (button.getAttribute("aria-expanded") === "true") closeMenu();
      else openMenu();
    });
    root.addEventListener("keydown", function (event) {
      if (event.key === "Escape") {
        closeMenu();
        button.focus();
      }
    });
  });

  /* ---------------------------------------------------------------
     Scroll-triggered reveal animations
     --------------------------------------------------------------- */
  var revealEls = document.querySelectorAll(".reveal");

  if (prefersReducedMotion || !("IntersectionObserver" in window)) {
    revealEls.forEach(function (el) { el.classList.add("is-visible"); });
  } else {
    var revealObserver = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            revealObserver.unobserve(entry.target);
          }
        });
      },
      // threshold 0 so elements taller than the viewport still trigger
      { threshold: 0, rootMargin: "0px 0px -80px 0px" }
    );
    revealEls.forEach(function (el) { revealObserver.observe(el); });
  }

  /* ---------------------------------------------------------------
     FAQ accordion (multi-open, accessible)
     --------------------------------------------------------------- */
  var accordionTriggers = document.querySelectorAll(".accordion__trigger");

  accordionTriggers.forEach(function (trigger) {
    var panel = document.getElementById(trigger.getAttribute("aria-controls"));
    if (!panel) return;

    trigger.addEventListener("click", function () {
      var isOpen = trigger.getAttribute("aria-expanded") === "true";
      trigger.setAttribute("aria-expanded", String(!isOpen));

      if (isOpen) {
        panel.style.maxHeight = null;
      } else {
        panel.style.maxHeight = panel.scrollHeight + "px";
      }
    });
  });

  /* ---------------------------------------------------------------
     Project lightbox
     Tiles are <button>s; clicking one opens the photograph in a native
     <dialog>. showModal() gives focus trapping, Esc-to-close and an inert
     background for free, so none of that is hand-rolled here.
     --------------------------------------------------------------- */
  var lightbox = document.getElementById("lightbox");
  var lightboxImg = document.getElementById("lightbox-img");
  var lightboxCaption = document.getElementById("lightbox-caption");
  var lightboxClose = document.getElementById("lightbox-close");
  var tiles = document.querySelectorAll("button.project-tile, button.gallery-item");

  if (lightbox && lightboxImg && typeof lightbox.showModal === "function") {
    tiles.forEach(function (tile) {
      tile.addEventListener("click", function () {
        var img = tile.querySelector("img");
        var label = tile.querySelector(".project-tile__label");
        if (!img) return;

        lightboxImg.src = img.currentSrc || img.src;
        lightboxImg.alt = img.alt;
        if (lightboxCaption) {
          var caption = tile.getAttribute("data-caption");
          lightboxCaption.textContent = caption || (label ? label.textContent : img.alt);
        }
        lightbox.showModal();
      });
    });

    if (lightboxClose) {
      lightboxClose.addEventListener("click", function () { lightbox.close(); });
    }

    // Click outside the figure closes it. The dialog fills the backdrop area,
    // so compare against the figure's box rather than the event target.
    lightbox.addEventListener("click", function (event) {
      var fig = lightbox.querySelector(".lightbox__figure");
      if (!fig) return;
      var r = fig.getBoundingClientRect();
      var inside = event.clientX >= r.left && event.clientX <= r.right &&
                   event.clientY >= r.top && event.clientY <= r.bottom;
      if (!inside && event.target !== lightboxClose) lightbox.close();
    });

    // Release the (potentially large) image once closed
    lightbox.addEventListener("close", function () {
      lightboxImg.removeAttribute("src");
      lightboxImg.alt = "";
    });
  } else if (lightbox) {
    // No <dialog> support: leave the tiles inert rather than half-working.
    tiles.forEach(function (tile) { tile.disabled = true; tile.style.cursor = "default"; });
  }

  /* ---------------------------------------------------------------
     Forms on this variation never leave the browser. No webhook,
     no FormSubmit, no GoHighLevel. A status note explains that.
     --------------------------------------------------------------- */
  document.querySelectorAll("form").forEach(function (form) {
    form.setAttribute("action", "#");
    form.addEventListener("submit", function (event) {
      event.preventDefault();
      var note = form.querySelector("[data-form-note]");
      if (!form.checkValidity()) {
        if (note) note.textContent = "Please complete the required fields. This preview still will not send anything.";
        form.reportValidity();
        return;
      }
      if (note) {
        note.textContent = "TODO: this preview does not submit the form. Nothing was sent. Call or text (808) 201-6922, or book a free discovery call.";
      }
    });
  });
})();
