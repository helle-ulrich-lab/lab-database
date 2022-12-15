$(document).ready(function () {

    // Taken from https://stackoverflow.com/questions/34114819/how-load-on-double-click-instead-of-click-for-magnific-popup

    let magnific = $('.magnific-id').magnificPopup({
        type: 'iframe',

        iframe: {
            markup: '<div class="mfp-iframe-scaler">' +
                '<div class="mfp-close"></div>' +
                '<iframe class="mfp-iframe" frameborder="0" allowfullscreen></iframe>' +
                '</div>'
        },

        gallery: {
            enabled: true,
            preload: [0, 2],
            navigateByImgClick: true,
            arrowMarkup: '<button title="%title%" type="button" class="mfp-arrow mfp-arrow-%dir%"></button>',
            tPrev: 'Previous (Left arrow key)',
            tNext: 'Next (Right arrow key)',
            tCounter: '<span class="mfp-counter">%curr% of %total%</span>'
        },

        callbacks: {
            elementParse: function (item) {
                item.src = item.src + '?_to_field=id&_popup=1';
            }
        }
    })

    // remove click handler of magnific
    magnific.off('click');

    // add double click handler and call the `open` function of magnific
    magnific.on('contextmenu', function (e) {
        e.preventDefault();
        magnific.magnificPopup('open')
    });

})