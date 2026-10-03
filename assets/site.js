/* Island PT shared navigation behavior (desktop dropdowns + mobile drawer groups). */
(function () {
  'use strict';
  var items = Array.prototype.slice.call(document.querySelectorAll('.nav .has-submenu'));
  var lastPointer = '';
  var suppressFocusOpen = false;

  function setOpen(li, open) {
    var btn = li.querySelector('.submenu-trigger');
    li.setAttribute('data-open', open ? 'true' : 'false');
    if (btn) btn.setAttribute('aria-expanded', open ? 'true' : 'false');
  }
  function closeAll(except) {
    items.forEach(function (li) { if (li !== except) setOpen(li, false); });
  }

  items.forEach(function (li) {
    var btn = li.querySelector('.submenu-trigger');
    if (!btn || !li.querySelector('.submenu')) return;
    li.setAttribute('data-js', 'true');
    setOpen(li, false);

    li.addEventListener('pointerdown', function (e) { lastPointer = e.pointerType || ''; });
    // Desktop hover (mouse only, so a tap does not open and then immediately close).
    li.addEventListener('pointerenter', function (e) {
      if (e.pointerType === 'mouse') { closeAll(li); setOpen(li, true); }
    });
    li.addEventListener('pointerleave', function (e) {
      if (e.pointerType === 'mouse') setOpen(li, false);
    });
    // Keyboard focus opens; focus leaving the item closes.
    btn.addEventListener('focus', function () {
      if (suppressFocusOpen) { suppressFocusOpen = false; return; }
      var kb = true;
      try { kb = btn.matches(':focus-visible'); } catch (err) {}
      if (kb) { closeAll(li); setOpen(li, true); }
    });
    li.addEventListener('focusout', function (e) {
      if (!e.relatedTarget || !li.contains(e.relatedTarget)) setOpen(li, false);
    });
    // Tap / click / Enter / Space toggles. A mouse click on an already hovered menu keeps it open.
    btn.addEventListener('click', function (e) {
      e.preventDefault();
      var isOpen = li.getAttribute('data-open') === 'true';
      if (lastPointer === 'mouse' && isOpen) { lastPointer = ''; return; }
      lastPointer = '';
      closeAll(li);
      setOpen(li, !isOpen);
    });
    li.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && li.getAttribute('data-open') === 'true') {
        setOpen(li, false);
        suppressFocusOpen = true;
        btn.focus();
        suppressFocusOpen = false;
      }
    });
  });

  document.addEventListener('click', function (e) {
    items.forEach(function (li) { if (!li.contains(e.target)) setOpen(li, false); });
  });

  // Mobile drawer: start it just below the sticky header (whose height varies with the top bar),
  // so the first menu item is never hidden behind the header.
  var nav = document.querySelector('.nav');
  var drawer = document.getElementById('nav-drawer');
  var toggle = document.querySelector('.nav-toggle');
  function placeDrawer() {
    if (!nav || !drawer) return;
    var bottom = Math.max(0, Math.round(nav.getBoundingClientRect().bottom));
    drawer.style.top = bottom + 'px';
  }
  if (toggle) toggle.addEventListener('click', placeDrawer);
  window.addEventListener('resize', function () { if (drawer && drawer.dataset.open === 'true') placeDrawer(); });

  // Mobile drawer groups: buttons with aria-expanded controlling a sub-list.
  Array.prototype.forEach.call(document.querySelectorAll('.nav-drawer .drawer-toggle'), function (b) {
    var sub = document.getElementById(b.getAttribute('aria-controls'));
    if (!sub) return;
    sub.hidden = b.getAttribute('aria-expanded') !== 'true';
    b.addEventListener('click', function () {
      var open = b.getAttribute('aria-expanded') === 'true';
      b.setAttribute('aria-expanded', open ? 'false' : 'true');
      sub.hidden = open;
    });
  });
})();
