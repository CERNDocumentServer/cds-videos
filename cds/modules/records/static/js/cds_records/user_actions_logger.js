var userActionsLogger = (function() {

    function pageView(url) {
        if (url) {
            var r = new XMLHttpRequest();
            r.open('GET', url, true);
            r.send();
        }
    }

    return {
        pageView: pageView
    }

})();
