/****************************************************************************
 * voidfox - overrides/zen.js
 *
 * Overrides applied to ZEN ONLY (not Firefox). Loaded after common.js, so
 * anything here wins over both Betterfox's zen/user.js and common.js for Zen.
 *
 * NOTE ON SCROLLING: Zen ships its own scrolling prefs. The Smoothfox block
 * in common.js will override them, which is usually what you want. If Zen's
 * native scrolling feels better to you, reset the general.smoothScroll* and
 * mousewheel* prefs here to Zen's defaults instead. See the SMOOTHFOX note in
 * ../upstream/zen/user.js for the exact Zen values.
 ***************************************************************************/

// Example: keep Zen's compact/feature toggles, leave the rest to common.js.

// Show the Enhanced Tracking Protection shield in the URL bar:
// user_pref("zen.urlbar.show-protections-icon", true);
