gen_short = (path) ->
    $.get "/m/new/?url=" + encodeURIComponent(path), (data) ->
        $("#genshort").hide()
        $("#dispshort").html "<a href=\"/m/" + data + "/\">/m/" +
                data + "</a>"
        $("#dispshort").show()
