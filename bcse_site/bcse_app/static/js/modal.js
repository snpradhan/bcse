function bindModalOpen() {
  $(".modal-open").click(function(e){
    //e.preventDefault();
    var parentModal = $(this).closest('.modal')
    var url = $(this).data('href');
    var target = $(this).data('bs-target');
    $(target).load(url, function() {
      $(this).show();
      if($(parentModal).length){
        $(parentModal).hide();
      }
    });
  });
}

$(function (){
  bindModalOpen();
});

