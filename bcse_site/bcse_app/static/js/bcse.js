$(function (){

  $("#copyright_year").html(new Date().getFullYear());

  $(".datepicker:not(.reservation_date):not(.availability)").datepicker({
    dateFormat: "MM dd, yy",
    changeMonth: true,
    changeYear: true
  });

  $(".timepicker").timepicker({
    timeFormat: 'hh:mm p',
    interval: 15,
    minTime: '12:00am',
    maxTime: '11:45pm',
    //defaultTime: '08:00am',
    startTime: '12:00am',
    dynamic: false,
    dropdown: true,
    scrollbar: true
  });

  //generic filter form submit handler
  $('form.filter_form').on('submit', function(e){
    e.preventDefault();
    var form = $(this);
    var form_id = $(this).attr('id');
    //the container to place the search results
    var result_container = $(this).closest('.content').find('.search_results');
    const queryString = $(form).serialize();
    var url = $(form).attr('action')+'?'+queryString;
    console.log(queryString);
    $.ajax({
      type: $(form).attr('method'),
      url: url,
      beforeSend: function(){
        $(result_container).html('');
        $('#spinner').show();
      },
      complete: function(){
        $('#spinner').hide();
      },
      success: function(data){
        $('#spinner').hide();
        if(data['success'] = true) {
          $(result_container).html(data['html']);
          if(form_id == 'workshop_filter_form') {
            bindRegistrationSubmit();
          }
          else if (form_id == 'availability_filter_form') {
            bindCalendarNavigation();
          }
          else if (form_id == 'baxter_box_filter_form') {
            bindBaxterBoxTabs();
            bindModalOpen();
          }
          bindPagination();
          bindDeleteAction();
          bindCancelAction();
          bindModalOpen();
          bindWarningAction();
          bindUseAjax();
        }
        else{
          displayErrorDialog();
        }
        return false;
      },
      error: function(xhr, ajaxOptions, thrownError){
        displayErrorDialog();
      },
    });
  });

  //submit search form on input change
  $('form.filter_form :input').on('change', function(){
    auto_submit_search($(this).closest('form'));
  });

  $('form.filter_form #clear').on('click', function(e){
    $('form.filter_form')[0].reset();
    var autocomplete_elements = $('form.filter_form :input[data-autocomplete-light-function=select2]');
    var select2_elements = $('form.filter_form .select2');
    if($(autocomplete_elements).length) {
      $(autocomplete_elements).val('');
      $(autocomplete_elements).trigger('change');
    }
    else if(select2_elements.length) {
      $(select2_elements).val(null).trigger('change');
    }
    else {
      var form = $(this).closest('form');
      $(form).submit();
    }
  });

  $('#filter_toggle label').click(function(){
    $('#filter_toggle label').toggle();
    $('#filter_content').toggle();
  });

  //disable Enter key press
  $("form.filter_form").bind("keypress", function(e) {
    if (e.keyCode == 13) {
      return false;
    }
  });

  $('ul.messages').children().delay(30000).fadeOut('slow');
  $('ul.messages i').click(function(){
    $('ul.messages').children().hide();
  });

  $('div#slides').slick({
    dots: false,
    autoplay: true,
    autoplaySpeed: 5000,
    infinite: true,
    speed: 500,
    fade: true,
    cssEase: 'linear',
    adaptiveHeight: true,
  });

  $('.banner_text.play').click(function() {
    $(this).hide();
    var video = $(this).closest('.banner').find('.banner_text.video');
    $(video).show()
    var iframe = $(video).find('iframe#banner_video');
    $(iframe).attr('src', $(iframe).attr('src') + '?autoplay=1');
    $('div#slides').slick('slickPause');

  });

  var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
  var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
    return new bootstrap.Tooltip(tooltipTriggerEl)
  });

  bindPagination();
  bindRegistrationSubmit();
  bindDeleteAction();
  bindCancelAction();
  bindWarningAction();
  bindUseAjax();

});

var timeout = null;

function bindRegistrationSubmit(){
  $('.registration_submit').unbind('click');
  $('.registration_submit').on('click', function(e){
    e.preventDefault();
    var workshop_registration_container = $(this).closest('.workshop_registration');
    var form = $(this).closest('form');
    $.ajax({
      type: $(form).attr('method'),
      url: $(form).attr('action'),
      data: $(form).serialize(),
      success: function(data){
        if (data['success'] = true) {
          if (data['html']) {
            $(workshop_registration_container).html(data['html']);
            if (data['admin_message']) {
              bootbox.alert({
                title: 'Registration Confirmation',
                message: data['admin_message'],
                closeButton: false
              });
            }
            bindRegistrationSubmit();
            bindDeleteAction();
            bindCancelAction();
          }
          else {
            displayErrorDialog();
          }
        }
        else {
          displayErrorDialog();
        }
        return false;
      },
      error: function(xhr, ajaxOptions, thrownError){
        displayErrorDialog();
      },
    });
  });
}

function bindDeleteAction() {
  $('.delete.action').unbind('click');
  $('.delete.action').on('click', function(e){
    e.preventDefault();
    var link = $(this).data('href');
    var title = $(this).data('title');

    bootbox.confirm({ title: 'Confirm',
                      message: "<p>Do you want to delete "+title+"?</p>",
                      buttons: {
                        confirm: {
                            label: 'Delete',
                            className: 'btn btn-small btn-danger'
                        },
                        cancel: {
                            label: 'Cancel',
                            className: 'btn btn-small'
                        }
                      },
                      closeButton: false,
                      callback: function(result){
                        if (result == true) {
                          window.location = link;
                        }
                      },
                    });
  });
}

function bindCancelAction() {
  $('.cancel.action').unbind('click');
  $('.cancel.action').on('click', function(e){
    e.preventDefault();
    var link = $(this).data('href');
    var title = $(this).data('title');

    bootbox.confirm({ title: 'Confirm',
                      message: "<p>Do you want to cancel "+title+"?</p>",
                      buttons: {
                        confirm: {
                            label: 'Confirm',
                            className: 'btn btn-small btn-danger'
                        },
                        cancel: {
                            label: 'Cancel',
                            className: 'btn btn-small'
                        }
                      },
                      closeButton: false,
                      callback: function(result){
                        if (result == true) {
                          window.location = link;
                        }
                      },
                    });
  });
}

function bindUseAjax() {
  $('.useAjax').unbind('click');
  $('.useAjax').on('click', function(e){
    e.preventDefault()
    var url = $(this).data('href');
    $.ajax({
      type: 'GET',
      url: url,
      success: function(data){
        if (data['success'] = true) {
          if (data['message']) {
            displayInfoDialog('Reservation Email', data['message'], true);
          }
          else {
            location.reload();
          }
        }
        else {
          displayErrorDialog();
        }
        return false;
      },
      error: function(xhr, ajaxOptions, thrownError){
        displayErrorDialog();
      },
    });
  });
}

function displayErrorDialog() {
  bootbox.alert({title: "Error",
                message: "Something went wrong.  Try again later!",
                closeButton: false
              });
}

function displayWarningDialog(message) {
   bootbox.alert({title: "Warning",
                message: message,
                closeButton: false
              });
}
function displayInfoDialog(title, message, reload) {
   bootbox.alert({title: title,
                message: message,
                closeButton: false,
                callback: function() {
                  if (reload) {
                    location.reload();
                   }
                }
              });
}

function bindWarningAction() {
  $('.warn.action').on('click', function(e) {
    e.preventDefault();
    var message = $(this).data('title');
    displayWarningDialog(message);
  });
}

function bindPagination(){
  var page = '';
  $('div.paginate a.page').on('click', function(e){
    page = $(this).data('page');
    $('form.filter_form input#page').val(page);
    $('form.filter_form').submit();
  });
  $('div.paginate select.pages').on('change', function(e){
    page = $(this).val();
    $('form.filter_form input#page').val(page);
    $('form.filter_form').submit();
  });
}

function bindCalendarNavigation() {
  $('table.calendar th.month').prepend('<i class="fa fa-caret-left prev_month nav_month" title="Previous Month"></i>').append('<i class="fa fa-caret-right next_month nav_month" title-"Next Month"></i>');
  $('table.calendar th.month .nav_month').on('click', function(){
    var delta = 0;
    if($(this).hasClass('prev_month')){
      delta = -1;
    }
    else {
      delta = 1;
    }
    var selected_date = $('.datepicker.availability').val().split(' ');
    var new_date = new Date(selected_date[0] + '1, '+ selected_date[1]);
    new_date.setMonth(new_date.getMonth() + delta);
    $('.datepicker.availability').datepicker("setDate", new_date).trigger("change");
  });
  equalheight();
  $(window).bind("resize", equalheight);
}

function bindBaxterBoxTabs() {
  if ($('input#current_tab').val() == 'activities_tab') {
    $('a#activities_tab').trigger('click');
  }
  else {
    $('a#equipment_tab').trigger('click');
  }
}

function equalheight() {
  var maxHeight = 0;
  $('.availability_row').height('auto');
  $('.availability_row').each(function () {
    if ($(this).height() > maxHeight) {
      maxHeight = $(this).height();
    }
  });
  $('.availability_row').height(maxHeight);
}



function auto_submit_search(form) {
  clearTimeout(timeout);
  timeout = setTimeout(function(){
    $(form).submit();
  }, 800);
}

