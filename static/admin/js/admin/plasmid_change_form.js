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

    // If map field changes add ShowLoading to form onsubmit and show toggle to decide if common features should be detected
    $("#id_map,#id_map_gbk").change(function() {

        $("#plasmid_form").attr('onsubmit', 'ShowLoading()');

        const fieldName = $(this).attr('id').replace('id_', '');

        if ($(`#detect-common-features-dna_${fieldName}`).length < 1) {
            var dna_map_field_label = document.getElementsByClassName(`form-row field-${fieldName}`).item(0).children.item(0).children.item(0);
            dna_map_field_label.innerHTML = dna_map_field_label.innerHTML + '<br><br>';

            var detect_common_features_toggle = document.createElement('input');
            detect_common_features_toggle.name = `detect_common_features_${fieldName}`;
            detect_common_features_toggle.id = `detect-common-features-dna_${fieldName}`;
            detect_common_features_toggle.type = "checkbox";
            detect_common_features_toggle.checked = true;

            var label_for_toggle = document.createElement('span');
            label_for_toggle.innerText = ' Detect common features in this map?';
            label_for_toggle.style = 'color: #efb829;';

            dna_map_field_label.appendChild(detect_common_features_toggle);
            dna_map_field_label.appendChild(label_for_toggle);
        }
    });

    // Add "button" to show plasmid map as OVE plasmid preview in a magnificent popup

    let plasmidNameField = $('.field-name');
    let plasmidName = plasmidNameField.find('.readonly')[0] ? plasmidNameField.find('.readonly')[0].innerHTML : plasmidNameField.find('input')[0].value;
    
    $('.field-map,.field-map_gbk').each((i, e) => {
        let mapLinkElement = $(e).find('a')[0];
        if (mapLinkElement !== undefined) {
            let plasmidMapBaseUrl = `/ove/?file_name=${mapLinkElement.pathname}&title=${plasmidName}`;
            $(`<a class="magnific-iframe" style="padding-left:10px; padding-right:10px;" href=${plasmidMapBaseUrl}>⊙</a>`).insertAfter(mapLinkElement);
        }
    }
    );

    $('.magnific-iframe').magnificPopup({
          
        type: 'iframe',
        
        iframe: {
            markup: '<div class="mfp-iframe-scaler">' +
                    '<div class="mfp-close"></div>' +
                    '<iframe class="mfp-iframe" frameborder="0" allowfullscreen></iframe>'+
                    '</div>'
        },
        
        gallery: {
          enabled: true,
          preload: [0,2],
          navigateByImgClick: true,
          arrowMarkup: '<button title="%title%" type="button" class="mfp-arrow mfp-arrow-%dir%"></button>',
          tPrev: 'Previous (Left arrow key)',
          tNext: 'Next (Right arrow key)',
          tCounter: '<span class="mfp-counter">%curr% of %total%</span>'
        }
      });
    
});