/*
 * Island PT analytics (GA4). OFF until a Measurement ID is pasted below.
 *
 * TO TURN ON: paste the GA4 web-stream Measurement ID (looks like G-XXXXXXXXXX)
 * between the quotes on the GA4_MEASUREMENT_ID line, commit, and deploy.
 * Nothing loads from Google and no data is sent while it is empty.
 *
 * Events sent once enabled:
 *   generate_lead  GoHighLevel form submit (detected from the GHL iframe's
 *                  postMessage), or a thank-you page view as the fallback.
 *                  Deduplicated so one submission counts once.
 *   sign_up        Newsletter form (formsubmit.co) submit. Its redirect to the
 *                  thank-you page is NOT counted as a lead.
 *   booking_click  Any link to /booking or *.janeapp.com
 *   phone_click    Any tel: link
 *   text_click     Any sms: link
 * Each click event carries link_url, link_text and link_location
 * (header, menu, sticky_bar, footer, top_bar or content).
 * Debug: add ?ipt_debug=1 to a URL to log events to the console.
 */
(function () {
  'use strict';

  var GA4_MEASUREMENT_ID = ''; // <-- paste the GA4 Measurement ID here, e.g. 'G-ABC123XYZ9'

  var enabled = /^G-[A-Z0-9]{4,}$/.test(GA4_MEASUREMENT_ID);
  var debug = /[?&]ipt_debug=1/.test(location.search);
  var LEAD_FLAG = 'ipt_lead_tracked';
  var NEWSLETTER_FLAG = 'ipt_newsletter_submitted';

  window.dataLayer = window.dataLayer || [];
  function gtag() { window.dataLayer.push(arguments); }

  if (enabled) {
    var s = document.createElement('script');
    s.async = true;
    s.src = 'https://www.googletagmanager.com/gtag/js?id=' + encodeURIComponent(GA4_MEASUREMENT_ID);
    document.head.appendChild(s);
    gtag('js', new Date());
    gtag('config', GA4_MEASUREMENT_ID);
  }

  function track(name, params) {
    params = params || {};
    if (debug && window.console) console.info('[ipt analytics' + (enabled ? '' : ' (disabled)') + ']', name, params);
    if (enabled) gtag('event', name, params);
  }
  window.iptTrack = track;

  function store(key, val) {
    try { if (val === null) sessionStorage.removeItem(key); else sessionStorage.setItem(key, val); } catch (e) {}
  }
  function read(key) {
    try { return sessionStorage.getItem(key); } catch (e) { return null; }
  }

  function region(el) {
    if (el.closest('.call-bar')) return 'sticky_bar';
    if (el.closest('.nav-drawer')) return 'menu';
    if (el.closest('.nav')) return 'header';
    if (el.closest('.top-bar')) return 'top_bar';
    if (el.closest('footer')) return 'footer';
    return 'content';
  }
  function linkText(a) {
    return (a.textContent || a.getAttribute('aria-label') || '').replace(/\s+/g, ' ').trim().slice(0, 100);
  }

  // Clicks on booking, phone and text links (capture phase so it runs before navigation).
  document.addEventListener('click', function (e) {
    var a = e.target && e.target.closest ? e.target.closest('a[href]') : null;
    if (!a) return;
    var href = a.getAttribute('href') || '';
    var params = { link_url: href, link_text: linkText(a), link_location: region(a) };
    if (/^tel:/i.test(href)) return track('phone_click', params);
    if (/^sms:/i.test(href)) return track('text_click', params);
    var path = '';
    try { var u = new URL(href, location.href); path = u.host === location.host ? u.pathname : u.host; } catch (err) {}
    if (/^\/booking\/?$/.test(path) || /(^|\.)janeapp\.com$/i.test(path)) return track('booking_click', params);
  }, true);

  // GoHighLevel form submit: after a successful submit the GHL iframe posts
  // ['set-sticky-contacts', <form storage key>, <iframe id>, ...] to this page.
  window.addEventListener('message', function (e) {
    if (!/(^|\.)(leadconnectorhq\.com|msgsndr\.com|gohighlevel\.com)$/i.test((e.origin || '').replace(/^https?:\/\//, ''))) return;
    var d = e.data;
    if (!Array.isArray(d) || d[0] !== 'set-sticky-contacts' || !d[1] || d[1] === '_ud') return;
    var frame = null;
    var frames = document.querySelectorAll('iframe[data-form-id]');
    for (var i = 0; i < frames.length; i++) if (frames[i].contentWindow === e.source) frame = frames[i];
    var formId = frame ? frame.getAttribute('data-form-id') : String(d[2] || '');
    if (frame && frame.dataset.iptLead === '1') return;
    if (frame) frame.dataset.iptLead = '1';
    store(LEAD_FLAG, '1');
    track('generate_lead', {
      method: 'ghl_form',
      form_id: formId,
      form_name: frame ? (frame.getAttribute('data-form-name') || frame.title || '') : '',
      page_path: location.pathname
    });
  });

  // Newsletter (formsubmit.co) submit.
  document.addEventListener('submit', function (e) {
    var f = e.target;
    if (f && f.action && /formsubmit\.co/i.test(f.action)) {
      store(NEWSLETTER_FLAG, '1');
      track('sign_up', { method: 'newsletter', page_path: location.pathname });
    }
  }, true);

  // Thank-you page fallback: count a lead only if it was not already counted above.
  if (/^\/thank-you(\.html)?\/?$/.test(location.pathname) && window.top === window.self) {
    if (read(LEAD_FLAG)) { store(LEAD_FLAG, null); }
    else if (read(NEWSLETTER_FLAG)) { store(NEWSLETTER_FLAG, null); }
    else { track('generate_lead', { method: 'thank_you_page', page_path: location.pathname }); }
  }
})();
