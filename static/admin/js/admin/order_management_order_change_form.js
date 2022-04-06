// Order autocomplete

$('#id_part_description,#id_supplier_part_no').click(function () {

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
            Object.entries(ui.item.data).forEach((fieldData) => {
                $(`#id_${fieldData[0]}`).val(fieldData[1]);
            });
        },
    }).autocomplete("instance")._renderItem = function (ul, item) {
        return $("<li>")
            .attr("data-value", item.value)
            .append([item['label'], Object.values(item['data'])[0], Object.values(item['data'])[1].replace(" GmbH", "")].join("<span style='color:indianred; margin:0; padding-left:5px; padding-right:5px;'>|</span>"))
            .appendTo(ul);

    }
});

