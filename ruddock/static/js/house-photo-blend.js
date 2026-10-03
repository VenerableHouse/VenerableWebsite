/* Easter egg: the house photo drifts into its silly-poses variant.
 *
 * The transition itself is a pre-rendered FILM interpolation (see tools/), shipped
 * as two short clips -- forward and reverse. All this file does is decide when to
 * play them and how fast.
 *
 * Progressive enhancement: the page ships a plain <img>, and nothing here runs
 * unless a clip actually loads. If it doesn't, the homepage is exactly what it
 * was before.
 */
(function () {
  'use strict';

  var script = document.currentScript;
  if (!script) return;

  var IDLE_MS = 60000;      // wall clock since load, foreground or background
  var LEAD_MS = 20000;      // start fetching this far ahead of the ambient trigger
  var SLOW_SECONDS = 15;    // the ambient drift
  var FAST_SECONDS = 0.7;   // the hover "do it now"

  var container = document.getElementById('house-photo');
  if (!container) return;
  var still = container.querySelector('.house-photo__still');
  if (!still) return;

  var sources = {
    a: script.getAttribute('data-still-a'),
    b: script.getAttribute('data-still-b')
  };
  if (!sources.a || !sources.b) return;

  var reduceMotion = window.matchMedia &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  var state = 'a';
  var desiredState = 'a';
  var desiredSeconds = FAST_SECONDS;
  var busy = false;
  var waitingForMedia = false;
  var armed = false;
  var autoTimer = null;
  var videos = {};

  function makeVideo(webm, mp4) {
    var v = document.createElement('video');
    v.className = 'house-photo__video';
    v.muted = true;
    v.defaultMuted = true;
    v.playsInline = true;
    v.setAttribute('playsinline', '');   // iOS needs the attribute, not just the property
    v.setAttribute('aria-hidden', 'true');
    v.loop = false;
    // Nothing is fetched until arm() flips this and calls load(), so a visitor who
    // never lingers pays nothing for the clips.
    v.preload = 'none';
    [[webm, 'video/webm'], [mp4, 'video/mp4']].forEach(function (pair) {
      if (!pair[0]) return;
      var s = document.createElement('source');
      s.src = pair[0];
      s.type = pair[1];
      v.appendChild(s);
    });
    container.appendChild(v);
    return v;
  }

  function arm() {
    if (armed) return;
    armed = true;
    Object.keys(videos).forEach(function (key) {
      videos[key].preload = 'auto';
      videos[key].load();
    });
  }

  function swapStill(to) {
    still.src = sources[to];
    state = to;
  }

  /* Plays one of the two pre-rendered clips. The pacing curve is already baked
   * into the frames, so speed is just playbackRate -- the same clip serves both
   * the slow ambient drift and the fast hover. */
  function run(direction, seconds) {
    var video = videos[direction];
    var target = direction === 'forward' ? 'b' : 'a';
    if (!video || busy) return;

    var duration = video.duration;
    if (!duration || !isFinite(duration)) {
      // On the first hover the clips may not have metadata yet. Keep the still
      // visible while they load, then start the requested transition instead of
      // abruptly swapping the photo.
      if (waitingForMedia) return;
      waitingForMedia = true;
      function startWhenReady() {
        video.removeEventListener('loadedmetadata', startWhenReady);
        waitingForMedia = false;
        if (desiredState !== state) transitionTo(desiredState, desiredSeconds);
      }
      video.addEventListener('loadedmetadata', startWhenReady);
      arm();
      return;
    }

    busy = true;
    // Browsers only guarantee roughly 0.0625x-16x; outside that, playback is
    // silently clamped or refused.
    video.playbackRate = Math.min(16, Math.max(0.0625, duration / seconds));

    function finish() {
      video.removeEventListener('ended', finish);
      video.removeEventListener('error', finish);
      swapStill(target);
      video.classList.remove('is-visible');
      busy = false;
      if (desiredState !== state) transitionTo(desiredState, desiredSeconds);
    }
    video.addEventListener('ended', finish);
    video.addEventListener('error', finish);

    try {
      video.currentTime = 0;
    } catch (err) { /* not seekable yet; it starts from 0 anyway */ }

    var playing = video.play();
    video.classList.add('is-visible');
    if (playing && playing.catch) {
      playing.catch(finish);   // autoplay blocked: fall back to a plain swap
    }
  }

  function transitionTo(to, seconds) {
    desiredState = to;
    desiredSeconds = seconds;
    if (busy || state === to) return;
    if (reduceMotion) {
      swapStill(to);
      return;
    }
    run(to === 'b' ? 'forward' : 'reverse', seconds);
  }

  function cancelAuto() {
    if (autoTimer !== null) {
      clearTimeout(autoTimer);
      autoTimer = null;
    }
  }

  // --- triggers -------------------------------------------------------------

  // Only react when a non-touch pointer enters the photo, not when it moves
  // between the container and its still image. The video layers ignore pointer
  // events.
  container.addEventListener('pointerover', function (event) {
    if (event.pointerType === 'touch') return;
    if (event.relatedTarget && container.contains(event.relatedTarget)) return;
    cancelAuto();
    transitionTo('b', FAST_SECONDS);
  });
  container.addEventListener('pointerout', function (event) {
    if (event.pointerType === 'touch') return;
    if (event.relatedTarget && container.contains(event.relatedTarget)) return;
    transitionTo('a', FAST_SECONDS);
  });
  container.addEventListener('pointerup', function (event) {
    if (event.pointerType !== 'touch') return;
    cancelAuto();
    transitionTo(desiredState === 'a' ? 'b' : 'a', FAST_SECONDS);
  });

  // --- boot -----------------------------------------------------------------

  if (reduceMotion) return;   // no clips fetched at all; hover still swaps

  videos.forward = makeVideo(script.getAttribute('data-video-webm'),
                             script.getAttribute('data-video-mp4'));
  videos.reverse = makeVideo(script.getAttribute('data-video-reverse-webm'),
                             script.getAttribute('data-video-reverse-mp4'));

  // Fetch on intent, so someone who reaches for the photo gets a real animation.
  container.addEventListener('pointerenter', arm, {once: true});
  container.addEventListener('pointerdown', arm, {once: true});

  // Wall-clock since navigation, so a backgrounded tab is not a special case:
  // timer callbacks throttle in the background but elapsed time does not, and if
  // it fires while hidden the visitor simply returns to the blended photo.
  var elapsed = performance.now();
  setTimeout(arm, Math.max(0, IDLE_MS - LEAD_MS - elapsed));
  autoTimer = setTimeout(function () {
    autoTimer = null;
    if (state === 'a') transitionTo('b', SLOW_SECONDS);
  }, Math.max(0, IDLE_MS - elapsed));
})();
