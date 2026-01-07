$(function (){

  $(".copyright_year").html(new Date().getFullYear());

  //generic filter form submit handler
  $('form.filter_form').on('submit', function(e){
    e.preventDefault();
    var form = $(this);
    var form_id = $(this).attr('id');
    //the container to place the search results
    var result_container = $(this).closest('.content').find('.search_results');
    const queryString = $(form).serialize();
    var url = $(form).attr('action')+'?'+queryString;
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
          if(data['html']){
            $(result_container).html(data['html']);
          }

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
          bindTooltipTrigger();
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

  $('.filter_fields').filter(function() {
      return $.trim($(this).text()) === '';
  }).hide();

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



  /*$(window).on('resize', function(){
    paginationPadding();
  });*/

  $('.about_us .partner .description p').addClass('callout wysiwyg_content');
  $('.about_us .member .description p').addClass('callout wysiwyg_content');

  bindPagination();
  bindRegistrationSubmit();
  bindDeleteAction();
  bindCancelAction();
  bindWarningAction();
  bindUseAjax();
  bindSelect2();
  bindTooltipTrigger();
  bindDateTimePicker();
  bindUnsavedChangesWarning();

});

var timeout = null;

function bindDateTimePicker() {

  $('.datepicker:not(.reservation_date):not(.availability)').datepicker('destroy');
  $(".datepicker:not(.reservation_date):not(.availability)").each(function(){

    $(this).datepicker({
      dateFormat: "MM dd, yy",
      yearRange: "-20:+20",
      changeMonth: true,
      changeYear: true,
      beforeShow: function(input, inst) {
        const $input = $(input);
        const isInModal = $input.closest('.modal').length > 0;
        if (isInModal) {
          // Append to modal to avoid z-index issues
          inst.dpDiv.appendTo($input.closest('.modal'));
        } else {
          // Default behavior
          inst.dpDiv.appendTo('body');
        }
      },
    });
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
    scrollbar: true,
    change: function(time) {
      $(this).trigger("change");
    }
  });

  $('.fa-calendar').on('click', function(){
    $(this).closest('.input-group').find('.datepicker').datepicker("show");
  });

  //insert clear(X) icon on datepicker input to clear the date

  $('.datepicker').each(function () {
    const $input = $(this);

    // Skip if already processed
    if ($input.data('has-clear')) return;
    $input.data('has-clear', true);

    const $group = $input.closest('.input-group');

    // Insert clear button before calendar icon
    const clearBtn = `
      <span class="input-group-text clear-date" style="cursor:pointer; display:none;">
        <i class="fa fa-times"></i>
      </span>
    `;

    $group.find('.fa-calendar').closest('.input-group-text').before(clearBtn);
  });

  // Clear date click
  $(document).on('click', '.clear-date', function () {
    const $input = $(this).closest('.input-group').find('.datepicker');

    $input.val('');

    // jQuery UI Datepicker support
    if ($.datepicker) {
      $input.datepicker('setDate', null);
    }

    $(this).hide();
    $input.trigger('change');
  });

  // Toggle clear icon on change
  function toggleClearIcon(input) {
    const $input = $(input);
    const $clearBtn = $input.closest('.input-group').find('.clear-date');

    $clearBtn.toggle(!!$input.val());
  }

  // On change
  $(document).on('change', '.datepicker', function () {
    toggleClearIcon(this);
  });

  // Run once on page load (handles pre-filled dates)
  $('.datepicker').each(function () {
    toggleClearIcon(this);
  });

}

function bindTooltipTrigger() {
  var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
  var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
    return new bootstrap.Tooltip(tooltipTriggerEl)
  });
}

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
            bindWarningAction();
            bindModalOpen();
            bindUseAjax();


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
    var title = $(this).data('title');

    bootbox.confirm({
      title: 'Confirm',
      message: "<p>Do you want to send reservation "+title+" email?</p>",
      buttons: {
        confirm: {
            label: 'Confirm',
            className: 'btn btn-small'
        },
        cancel: {
            label: 'Cancel',
            className: 'btn btn-small btn-danger'
        }
      },
      closeButton: false,
      callback: function(result){
        if (result == true) {
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
        }
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

  //paginationPadding();

}

/*function paginationPadding() {
  var delta = $('table.table').width() - $('div.paginate').width();
  $('div.paginate').width($('table.table').width());
  $('div.paginate').css('padding-right', delta);
}
*/
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

function bindInventoryRowDelete() {
  $('.delete_inventory').on('click', function(e){
    formRow = $(this).closest('.form-row');
    deleteInput = formRow.find('input[type="hidden"][name$="-DELETE"]')[0];

    if (deleteInput) {
      $(deleteInput).val('on'); // Mark for deletion
      $(formRow).hide();
    }
  });
}

function bindBaxterBoxTabs() {
  if ($('input#current_tab').val() == 'activities_tab') {
    $('a#activities_tab').trigger('click');
  }
  else if ($('input#current_tab').val() == 'equipment_tab') {
    $('a#equipment_tab').trigger('click');
  }
  else if ($('input#current_tab').val() == 'community_tab') {
    $('a#community_tab').trigger('click');
  }
  else {
    $('a#faq_tab').trigger('click');
  }
}

function equalheight() {
  var maxHeight = [];
  var count = 0;
  $('.admin_calendar .availability_row').height('auto');
  $('.admin_calendar tr').each(function(){
    count = $(this).find('td .availability_row').length;
    maxHeight = Array(count).fill(0);
    $(this).find('.availability_row').each(function () {
      if ($(this).height() > maxHeight[$(this).index()]) {
        maxHeight[$(this).index()] = $(this).height();
      }
    });
    var allZeros = maxHeight.every(function(value){
      return value === 0;
    })
    if(!allZeros){
      $(this).find('.availability_row').each(function () {
        $(this).height(maxHeight[$(this).index()]);
      });
    }
  });
}



function auto_submit_search(form) {
  clearTimeout(timeout);
  timeout = setTimeout(function(){
    $(form).submit();
  }, 800);
}

function bindSelect2() {
  $('select.select2:not(#id_equipment_types)').select2({
    placeholder: {
      id: '-1', // the value of the option
      text: 'Start typing to search and select one or more'
    },
    width : '100%'
  });
}

/*
  Export multiple html tables to excel and place them
  in individual tabs.
  tables: array of html table ids
  filename: excel filename to be exported
  filter: boolean to include filter form data
*/
function exportTablesToExcel(tables, filename, filter) {
  // Create a new workbook
  var wb = XLSX.utils.book_new();
  var table_element = [];
  var ws = [];
  var index = 0;

  for(var i=0; i < tables.length; i++) {
    // Get the tables
    table_element[i] = document.getElementById(tables[i]);

    // Get column index based on CSS class
    var columnsToRemove = [];
    var headers = table_element[i].querySelectorAll('th');
    headers.forEach((header, index) => {
      if (header.classList.contains('ignore-column')) {
        columnsToRemove.push(index);
      }
    });

    // Convert tables to worksheet
    ws[i] = XLSX.utils.table_to_sheet(table_element[i]);
     // Set all cell types in the sheet to string
    Object.keys(ws[i]).forEach((cellAddress) => {
      if (cellAddress[0] !== '!') {
        ws[i][cellAddress].t = 's'; // Force text
        ws[i][cellAddress].z = '@';  // Excel "Text" format
      }
    });


    // Iterate through each row and remove the cells in the columns to ignore
    for (let rowIndex = 0; rowIndex < table_element[i].rows.length; rowIndex++) {
      var row = table_element[i].rows[rowIndex];
      columnsToRemove.forEach(colIndex => {
        delete ws[i][XLSX.utils.encode_cell({r: rowIndex, c: colIndex})];  // Remove cell in the ignored column
      });
    }
    // Append worksheets to workbook
    XLSX.utils.book_append_sheet(wb, ws[i], tables[i].split('_').map(str => str.replace(/^\w/, c => c.toUpperCase())).join(' '));
  }

  if(filter) {

    var formData = [
      ['Field', 'Value']
    ];

    $('.filter_form').find('select').each(function () {
      var fieldName = $(this).closest('.form-group').find('label').text().trim();
      var fieldValue = $(this).find('option:selected').map(function() {
                                                              return $(this).text();  // Get the text of each selected option
                                                          }).get().join('\n');

      formData.push([fieldName, fieldValue]); // Add the field name and value to the table array
    });

    $('.filter_form').find('input[type="text"]').each(function(){
      var fieldName = $(this).closest('.form-group').find('label').text().trim();
      var fieldValue = $(this).val();
      formData.push([fieldName, fieldValue]);
    });

    // Create a worksheet from the 2D data array
    var ws_filter = XLSX.utils.aoa_to_sheet(formData);
    XLSX.utils.book_append_sheet(wb, ws_filter, 'Applied Filters');

  }
  // Export the workbook
  XLSX.writeFile(wb, filename);
}

function exportReservations() {
  $("#baxter_box_reservations").table2excel({
    exclude: ".noExl",
    name: "Baxter Box Reservations",
    filename: "Baxter_Box_Reservations", //do not include extension
    fileext:".xls", // file extension
    preserveColors: true, // set to true if you want background colors and font colors preserved
  });
}

function cloneForm(prefix, parent) {
  console.log(parent);
  const formset = document.getElementById(parent);
  console.log(formset);
  const totalFormsInput = document.getElementById('id_'+prefix+'-TOTAL_FORMS');
  const totalForms = parseInt(totalFormsInput.value, 10);

  const lastForm = formset.querySelector('.form-row:last-child');
  const newForm = lastForm.cloneNode(true);

  // Update attributes in the cloned form
  newForm.id = `form-${totalForms}`;
  const inputs = newForm.querySelectorAll('input, select, textarea');

  inputs.forEach(input => {
    // Update name and id attributes
    const nameRegex = new RegExp(`${prefix}-(\\d+)-`);
    input.name = input.name.replace(nameRegex, `${prefix}-${totalForms}-`);
    input.id = input.id.replace(nameRegex, `id_${prefix}-${totalForms}-`);

    // Destroy any existing datepicker on the clone
    if (input.classList.contains('hasDatepicker')) {
      $.datepicker.destroy && $.datepicker.destroy(input);  // Optional
      input.classList.remove('hasDatepicker');
      //remove clear button
      const group = input.closest('.input-group');
      group?.querySelector('.clear-date')?.remove();
      //newInput.removeAttribute('id'); // remove old id to avoid duplicate IDs
    }


    // Clear the value
    input.value = '';
  });
  console.log(newForm);

  // Append new form and update TOTAL_FORMS
  formset.appendChild(newForm);
  totalFormsInput.value = totalForms + 1;
  bindDateTimePicker();
  bindInventoryRowDelete();
  $(newForm).show();
}

// Track dirty state per form
function initializeForm($form) {
  if ($form.data("isTracking")) return; // avoid double tracking
  $form.data("isDirty", false);
  $form.data("isTracking", true);
}

function bindCkeditorChange() {
  // Track CKEditor fields (v4 or v5)
  if (typeof CKEDITOR !== 'undefined') {
    // CKEditor v4
    for (var name in CKEDITOR.instances) {

      CKEDITOR.instances[name].on('change', function() {
        var $form = $(this.element.$).closest("form");
        initializeForm($form);
        $form.data("isDirty", true);
      });
    }

    // Listen for dynamically added CKEditor instances
    CKEDITOR.on('instanceReady', function(ev) {
      ev.editor.on('change', function() {
        var $form = $(ev.editor.element.$).closest("form");
        initializeForm($form);
        $form.data("isDirty", true);
      });
    });
  }
}

function bindUnsavedChangesWarning() {

  /// Track standard fields
  $(document).on("input change", "form input, form textarea, form select", function(e) {
    if (e.originalEvent !== undefined) { // ignore programmatic triggers
      var $form = $(this).closest("form");
      initializeForm($form);
      $form.data("isDirty", true);
    }
  });

  // Track Select2 fields
  $(document).on("select2:select select2:unselect", "select", function(e) {
      var $form = $(this).closest("form");
      initializeForm($form);
      $form.data("isDirty", true);
  });


  $(document).on("change", ".timepicker", function (e) {
    if (!e.originalEvent) {
      this.dispatchEvent(new Event("change", { bubbles: true }));
    }
  });

  // Bridge jQuery UI Datepicker → real change event
  $(document).on("change", ".hasDatepicker", function (e) {
      // jQuery UI Datepicker calls .val(...) programmatically,
      // so this ensures your listener sees it as user-triggered.
      if (!e.originalEvent) {
          this.dispatchEvent(new Event("change", { bubbles: true }));
      }
  });

  // Reset dirty on submit
  $(document).on("submit", "form", function() {
    $(this).data("isDirty", false);
  });

  // Helper: check if any form is dirty (all forms)
  function anyFormDirty() {
    return $("form").filter(function() {
      return $(this).data("isDirty") === true;
    }).length > 0;
  }

  // Helper: check if any form inside a specific modal is dirty
  function modalFormsDirty($modal) {
    return $modal.find("form").filter(function() {
      return $(this).data("isDirty") === true;
    }).length > 0;
  }

  bindCkeditorChange();

  // Warn on tab close / refresh
  $(window).off("beforeunload.unsaved").on("beforeunload.unsaved", function(e) {
    if (anyFormDirty()) {
      var message = "You have unsaved changes. Are you sure you want to leave?";
      e.preventDefault();
      e.returnValue = message;
      return message;
    }
  });

  // Warn on in-page navigation links
  $(document).off("click.unsaved", "a").on("click.unsaved", "a", function(e) {

    // Skip ALL CKEditor interactions
    if ($(this).closest(
      '.cke, .cke_dialog, .cke_reset, .ck-editor, .ck, .ck-dialog'
    ).length) {
      return;
    }

    // Skip links inside datepicker
    if ($(this).hasClass("ui-corner-all")) {
      return; // do nothing if inside datepicker
    }

    if (anyFormDirty()) {
      e.preventDefault();
      var href = $(this).attr("href");

      bootbox.confirm({
        title: "Unsaved Changes",
        message: "You have unsaved changes on this page. Are you sure you want to leave this page?",
        buttons: {
          confirm: { label: 'Leave', className: 'btn-danger' },
          cancel: { label: 'Stay', className: 'btn-secondary' }
        },
        closeButton: false,
        callback: function(result) {
          if (result) {
            $("form").data("isDirty", false);
            window.location.href = href;
          }
        }
      });
    }
  });

  // Warn when closing a Bootstrap modal if it contains dirty forms
  $(document).on("hide.bs.modal", ".modal", function(e) {
    var $modal = $(this);

    if (modalFormsDirty($modal)) {
      e.preventDefault(); // prevent modal from closing immediately

      bootbox.confirm({
        title: "Unsaved Changes",
        message: "You have unsaved changes in this popup. Are you sure you want to close it?",
        buttons: {
          confirm: { label: 'Leave', className: 'btn-danger' },
          cancel: { label: 'Stay', className: 'btn-secondary' }
        },
        closeButton: false,
        callback: function(result) {
          if (result) {
            // Reset dirty state for forms in this modal
            $modal.find("form").data("isDirty", false);
            $modal.modal("hide"); // manually hide modal
          }
        }
      });
    }
  });
}
