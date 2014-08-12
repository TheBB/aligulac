clocks_toggle_more = (e) ->
    $(e).next().toggle()
    $(e).find(".clock-toggle").toggleClass("right-caret").toggleClass("down-caret")


module.exports.Clocks = Clocks =
    init: () ->
        $(".clock-expandable").click () ->
            clocks_toggle_more this
