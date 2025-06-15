document.addEventListener("DOMContentLoaded", function () {
  var eventImages = document.querySelectorAll(".event-card-image");

  eventImages.forEach(function (image) {
    var originalSrc = image.src;

    var fullsizeSrc = getHighResImageUrl(originalSrc);

    image.addEventListener("mouseenter", function () {
      if (fullsizeSrc && image.src !== fullsizeSrc) {
        image.src = fullsizeSrc;
      }
    });

    image.addEventListener("mouseleave", function () {
      image.src = originalSrc;
    });
  });

  function getHighResImageUrl(thumbnailUrl) {
    if (thumbnailUrl.includes("/thumbnails/")) {
      return thumbnailUrl.replace("/thumbnails/", "/fullsize/");
    }

    if (thumbnailUrl.includes("_thumb.")) {
      return thumbnailUrl.replace("_thumb.", ".");
    }

    return thumbnailUrl;
  }
});
