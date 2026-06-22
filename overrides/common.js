/****************************************************************************
 * voidfox - overrides/common.js
 *
 * Personal overrides applied to BOTH Firefox and Zen, layered on top of
 * Betterfox. These are appended after the upstream user.js, so any pref
 * here wins over Betterfox's value (Firefox keeps the last user_pref()).
 *
 * This is YOUR file. Betterfox's own files in ../upstream are auto-synced
 * and must never be edited by hand. Make every personal change here (or in
 * the per-browser files firefox.js / zen.js).
 *
 * References worth raiding for more prefs:
 *   - Common overrides:  https://github.com/yokoffing/Betterfox/wiki/Common-Overrides
 *   - Optional hardening: https://github.com/yokoffing/Betterfox/wiki/Optional-Hardening
 *   - Smooth scrolling:   ../upstream/firefox/Smoothfox.js
 ***************************************************************************/

/*== Session & startup =====================================================*/
// Reopen your previous windows and tabs on startup (Betterfox leaves this
// at the Firefox default of a fresh homepage). Comment out for a clean start.
user_pref("browser.startup.page", 3);

// Don't quit the whole window when you close the last tab.
user_pref("browser.tabs.closeWindowWithLastTab", false);

/*== Scrolling (from Smoothfox: "Natural Smooth Scrolling v3") ==============*
 * Best feel on 120Hz+ displays; comfortable everywhere. Pick ONE scrolling
 * style only. To switch styles, copy a different OPTION block from
 * ../upstream/firefox/Smoothfox.js and remove this one.
 * credit: AveYo - https://github.com/AveYo/fox
 *==========================================================================*/
user_pref("apz.overscroll.enabled", true);                                  // DEFAULT NON-LINUX
user_pref("general.smoothScroll", true);                                    // DEFAULT
user_pref("general.smoothScroll.msdPhysics.continuousMotionMaxDeltaMS", 12);
user_pref("general.smoothScroll.msdPhysics.enabled", true);
user_pref("general.smoothScroll.msdPhysics.motionBeginSpringConstant", 600);
user_pref("general.smoothScroll.msdPhysics.regularSpringConstant", 650);
user_pref("general.smoothScroll.msdPhysics.slowdownMinDeltaMS", 25);
user_pref("general.smoothScroll.msdPhysics.slowdownMinDeltaRatio", "2");
user_pref("general.smoothScroll.msdPhysics.slowdownSpringConstant", 250);
user_pref("general.smoothScroll.currentVelocityWeighting", "1");
user_pref("general.smoothScroll.stopDecelerationWeighting", "1");
user_pref("mousewheel.default.delta_multiplier_y", 300);                    // 250-400 to taste

/*== Quality-of-life ========================================================*/
// Open PDFs inline in the built-in viewer rather than downloading them.
user_pref("browser.download.open_pdf_attachments_inline", true);

// Show the full URL including https:// (Betterfox trims it). Uncomment if you
// prefer to see the scheme at all times.
// user_pref("browser.urlbar.trimURLs", false);

/*== Optional: relax some Betterfox hardening (uncomment to enable) ==========*
 * Betterfox is privacy-first and disables several conveniences. Re-enable the
 * ones you miss by uncommenting below.
 *==========================================================================*/
// Search suggestions in the address bar:
// user_pref("browser.search.suggest.enabled", true);
// user_pref("browser.urlbar.suggest.searches", true);

// Browsing-history suggestions in the address bar:
// user_pref("browser.urlbar.suggest.history", true);

// Form autofill / saved form history:
// user_pref("browser.formfill.enable", true);

// Keep the disk cache (Betterfox disables it for privacy; enabling speeds up
// repeat visits at the cost of writing browsing data to disk):
// user_pref("browser.cache.disk.enable", true);
