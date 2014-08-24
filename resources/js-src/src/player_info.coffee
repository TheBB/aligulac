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
        $("#id_#{ k.replace('-', '_') }").val(val)

module.exports.PlayerInfo = PlayerInfo =
    init: ->
        $('.player-info-edit-button').click ->
            toggle_form this
