$(function (){

  var timeout = null;

  function bindRegistrationSubmit(){
    $('.registration_submit').on('click', function(e){
      e.preventDefault();
      var workshop_registration_container = $(this).closest('.workshop_registration');
      var form = $(this).closest('form');
      $.ajax({
        type: $(form).attr('method'),
        url: $(form).attr('action'),
        data: $(form).serialize(),
        success: function(data){
          console.log(data);
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
              bindDeleteAction()
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
    $('.delete.action').on('click', function(e){
      e.preventDefault();
      var link = $(this).data('href');
      var title = $(this).data('title');

      bootbox.confirm({ title: 'Confirm',
                        message: "<p>Do you want to delete "+title+"</p>",
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

  function displayErrorDialog(){
    bootbox.alert({title: "Error",
                  message: "Something went wrong.  Try again later!",
                  closeButton: false
                });
  }

  $(".datepicker").datepicker({
    dateFormat: "MM dd, yy"
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

  $('form.filter_form').on('submit', function(e){
    e.preventDefault();
    var form = $(this);
    const queryString = $(form).serialize();
    var url = $(form).attr('action')+'?'+queryString;
    console.log(queryString);
    $.ajax({
      type: $(form).attr('method'),
      url: url,
      success: function(data){
        if(data['success'] = true) {
          $('div.workshops').html(data['html']);
          bindRegistrationSubmit();
          bindDeleteAction();
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
  $('form.filter_form :input').on('change', function(e){
    clearTimeout(timeout);
    var form = $(this).closest('form');
    timeout = setTimeout(function(){
      $(form).submit();
    }, 800);
  });

  $('form.filter_form #clear').on('click', function(e){
    $('form.filter_form')[0].reset();
    var form = $(this).closest('form');
    $(form).submit();
  });

  $('#filter_toggle label').click(function(){
    $('#filter_toggle label').toggle();
    $('#filter_fields').toggle();
  });

  //disable Enter key press
  $("form").bind("keypress", function(e) {
    if (e.keyCode == 13) {
      return false;
    }
  });

  bindRegistrationSubmit();
  bindDeleteAction();

});



