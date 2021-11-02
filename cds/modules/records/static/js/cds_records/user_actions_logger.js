var userActionsLogger = (function () {
  function pageView(url) {
    if (url) {
      try {
        var r = new XMLHttpRequest();
        r.open("GET", url, true);
        r.send();
      } catch (e) {
        console.error(e);
      }
    }
  }

  return {
    pageView: pageView,
  };
})();
