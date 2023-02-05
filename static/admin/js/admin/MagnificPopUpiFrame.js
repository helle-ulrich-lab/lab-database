$(document).ready(function () {

    for (classId of MagnificiFrameClassIds) {

        $(`.${classId}`).magnificPopup({

            type: 'iframe',

            iframe: {
                markup: '<div class="mfp-iframe-scaler mfp-loader">' + 
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
            }
        });

    }
})