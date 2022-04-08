// Order autocomplete

$('#id_part_description,#id_supplier_part_no').click(function () {

    let LabelFieldName = $(this).attr('id').replace('id_', '');
    let firstDataFieldName = LabelFieldName === 'part_description' ? 'supplier_part_no' : 'part_description';
    let dotifyText = (text, maxLength) => {
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
    }).autocomplete("instance")._renderItem = (ul, item) => {
        let spanStyle = 'color:var(--link-fg); margin:0; padding-left:3px; padding-right:3px;';
        let firstTextElement = LabelFieldName === 'part_description' ? dotifyText(item['label'], 50) : item['label'];
        let secondTextElement = firstDataFieldName === 'part_description' ? dotifyText(item['data'][firstDataFieldName], 50) : item['data'][firstDataFieldName];
        let displayText = [firstTextElement, secondTextElement, item['data']['supplier'].replace(" GmbH", "")].join(`<span style='${spanStyle}'>┃</span>`);
        return $("<li>")
            .attr("data-value", item.value)
            .append(`<span style='margin:0px 5px; white-space: nowrap; padding:0;'>${displayText}</span>`)
            .appendTo(ul);
    }
});