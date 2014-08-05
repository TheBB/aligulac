gen_short = (path) ->
    $.get "/m/new/?url=" + encodeURIComponent(path), (data) ->
        $("#gen_short").hide()
        $("#disp_short").html "<a href=\"/m/" + data + "/\">/m/" +
                data + "</a>"
        $("#disp_short").show()

module.exports.GenShort = GenShort =
    init: () ->
        $("#gen_short").click () ->
            gen_short location.href
