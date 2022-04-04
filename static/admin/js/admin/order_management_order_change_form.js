// Order autocomplete

let fillInFields = data => {
    Object.entries(data).forEach((fieldData) =>{
        $(`#id_${fieldData[0]}`).val(fieldData[1]);
    });
}

// Autocomplete for part_description

$('#id_part_description').autocomplete({

    minLength: 3,

    source: (request, response) => {
        let ts = Date.now();
        $.getJSON(`/order_management/order_autocomplete/part_description=${request.term.trim().replace('=', '')},${ts}`, data => {
            response(data);
        })
    },

    select: (e, ui) => {
        fillInFields(ui.item.data);
    }
});

// Autocomplete for supplier_part_no

$('#id_supplier_part_no').autocomplete({

    minLength: 3,

    source: (request, response) => {
        let ts = Date.now();
        $.getJSON(`/order_management/order_autocomplete/supplier_part_no=${request.term.trim().replace('=', '')},${ts}`, data => {
            response(data);
        })
    },

    select: (e, ui) => {
        fillInFields(ui.item.data);
    }
});