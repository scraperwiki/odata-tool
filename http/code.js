String.prototype.endsWith = function(suffix) {
    return this.indexOf(suffix, this.length - suffix.length) !== -1
}

var showEndpoints = function(datasetUrl) {
  $('#loading span').html('Reading OData endpoint&hellip;')



  scraperwiki.sql.meta().done(function(metadata){
    $('#feeds').show()
    $('#loading').hide()

    $.each(metadata.table, function(name) {
      var odataUrl = datasetUrl + "/cgi-bin/odata/"
      $('#feeds').append('<div><h2>' + name + '</h2><input type="text" value="' + odataUrl + name + '"></div>')
    })
  }).fail(function(jqXHR){
      $('#error').show().children('span').html('OData endpoint failed to respond:<br/>' + jqXHR.status + ' ' + jqXHR.statusText)
      $('#loading').hide()
  })
}

$(function(){
  datasetUrl = scraperwiki.readSettings().target.url
  showEndpoints(datasetUrl)

  $(document).on('focus', '#feeds input', function(e){
    e.preventDefault()
    this.select()
  }).on('mouseup', '#feeds input', function(e){
    e.preventDefault()
  })
})
