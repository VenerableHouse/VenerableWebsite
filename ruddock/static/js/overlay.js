/**
 * This library is used to create very basic overlays with a dark transparent
 * background and a window in front. By itself, the overlayWindow element
 * doesn't do anything except appear, but you can use it as a starting point
 * for other things. Clicking on the background, outside the window,
 * automatically closes the overlay.
 *
 * Usage:
 * - This script assumes jQuery is already being used.
 * - Use the overlay.css file
 */


/*
 * This function creates the overlay, which consists of a transparent
 * background and an overlay window.
 */
function showOverlay() {
    // Check if an overlay already exists.
    if ($("#overlay").length)
        return;

    // Create the overlay. The overlayBackground and overlayWindow are child
    // elements of the overlay div.
    var overlay = document.createElement("div");
    overlay.setAttribute("id", "overlay");

    var overlayBackground = document.createElement("div");
    overlayBackground.setAttribute("id", "overlayBackground");

    var overlayWindow = document.createElement("div");
    overlayWindow.setAttribute("id", "overlayWindow");

    // We want clicking on the background to close the overlay.
    overlayBackground.setAttribute("onclick", "closeOverlay()");

    centerOverlay();

    // Append the overlay elements to each other.
    $(overlay).append(overlayBackground, overlayWindow);
    $(document.body).append(overlay);
}

/*
 * This function closes the overlay.
 */
function closeOverlay() {
    $("#overlay").remove();
}

/*
 * Centers overlayWindow. This should be called whenever the size of the
 * overlay window changes.
 */
function centerOverlay() {
    var width = $("#overlayWindow").width();
    var height = $("#overlayWindow").height();

    // We position the element so the top left corner is in the middle of
    // the page. Then we move it up/left by half its height/width to actually
    // center it.
    $("#overlayWindow").css({
        "top": "50%",
        "left": "50%",
        "margin-top": "-" + (height / 2) + "px",
        "margin-left": "-" + (width / 2) + "px"
    });
}
