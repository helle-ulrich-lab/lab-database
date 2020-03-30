// For /templates/admin/collection_management/plasmid/change_form.html

$(window).on('load', function() {

    // If there is a formz feature warning uncollapse formz section and highlight formz element field
    if (document.getElementsByClassName("missing-formz-features").length > 0) {
        var formz_element_field = document.getElementsByClassName("form-row field-formz_elements")[0];
        formz_element_field.closest('fieldset').classList.remove('collapsed');
        formz_element_field.classList.add('errors');

        var warning_in_field = document.createElement('ul');
        var warning_message = document.createElement('li');
        warning_in_field.classList.add('errorlist');
        warning_message.innerText = "Missing elements: " + document.getElementsByClassName('missing-formz-features')[0].innerText;
        warning_message.style = 'color: #efb829;';
        warning_in_field.appendChild(warning_message);
        formz_element_field.appendChild(warning_in_field);

        formz_element_field.getElementsByClassName("select2-selection select2-selection--multiple")[0].style = 'border:solid 1px #efb829;';
    }
});

$(document).ready(function() {

    // If map field changes add ShowLoading to form onsubmit and show toggle to decide if common features shoudl be detected
    $("#id_map").change(function() {

        $("#plasmid_form").attr('onsubmit', 'ShowLoading()');

        if ($('#detect-common-features-dna_map_dna').length < 1) {
            var dna_map_field_label = document.getElementsByClassName("form-row field-map").item(0).children.item(0).children.item(0);
            dna_map_field_label.innerHTML = dna_map_field_label.innerHTML + '<br><br>';

            var detect_common_features_toggle = document.createElement('input');
            detect_common_features_toggle.name = "detect_common_features_map_dna";
            detect_common_features_toggle.id = "detect-common-features-dna_map_dna";
            detect_common_features_toggle.type = "checkbox";
            detect_common_features_toggle.checked = true;

            var label_for_toggle = document.createElement('span');
            label_for_toggle.innerText = ' Detect common features in this map?';
            label_for_toggle.style = 'color: #efb829;';

            dna_map_field_label.appendChild(detect_common_features_toggle);
            dna_map_field_label.appendChild(label_for_toggle);
        }
    });

    $("#id_map_gbk").change(function() {

        $("#plasmid_form").attr('onsubmit', 'ShowLoading()');

        if ($('#detect-common-features-dna_map_gbk').length < 1) {
            var gbk_map_field_label = document.getElementsByClassName("form-row field-map_gbk").item(0).children.item(0).children.item(0);
            gbk_map_field_label.innerHTML = gbk_map_field_label.innerHTML + '<br><br>';

            var detect_common_features_toggle = document.createElement('input');
            detect_common_features_toggle.name = "detect_common_features_map_gbk";
            detect_common_features_toggle.id = "detect-common-features-dna_map_gbk";
            detect_common_features_toggle.type = "checkbox";
            detect_common_features_toggle.checked = true;

            var label_for_toggle = document.createElement('span');
            label_for_toggle.innerText = ' Detect common features in this map?';
            label_for_toggle.style = 'color: #efb829;';

            gbk_map_field_label.appendChild(detect_common_features_toggle);
            gbk_map_field_label.appendChild(label_for_toggle);
        }
    });

    // DO NOT USE, it prevents the value of a submit
    // line button to be passed to request
    // Disable submit line if form is submitted
    // $('[id$="_form"').submit(function(event) {
    //     $("input:submit").attr('disabled', true);
    // });

});