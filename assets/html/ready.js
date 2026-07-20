/* ============================================================================
   ready.js — FAIL-CLOSED render gate, shared by every page (do not edit or
   inline per shot; pages load it with <script src="ready.js"></script> and the
   skill vendors ONE copy per design dir, next to set.css).

   Adds body.ready only when EVERYTHING a correct render needs is present:
     - document.fonts.ready resolved;
     - every <img> decoded (complete + naturalWidth > 0);
     - every copy of the raw (img.screen, plus a breakout <img> showing the
       same raw) matches the set's --raw-w contract — frame sizing and
       breakout placement math assume that width, and a mismatched capture
       desyncs the geometry silently while every pixel still "loads". A genai
       piece composited with its own src is exempt;
     - the headline font face actually loaded (checked against the .verb
       element's computed family, so a swapped CJK face is verified too);
     - a CJK headline is not silently resolving to the Latin face (a missing
       <html lang> or :lang() rule would render tofu / a thin system fallback);
     - the stylesheet applied (--canvas-w resolves) and the body background
       resolved to a real colour (a malformed --bg turns the canvas
       transparent without any other error);
     - the headline fits its box (the canvas is overflow:hidden, so an
       unbreakable overlong verb would otherwise be clipped silently).

   On any failure it adds body.render-error and records a semicolon-joined
   cause in data-render-error instead — a broken asset never passes silently.
   The gate is deliberately ONE-SHOT: it runs once (after fonts.ready and the
   image decodes) and the verdict is final for that page load. Pages are
   static per render, so nothing legitimately changes afterwards; a resource
   arriving late can only turn a fail into a false FAIL (the safe direction) —
   re-open the page to re-run the gate.
   set.css additionally paints a full-canvas NOT-READY banner until body.ready
   exists, so a screenshot captured without waiting on the gate (e.g. the
   timer-based fallback renderer) is unmissable in QA.
   ========================================================================= */
(async () => {
  const fails = [];
  try { await document.fonts.ready; }
  catch (e) { fails.push("fonts.ready rejected"); }
  for (const img of document.images) {
    try { await img.decode(); } catch (e) { /* fall through to the check */ }
    if (!img.complete || img.naturalWidth === 0)
      fails.push("image failed: " + (img.getAttribute("src") || "(no src)"));
  }

  const bodyStyle = getComputedStyle(document.body);

  // RAW-WIDTH CONTRACT (see set.css --raw-w): the screen raw must be exactly
  // --raw-w wide, or the frame sizing and --screen-scale-derived breakout
  // placement are silently wrong. A breakout <img> is checked only when it
  // shows the SAME raw as a screen (the CSS-crop case, whose offset math
  // assumes --raw-w); a genai piece composited with its own src is exempt —
  // it is sized by the `.breakout img.piece` rule, not the raw-offset math.
  // Same-raw detection compares RESOLVED URLs (img.src), so `raw/x.png` and
  // `./raw/x.png` spellings of one file can't dodge the check.
  const rawW = Math.round(parseFloat(bodyStyle.getPropertyValue("--raw-w")) || 0);
  if (rawW) {
    const screens = [...document.querySelectorAll("img.screen")];
    const screenSrcs = new Set(screens.map((s) => s.src));
    const rawCopies = screens.concat(
      [...document.querySelectorAll(".breakout img")].filter((img) =>
        screenSrcs.has(img.src)));
    for (const img of rawCopies) {
      if (img.naturalWidth > 0 && img.naturalWidth !== rawW)
        fails.push("raw width " + img.naturalWidth + "px != --raw-w " + rawW +
          "px: " + (img.getAttribute("src") || "(no src)") +
          " (set --raw-w to the real width and recompute --screen-scale, or fix the raw)");
    }
  }

  // Localized CJK pages swap the headline family via a :lang() rule, so read
  // the .verb element's actual first family rather than hardcoding Inter.
  const verb = document.querySelector(".verb");
  let family = "Inter Display";
  if (verb) {
    const first = getComputedStyle(verb).fontFamily.split(",")[0].trim()
      .replace(/^["']|["']$/g, "");
    if (first) family = first;
  }
  if (!document.fonts.check('900 1em "' + family + '"'))
    fails.push("headline font not loaded: " + family);

  // CJK GUARD: CJK headline text whose computed face is still the Latin
  // headline font means the page is missing its <html lang> attribute or the
  // set-wide :lang() CJK @font-face rule.
  const headline = document.querySelector(".headline");
  const headText = headline ? headline.textContent : "";
  const hasCJK =
    /[぀-ヿ㐀-䶿一-鿿豈-﫿가-힯]/.test(headText);
  if (hasCJK && /^Inter/i.test(family))
    fails.push("CJK headline but the computed face is " + family +
      " — missing <html lang> or the :lang() CJK font rule in set.css");

  if (!bodyStyle.getPropertyValue("--canvas-w").trim())
    fails.push("stylesheet not applied (--canvas-w empty)");

  // BACKGROUND: a malformed --bg (e.g. "E31837" without the #) is a legal
  // custom-property token but invalid at computed-value time — the brand fill
  // silently becomes transparent. A background-image (a user-approved
  // gradient direction) counts as painted, so only fail when BOTH resolve to
  // nothing.
  const bg = bodyStyle.backgroundColor;
  const bgImage = bodyStyle.backgroundImage;
  if ((!bg || bg === "transparent" || bg === "rgba(0, 0, 0, 0)") &&
      (!bgImage || bgImage === "none"))
    fails.push("body background did not resolve (malformed --bg in set.css?)");

  // HEADLINE FIT: the canvas is overflow:hidden, so an overlong unbreakable
  // verb/descriptor would be clipped with no other signal.
  for (const el of document.querySelectorAll(".verb, .desc")) {
    if (el.scrollWidth > el.clientWidth + 1)
      fails.push("headline overflows (" + el.className + ": " + el.scrollWidth +
        "px > " + el.clientWidth +
        "px) — shrink the set-wide type scale or reword, never per shot");
  }

  if (fails.length === 0) {
    document.body.classList.add("ready");
  } else {
    document.body.dataset.renderError = fails.join("; ");
    document.body.classList.add("render-error");
  }
})();
