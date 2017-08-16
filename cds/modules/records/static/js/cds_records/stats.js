function getStats(record) {
  var record_id = record.recid;
  var defaultConfig = {
    legend: {
      visible: false,
    },
    tooltip: {
      enabled: false
    }
  };
  // Fetch the pageviews of the specific record
  $.ajax({
    type: 'GET',
    url: '/api/stats/' + record_id + '/pageviews',
    headers: {
      'Content-Type': 'application/json'
    }
  })
  .success(function(data) {
    new inveniographs.LineGraph(data, 'pageviews', defaultConfig).render();
  });

  // Fetch the downloads of the specific record
  $.ajax({
    type: 'GET',
    url: '/api/stats/' + record_id + '/downloads',
    headers: {
      'Content-Type': 'application/json'
    }
  })
  .success(function(data) {
    new inveniographs.LineGraph(data, 'downloads', defaultConfig).render();
  });

}
