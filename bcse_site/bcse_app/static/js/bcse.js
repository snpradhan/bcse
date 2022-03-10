$(function (){

  $(".datepicker").datepicker();

  $('.registration_submit').on('click', function(e){
    e.preventDefault();
    var workshop_registration_container = $(this).closest('.workshop_registration');
    var form = $(this).closest('form');
    $.ajax({
      type: $(form).attr('method'),
      url: $(form).attr('action'),
      data: $(form).serialize(),
      success: function(data){
        if(data['success'] = true) {
          if(data['message']) {
            var delete_url = '/workshop/'+data['workshop_id']+'/registration/'+data['registration_id']+'/delete';
            var delete_button = '<a role="button" class="btn btn-danger btn-small" href="'+delete_url+'" >Delete</a>';
            var message = '<div class="message '+data['message_class']+'"><div>'+data['message']+'</div><br>'+delete_button+'</div>';
            $(workshop_registration_container).html(message);
          }
          else {
            location.reload();
          }
        }
        else{
          alert("Something went wrong.  Try again later!");
        }
        return false;
      },
      error: function(xhr, ajaxOptions, thrownError){
        alert("Something went wrong.  Try again later!");
      },
    });
  });
});



