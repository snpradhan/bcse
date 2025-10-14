function bindModalOpen() {
  $(".modal-open").click(function(e){
    e.stopImmediatePropagation();
    var parentModal = $(this).closest('.modal');
    var url = $(this).data('href');
    var target = $(this).data('bs-target');

    $(target).load(url, function() {
      $(target).show();
      if (parentModal.length) {
        parentModal.hide();
      }
      bindTooltipTrigger();
      bindDateTimePicker();
      bindSelect2();
    });
  });
}

$(function (){
  bindModalOpen();

  $('.modal').on('hidden.bs.modal', function () {
    bindDateTimePicker();
  });

  $('.modal').on('scroll', function(){
    $('.datepicker').blur().datepicker('hide');
  });

});

