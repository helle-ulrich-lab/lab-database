// For /templates/admin/collection_management/change_form.html

$(window).on('load', function() {

    // If there is an error uncollapse collapsed divs with error
    var errorlist_msg = document.getElementsByClassName("errorlist");
    if (errorlist_msg.length > 0) {
        for (let i = 0; i < errorlist_msg.length; i++) {
            errorlist_msg[i].closest('fieldset').classList.remove('collapsed');
        }
    }

    // Colour-code episomal plasmids present in a stocked strain or viral packaging plasmids
    let episomal_plasmids = $("input[name$='present_in_stocked_strain'], input[name$='s2_work_episomal_plasmid']",).filter(':checked');
    if (episomal_plasmids.length > 0) {
        episomal_plasmids.each(function(i, e){
            e.closest('tr').style = 'border:2px solid var(--accent)';
        });
    }
});