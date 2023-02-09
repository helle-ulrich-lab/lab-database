// Refresh list of orders asynchronously, after a period of inactivity 
// at least 1 min

var idleTime = 0;
let currentRootUrl = window.location.pathname + window.location.search;

// Increment the idle time every min
function timerIncrement() {
    idleTime = idleTime + 1;
}

// Check if the page being viewed is the 'root' order list view
if (orderRootUrl == currentRootUrl) {

    $(document).ready(function () {

        // Increment the idle time counter every minute.
        var idleInterval = setInterval(timerIncrement, 1000);

        // On mouse movement or key press, refresh the order list 
        // reset the idle timer
        $(this).mousemove(() => {
            if (idleTime > 59) {
                refreshOrderList();
            }
            idleTime = 0;
        });

        $(this).keypress(() => {
            if (idleTime > 59) {
                refreshOrderList();
            }
            idleTime = 0;
        });
    });

}

// AJAX request to update the order list in the background
function refreshOrderList() {
    let getNewDataUrl = window.location.href;
    $.ajax({
        url: getNewDataUrl,
        method: 'GET',
        data: {},
        success: (data) => {
            $('#result_list').replaceWith($('#result_list', data));
        },
        error: (error) => {
            console.log(error);
        }
    });
}

$(document).ready(function () {

    function removeCustomActionDropdown() {
        if ($('#changelist-form').find('label').length > 1) {
            $('#changelist-form').find('label')[1].remove();
        }
    }

    // Get the Action dropdown menu
    let actionDropDown = $('#changelist-form').find('select').first();

    // If export action is selected, add file type dropdown
    actionDropDown.change(function () {

        if ($(this).val().startsWith("export_")) {

            removeCustomActionDropdown();

            // Create label new label for format selection dropdown
            let selectAttachElement = document.createElement('label');
            selectAttachElement.innerText = 'Format: ';
            selectAttachElement.style.cssText = 'padding-left: 1em;';

            // Create dropdown
            let selectAttachBox = document.createElement('select');
            selectAttachBox.name = 'format';

            // Create options for dropdown
            let optionTsv = document.createElement('option');
            optionTsv.innerText = 'Tab-separated values';
            optionTsv.value = 'tsv';

            let optionXlsx = document.createElement('option');
            optionXlsx.innerText = 'Excel';
            optionXlsx.value = 'xlsx';

            // Add options to dropdown
            selectAttachBox.appendChild(optionXlsx);
            selectAttachBox.appendChild(optionTsv);

            // Add dropdown to label
            selectAttachElement.appendChild(selectAttachBox);

            // Add dropdown element to form
            $('#changelist-form').find('label')[0].append(selectAttachElement);

        }
        else {
            removeCustomActionDropdown();
        }
    });
});