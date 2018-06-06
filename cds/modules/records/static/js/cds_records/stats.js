function getStats(record) {
  const defaultConfig = {
    legend: {
      visible: false,
    },
    tooltip: {
      enabled: false,
    },
  };

  fetchRecordData(record.recid, 'pageviews', defaultConfig); // fetch the pageviews for a record
  fetchRecordData(record.recid, 'downloads', defaultConfig); // fetch the downloads for a record
}

function fetchRecordData(recordId, category, defaultConfig) {
  $.ajax({
    type: 'GET',
    url: '/api/stats/' + recordId + '/' + category,
    headers: {
      'Content-Type': 'application/json'
    }
  })
  .success(function(data) {
    $('#' + category + '-loading-spinner').hide();
    new inveniographs.LineGraph(data, category, defaultConfig).render();
  })
  .error(function(error) {
    $('#' + category + '-loading-spinner').hide();
    $('#' + category + '-error-message').show();
  });
}
