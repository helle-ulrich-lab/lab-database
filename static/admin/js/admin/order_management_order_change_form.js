
window.onload = (event) => {

    // Autocomplete for part_description and supplier_part_no

    let fillInCommonFields = data => {
        const fields = ['supplier', 'location', 'msds_form',
            'price', 'cas_number', 'ghs_symbols',
            'signal_words', 'hazard_level_pregnancy'];
        fields.forEach(field => {
            let field_id = `#id_${field}`;
            $(field_id).val(data[field]);
        }
        )
    }

    $('#id_part_description').autocomplete({

        minLength: 3,

        source: (request, response) => {
            let ts = Date.now();
            $.getJSON(`/order_management/order_autocomplete/part_description=${request.term.trim().replace('=', '')},${ts}`, data => {
                response(data);
            })
        },

        select: (e, ui) => {
            let data = ui.item.data;
            $('#id_supplier_part_no').val(data['supplier_part_no']);
            fillInCommonFields(data);
        }
    });

    $('#id_supplier_part_no').autocomplete({

        minLength: 3,

        source: (request, response) => {
            let ts = Date.now();
            $.getJSON(`/order_management/order_autocomplete/supplier_part_no=${request.term.trim().replace('=', '')},${ts}`, data => {
                response(data);
            })
        },

        select: (e, ui) => {
            let data = ui.item.data;
            $('#id_part_description').val(data['part_description']);
            fillInCommonFields(data);
        }
    });

};