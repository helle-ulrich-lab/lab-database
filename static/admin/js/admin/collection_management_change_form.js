// For /templates/admin/collection_management/change_form.html

$(window).on('load', function() {

    // If there is an error uncollapse collapsed divs with error
    var errorlist_msg = document.getElementsByClassName("errorlist");
    if (errorlist_msg.length > 0) {
        var i;
        for (i = 0; i < errorlist_msg.length; i++) {
            errorlist_msg[i].closest('fieldset').classList.remove('collapsed');
        }
    }

    // Colour-code episomal plasmids
    var yeast_episomal_plasmids = $("input[name$='present_in_stocked_strain']").filter(':checked');
    if (yeast_episomal_plasmids.length > 0) {
        var i;
        for (i = 0; i < yeast_episomal_plasmids.length; i++) {
            yeast_episomal_plasmids[i].closest('tr').style = 'background-color:#d7e7ee;';
        }
    }

    var cellline_episomal_plasmids = $("input[name$='s2_work_episomal_plasmid']").filter(':checked');
    if (cellline_episomal_plasmids.length > 0) {
        var i;
        for (i = 0; i < cellline_episomal_plasmids.length; i++) {
            cellline_episomal_plasmids[i].closest('tr').style = 'background-color:#d7e7ee;';
        }
    }
});

// DO NOT USE, it prevents the value of a submit
// line button to be passed to request
// Disable submit line if form is submitted
// $(document).ready(function() {
//     $('[id$="_form"').submit(function(event) {
//         $("input:submit").attr('disabled', true);
//     });
// });