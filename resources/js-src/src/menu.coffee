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

$ ->
    allMenu = $ '.menu > ul > li > ul'
    menuHandler = ->
        menu = $(this).parent().next()
        if menu.is ':visible'
            allMenu.hide()
        else
            allMenu.hide()
            menu.show()

        $(document).one 'click', ->
            menu.hide()

        return false
    if mobile_regex.test navigator.userAgent
        $(".actionSelector").removeAttr "style"
        $('.menu > ul > li > div > a').next().button(
            text: false
            icons: primary: 'ui-icon-triangle-1-s'
        ).click(menuHandler).parent().next().buttonset().hide().menu()

        allMenu.parent().css
            paddingLeft: "0.1em"
            paddingRight: "0.1em"
    else
        $('.menu > ul > li > div > a').hover(menuHandler).parent()
        .next().buttonset().hide().menu()
