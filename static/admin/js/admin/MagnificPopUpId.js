$(document).ready(function () {

    // Taken from https://stackoverflow.com/questions/34114819/how-load-on-double-click-instead-of-click-for-magnific-popup
    // and https://stackoverflow.com/questions/5471291/javascript-with-jquery-click-and-double-click-on-same-element-different-effect

    // Get relevant fields and sort them by ascending order of id
    let idFields = $('.field-id').find('a').sort((a, b) => {
        return a.innerText - b.innerText;
    });

    let magnific = idFields.magnificPopup({
        type: 'iframe',

        iframe: {
            markup: '<div class="mfp-iframe-scaler">' +
                '<div class="mfp-close"></div>' +
                '<iframe class="mfp-iframe" frameborder="0" allowfullscreen></iframe>' +
                '</div>'
        },

        gallery: {
            enabled: true,
            preload: 0,
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

    magnific.on('click', function (e){
        
        e.preventDefault();
        
        var $this = $(this);
        
        if ($this.hasClass('clicked')) {
            $this.removeClass('clicked');
            // Action for double click
            magnific.magnificPopup('open', $.inArray(e.target, idFields));

        } else {

            $this.addClass('clicked');
            setTimeout(function () {
                if ($this.hasClass('clicked')) {
                    $this.removeClass('clicked');
                    // Action for single click
                    window.location.href = e.target.href;
                }
            }, 300);

        }


    })

})