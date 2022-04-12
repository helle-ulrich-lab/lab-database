// Order autocomplete

$('#id_part_description,#id_supplier_part_no').click(function () {

    const labelFieldName = $(this).attr('id').replace('id_', '');
    const firstDataFieldName = labelFieldName === 'part_description' ? 'supplier_part_no' : 'part_description';

    $(`#id_${labelFieldName}`).autocomplete({

        minLength: 3,

        source: (request, response) => {
            const timeStamp = Date.now();
            $.getJSON(`/order_management/order_autocomplete/${labelFieldName}=${request.term.trim().replace('=', '')},${timeStamp}`, data => {
                response(data);
            })
        },

        select: (e, ui) => {
            for (let fieldName in ui.item.data)
                $(`#id_${fieldName}`).val(ui.item.data[fieldName]);
        },

    }).autocomplete("instance")._renderItem = (ul, item) => {

        const firstTextElementWidth = labelFieldName === 'part_description' ? 50 : 16;
        const secondTextElementWidth = firstDataFieldName === 'part_description' ? 50 : 16;

        const displayText = `<span class='truncated' style='width:${firstTextElementWidth}%;'>${item['label']}</span>
                             <span class='field-separator'>|</span>
                             <span class='truncated' style='width:${secondTextElementWidth}%;'>${item['data'][firstDataFieldName]}</span>
                             <span class='field-separator'>|</span>
                             <span class='truncated' style='width:24%;'>${item['data']['supplier'].replace("GmbH", "")}</span>`;

        return $("<li>")
            .attr("data-value", item.value)
            .append(`<span style='margin:0px 5px; white-space: nowrap; padding:3px;'>${displayText}</span>`)
            .appendTo(ul);

    }
});