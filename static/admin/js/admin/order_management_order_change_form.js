// Order autocomplete

$('#id_part_description,#id_supplier_part_no').click(function() {
    
    let field_name = $(this).attr('id').replace("id_", "");

    $(`#id_${field_name}`).autocomplete({

        minLength: 3,
    
        source: (request, response) => {
            let ts = Date.now();
            $.getJSON(`/order_management/order_autocomplete/${field_name}=${request.term.trim().replace('=', '')},${ts}`, data => {
                response(data);
            })
        },
    
        select: (e, ui) => {
            Object.entries(ui.item.data).forEach((fieldData) =>{
                $(`#id_${fieldData[0]}`).val(fieldData[1]);
            });
        }
    });
});