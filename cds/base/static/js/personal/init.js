require(
  [
    'jquery',
    'js/personal/main',
    'flight/lib/compose',
    'flight/lib/registry',
    'flight/lib/advice',
    'flight/lib/logger',
    'flight/lib/debug',
  ],

  function($, initializePersonal) {
    // Init personal
    initializePersonal();
  }
);
