String.prototype.endsWith = function(suffix) {
    return this.indexOf(suffix, this.length - suffix.length) !== -1
}

var saveUrl = function(){
  var dfd = $.Deferred()
  $.ajax({
    url: '../cgi-bin/dataset_url',
    data: {
      url: scraperwiki.readSettings().target.url
    }
  }).done(function(currentUrl){
    dfd.resolve(currentUrl)
  }).fail(function(jqXHR, textStatus, errorThrown){
    dfd.reject('Dataset could not be saved', jqXHR.status + ' ' + jqXHR.statusText)
  })
  return dfd.promise()
}

var readUrl = function(){
  var dfd = $.Deferred()
  $.ajax({
    url: '../cgi-bin/dataset_url'
  }).done(function(currentUrl){
    dfd.resolve(currentUrl)
  }).fail(function(){
    dfd.resolve('')
  })
  return dfd.promise()
}

var pipInstall = function(){
  var dfd = $.Deferred()
  scraperwiki.exec('pip install --user --upgrade -r ~/tool/requirements.txt; echo "Exit Code: $?"').done(function(stdout){
    if($.trim(stdout).endsWith('Exit Code: 0')){
      dfd.resolve()
    } else {
      // Something went wrong with pip install!
      // There will be a traceback in stdout.
      dfd.reject('Python dependencies could not be installed', $.trim(stdout))
    }
  })
  return dfd.promise()
}

var showEndpoints = function(){
  $.ajax({
    url: '../cgi-bin/odata',
    dataType: 'xml'
  }).done(function(xmlDom){
    $('#feeds').show()
    $('#loading').hide()
    $(xmlDom).find('collection').each(function(){
      var table = $(this).find('title').text()
      var url = $(this).attr('href')
      $('#feeds').append('<div><h2>' + table + '</h2><input type="text" value="' + url + '"></div>')
    })
  })
}

$(function(){
  readUrl().done(function(currentUrl){
    if($.trim(currentUrl) == ''){
      $('#loading span').html('Installing OData endpoint&hellip;')
      $.when(saveUrl(), pipInstall()).then(function(firstResolution, secondResolution){
        showEndpoints()
      }, function(firstRejection, secondRejection){
        var $details = $('<pre>').html('<b>' + firstRejection + '</b><br/><br/>' + secondRejection)
        $('#error').show().append($details)
        $('#loading').hide()
      })
    } else {
      showEndpoints()
    }
  })

  $(document).on('focus', '#feeds input', function(e){
    e.preventDefault()
    this.select()
  }).on('mouseup', '#feeds input', function(e){
    e.preventDefault()
  })

})
