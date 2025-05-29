function bindModalOpen() {
  $(".modal-open").click(function(e){
    e.stopImmediatePropagation();
    var parentModal = $(this).closest('.modal')
    var url = $(this).data('href');
    var target = $(this).data('bs-target');
    $(target).load(url, function() {
      $(this).show();
      console.log('opening modal');
      if($(parentModal).length){
        $(parentModal).hide();
      }
      bindTooltipTrigger();
      bindDateTimePicker();

    });
  });
}

$(function (){
  bindModalOpen();

  $('.modal').on('hidden.bs.modal', function () {
    $('.datepicker').datepicker('destroy');
  });

});

