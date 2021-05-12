$('#id_part_description').autocomplete({
    minLength: 3, 
    source: function (request, response) {
        var ts = Date.now();
        $.getJSON(`/order_management/order_autocomplete/part_description=${request.term.replace('=','')},${ts}`, function(data){
            response(data);
        })
    },
    select: function(e, ui) {
        var extra_data = ui.item.data.split('§§');
        $('#id_supplier_part_no').val(extra_data[0]);
        $('#id_supplier').val(extra_data[1]);
        $('#id_location').val(extra_data[2]);
        if (extra_data[3] != "0") {
            $('#id_msds_form').val(extra_data[3])
        } else {
            $('#id_msds_form').val(null)
        };
        if (extra_data[4] != "") {
            $('#id_price').val(extra_data[4])
        } else {
            $('#id_price').val(null)
        };
        if (extra_data[5] != "") {
            $('#id_cas_number').val(extra_data[5])
        } else {
            $('#id_cas_number').val(null)
        };
        if (extra_data[6] != "") {
            $('#id_ghs_symbols').val(extra_data[6])
        } else {
            $('#id_ghs_symbols').val(null)
        };
        if (extra_data[7] != "") {
            $('#id_signal_words').val(extra_data[7])
        } else {
            $('#id_signal_words').val(null)
        };
        if (extra_data[8] != "") {
            $('#id_hazard_level_pregnancy').val(extra_data[8])
        } else {
            $('#id_hazard_level_pregnancy').val(null)
        };
    }
    });

$('#id_supplier_part_no').autocomplete({
    minLength: 3, 
    source: function (request, response) {
        var ts = Date.now();
        $.getJSON(`/order_management/order_autocomplete/supplier_part_no=${request.term.replace('=','')},${ts}`, function(data){
            response(data);
        })
    },
    select: function(e, ui) {
        var extra_data = ui.item.data.split('§§');
        $('#id_part_description').val(extra_data[0]);
        $('#id_supplier').val(extra_data[1]);
        $('#id_location').val(extra_data[2]);
        if (extra_data[3] != "0") {
            $('#id_msds_form').val(extra_data[3])
        } else {
            $('#id_msds_form').val(null)
        }
        ;if (extra_data[4] != "") {
            $('#id_price').val(extra_data[4])
        } else {
            $('#id_price').val(null)
        }
        ;if (extra_data[5] != "") {
            $('#id_cas_number').val(extra_data[5])
        } else {
            $('#id_cas_number').val(null)
        }
        ;if (extra_data[6] != "") {
            $('#id_ghs_symbols').val(extra_data[6])
        } else {
            $('#id_ghs_symbols').val(null)
        };
        if (extra_data[7] != "") {
            $('#id_signal_words').val(extra_data[7])
        } else {
            $('#id_signal_words').val(null)
        };
        if (extra_data[8] != "") {
            $('#id_hazard_level_pregnancy').val(extra_data[8])
        } else {
            $('#id_hazard_level_pregnancy').val(null)
        };
    }
});