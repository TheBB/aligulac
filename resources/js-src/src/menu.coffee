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
        $('a.dropdown-toggle').off('click')
    else
        $('a.dropdown-toggle').on('click', ->
            window.location.href = this.href
        )

$(document).ready toggle_navbar_method
$(window).resize toggle_navbar_method
