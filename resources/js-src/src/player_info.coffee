create_tag = require('common').create_tag

toggle_form = (sender) ->
    data = (x) -> $(sender).closest('tr').data x

    keys = [
        'id',
        'country',
        'birthday',
        'name',
        'romanized-name'
    ]

    for k in keys
        val = data k
        k2 = k.replace '-', '_'
        $("#id_#{ k2 }").val(val)
        if k2 == "id"
            continue
        lbl = $("label[for=id_#{ k2 }]")
        if lbl.children("small").length == 0
            lbl.append(
                create_tag('small')
                    .attr("id", "id_#{ k2 }_small")
                    .css("font-weight": "normal")
                    .hide()
            )
        else
            lbl.children("small").empty().hide()

    lp = data 'lp'
    if lp? and lp != ""
        $("#get_lp_btn").data 'lp', lp
        $("#get_lp_btn").show()
        $("#get_lp_span").show()
        $("#get_lp_span")
            .children("small")
            .text(autocomp_strings["Loading..."])
            .hide()
    else
        $("#get_lp_btn").data 'lp', null
        $("#get_lp_btn").hide()
        $("#get_lp_span").hide()

get_player_info = (lp) ->
    $("#get_lp_span").children().toggle()
    $.getJSON "/add/player_info_lp/?title=#{ escape(lp) }", (_data) ->
        if not _data.data?
            $("#get_lp_span")
                .children("small")
                .text(autocomp_strings[_data.message])
            return
        data = _data.data
        keys = [
            'name',
            'romanized_name',
            'birthday'
        ]
        for k in keys
            if data[k]?
                o = $("#id_#{ k }").val()
                n = data[k]
                if o != n
                    $("#id_#{ k }").val n
                    $("#id_#{ k }_small")
                        .text(autocomp_strings["Old value"] + ": " + o)
                        .show()
                    c = $("#id_#{ k }").css('background-color')
                    $("#id_#{ k }")
                        .animate('background-color': 'rgb(144, 238, 144)', 100)
                        .delay(750)
                        .animate('background-color': c, 600)
                else
                    $("#id_#{ k }_small").hide()

        $("#get_lp_span").children().toggle()

module.exports.PlayerInfo = PlayerInfo =
    init: ->
        $('.player-info-edit-button').click ->
            toggle_form this

        $('#country_filter').change ->
            $(this).closest('form').submit()

        $("#get_lp_btn").click ->
            get_player_info $(this).data 'lp'
            false
