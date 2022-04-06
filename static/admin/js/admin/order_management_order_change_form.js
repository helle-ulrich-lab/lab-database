// Order autocomplete

$('#id_part_description,#id_supplier_part_no').click(function () {

    let LabelFieldName = $(this).attr('id').replace('id_', '');
    let firstDataFieldName = LabelFieldName === 'part_description' ? 'supplier_part_no' : 'part_description';
    let dotifyText = function (text, maxLength) {
        if (text.length > maxLength) {
           return text.substring(0, maxLength) + '...';
        }
        return text;
     };

    $(`#id_${LabelFieldName}`).autocomplete({

        minLength: 3,

        source: (request, response) => {
            let timeStamp = Date.now();
            $.getJSON(`/order_management/order_autocomplete/${LabelFieldName}=${request.term.trim().replace('=', '')},${timeStamp}`, data => {
                response(data);
            })
        },

        select: (e, ui) => {
            Object.entries(ui.item.data).forEach((fieldData) => {
                $(`#id_${fieldData[0]}`).val(fieldData[1]);
            });
        },
    }).autocomplete("instance")._renderItem = function (ul, item) {
        let spanStyle = 'color:#417690; margin:0; padding-left:3px; padding-right:3px;';
        let displaText = [dotifyText(item['label'], 50), item['data'][firstDataFieldName], item['data']['supplier'].replace(" GmbH", "")].join(`<span style='${spanStyle}'>⬧</span>`);
        return $("<li>")
            .attr("data-value", item.value)
            .append(`<span style='margin:0; padding-right:5px; padding-left:5px;'>${displaText}</span>`)
            .appendTo(ul);
    }
});