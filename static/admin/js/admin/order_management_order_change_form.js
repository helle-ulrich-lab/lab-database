// Order autocomplete

$('#id_part_description,#id_supplier_part_no').click(function () {

    let labelFieldName = $(this).attr('id').replace('id_', '');
    let firstDataFieldName = labelFieldName === 'part_description' ? 'supplier_part_no' : 'part_description';
    
    let dotifyText = (text, maxLength) => {
        if (text.length > maxLength) {
           return text.substring(0, maxLength) + '...';
        }
        return text;
     };

    $(`#id_${labelFieldName}`).autocomplete({

        minLength: 3,

        source: (request, response) => {
            let timeStamp = Date.now();
            $.getJSON(`/order_management/order_autocomplete/${labelFieldName}=${request.term.trim().replace('=', '')},${timeStamp}`, data => {
                response(data);
            })
        },

        select: (e, ui) => {
            for (let fieldName in ui.item.data)
                $(`#id_${fieldName}`).val(ui.item.data[fieldName]);
        },

    }).autocomplete("instance")._renderItem = (ul, item) => {

        let firstTextElement = labelFieldName === 'part_description' ? dotifyText(item['label'], 50) : item['label'];
        let secondTextElement = firstDataFieldName === 'part_description' ? dotifyText(item['data'][firstDataFieldName], 50) : item['data'][firstDataFieldName];

        let spanStyle = 'color:var(--link-fg); margin:0; padding-left:3px; padding-right:3px;';
        let displayText = [firstTextElement, secondTextElement, item['data']['supplier'].replace(" GmbH", "")].join(`<span style='${spanStyle}'>┃</span>`);
        
        return $("<li>")
            .attr("data-value", item.value)
            .append(`<span style='margin:0px 5px; white-space: nowrap; padding:3px;'>${displayText}</span>`)
            .appendTo(ul);

    }
});