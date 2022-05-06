// Refresh list of orders if mouse moves after x s
var idleTime = 0;

var current_root_url = window.location.pathname + window.location.search;

if (order_root_url == current_root_url){
$(document).ready(function () {
    //Increment the idle time counter every minute.
    var idleInterval = setInterval(timerIncrement, 1000); // 5 s

    //Zero the idle timer on mouse movement.
    $(this).mousemove(function (e) {
        if (idleTime > 59){
        refreshStream();
        }
        idleTime = 0;
    });
    $(this).keypress(function (e) {
        if (idleTime > 59){
        refreshStream();
        }
        idleTime = 0;
    });
});
}

var refreshStream = function(){
var getNewDataUrl = window.location.href;
    $.ajax({
        url: getNewDataUrl,
        method: 'GET',
        data: {},
        success: function(data){
        $('#result_list').replaceWith($('#result_list',data));
        },
        error: function(error){
            console.log(error);
        }
    });
}

function timerIncrement() {
    idleTime = idleTime + 1;
    }

    $(document).ready(function() {

    var action_drop_down = $('#changelist-form').find('select').first();

    // Add plasmid map attachment type selection box if formz_as_html action is selected
    // Add file  selection box if export action is selected
    action_drop_down.change(function(){

    if($(this).val().startsWith("export_"))
    {

    if ($('#changelist-form').find('label').length > 1)
        {
        $('#changelist-form').find('label')[1].remove();
    }

    var form = $('#changelist-form');
    var select_attach_element = document.createElement('label');
    select_attach_element.innerText = 'Format: ';
    select_attach_element.style.cssText = 'padding-left: 1em;';

    var select_attach_box = document.createElement('select');
    select_attach_box.name = 'format';

    var option_tsv = document.createElement('option');
    option_tsv.innerText = 'Tab-separated values';
    option_tsv.value = 'tsv';

    var option_xlsx = document.createElement('option');
    option_xlsx.innerText = 'Excel';
    option_xlsx.value = 'xlsx';

    select_attach_box.appendChild(option_xlsx);
    select_attach_box.appendChild(option_tsv);

    select_attach_element.appendChild(select_attach_box);
    $('#changelist-form').find('label')[0].append(select_attach_element);

    }
    else {
        if ($('#changelist-form').find('label').length > 1)
        {
        $('#changelist-form').find('label')[1].remove();
        }
    }

    });

    });

    $('.magnificent').magnificPopup({
    type: 'iframe',
    iframe: {
        markup: '<div class="mfp-iframe-scaler">' +
                '<div class="mfp-close"></div>' +
                '<iframe class="mfp-iframe" frameborder="0" style="background: #FFFFFF;" allowfullscreen></iframe>'+
                '</div>'
    },
    gallery: {
        enabled: true, // set to true to enable gallery
        preload: [0,2], // read about this option in next Lazy-loading section
        navigateByImgClick: true,
        arrowMarkup: '<button title="%title%" type="button" class="mfp-arrow mfp-arrow-%dir%"></button>', // markup of an arrow button
        tPrev: 'Previous (Left arrow key)', // title for left button
        tNext: 'Next (Right arrow key)', // title for right button
        tCounter: '<span class="mfp-counter">%curr% of %total%</span>' // markup of counter
    }
});