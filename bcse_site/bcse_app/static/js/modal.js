$(function (){

  $(".modal-open").click(function(e){
    //e.preventDefault();
    var url = $(this).data('href');
    var target = $(this).data('bs-target');
    $(target).load(url, function() {
      $(this).show();
    });
  });


});
