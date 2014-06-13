 # ======================================================================
 # MENU
 # ======================================================================

mobile_regex = ///
    Android
    | webOS
    | iPhone
    | iPad
    | iPod
    | BlackBerry
    | IEMobile
    | Opera Mini
///i

toggle_navbar_method = ->
    if mobile_regex.test(navigator.userAgent) or $(window).width() <= 768
        $('.navbar .dropdown').off('mouseover').off('mouseout')
    else
        $('.navbar .dropdown').on('mouseover', ->
            $('.dropdown-toggle', this).trigger('click')
        ).on('mouseout', ->
            $('.dropdown-toggle', this).trigger('click').blur()
        )

toggle_navbar_method()
