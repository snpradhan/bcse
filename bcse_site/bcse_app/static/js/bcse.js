$(function (){

  $(".datepicker").datepicker();

  $('.registration_submit').on('click', function(e){
    var workshop_registration_container = $(this).closest('.workshop_registration');
    var form = $(this).closest('form');
    console.log($(form).attr('method'));
    console.log($(form).attr('action'));
    console.log($(form).serialize());
    $.ajax({
      type: $(form).attr('method'),
      url: $(form).attr('action'),
      data: $(form).serialize(),
      success: function(data){
        console.log('done');
        console.log(data);
        if(data['success'] = true) {
          if(data['message']) {
            $(workshop_registration_container).html(data['message']);
          }
          else {
            location.reload();
          }
          console.log('success');
          console.log(data['message']);
        }
        else{
          console.log('fail');
          console.log(data['message']);
          //$(workshop_registration_container).html(data['form']);
        }
        return false;
      },
      error: function(xhr, ajaxOptions, thrownError){
        alert("Something went wrong.  Try again later!");
      },
    });
  });
});



